u"""
Starts a worker on an untrusted user account, connected over \xd8MQ
to the database.
"""

import zmq
import misc
import os
import signal
import sys
from subprocess import Popen, PIPE
from multiprocessing import Process, Pipe
from zmq.eventloop import ioloop, zmqstream
import util
from util import log
from json import loads
shutting_down=False

class MessageLoop:
    u"""
    A \xd8MQ IO loop that runs in a separate process.
    It receives database commands over \xd8MQ, executes them,
    and sends the results back.

    :arg db: the database to send the commands to
    :type db: db.DB
    :arg isFS: True if the database is a filestore; False if not
    :type isFS: bool
    """

    def __init__(self, db, isFS=False):
        conn,self.pipe=Pipe()
        self.process=Process(target=loop, args=(conn, db, callback, isFS))
        self.process.start()
        self.port=self.pipe.recv()

    def pgid(self):
        """
        :return: the PGID of the process group associated with the device.
        :rtype: int
        """
        if self.pipe.closed:
            return self._pgid
        else:
            self._pgid=self.pipe.recv()
            self.pipe.close()
            return self._pgid

def loop(pipe, db, callback, isFS):
    u"""
    Create a \xd8MQ socket and an event loop listening for new messages.

    :arg pipe: one end of a multiprocessing Pipe, for sending information back into the main process
    :type pipe: _multiprocessing.Connection
    :arg db: the database to which to send the commands received
    :type db: db.DB
    :arg isFS: True if the database is a filestore; False if not
    :type isFS: bool
    """
    context=zmq.Context()
    rep=context.socket(zmq.REP)
    pipe.send(rep.bind_to_random_port('tcp://127.0.0.1'))
    loop=ioloop.IOLoop()
    stream=zmqstream.ZMQStream(rep,loop)
    stream.on_recv(lambda msgs:callback(rep,msgs,db,pipe,isFS), copy=False)
    loop.start()

def callback(socket, msgs, db, pipe, isFS):
    u"""
    Callback triggered by a new message received in the \xd8MQ socket.

    :arg socket: \xd8MQ REP socket
    :type socket: zmq.Socket
    :arg msgs: list of Message objects
    :type msgs: list
    :arg pipe: one end of a multiprocessing Pipe, for sending information back into the main process
    :type pipe: _multiprocessing.Connection
    :arg db: the database to which to send the commands received
    :type db: db.DB
    :arg isFS: True if the database is a filestore; False if not
    :type isFS: bool
    """
    
    msg=loads(msgs[0].bytes)
    # Since Sage ships an old version of Python,
    # we need to work around this python bug:
    # http://bugs.python.org/issue2646 (see also
    # the fix: http://bugs.python.org/issue4978).
    # Unicode as keywords works in python 2.7, so
    # upgrading Sage's python means we can get
    # around this.
    # Basically, we need to make sure the keys
    # are *not* unicode strings.
    msg['content']=dict((str(k),v) for k,v in msg['content'].items())
    if isFS:
        if msg['msg_type']=='create_file':
            with db.new_file(**msg['content']) as f:
                f.write(msgs[1].bytes)
                socket.send('')
        elif msg['msg_type']=='copy_file':
            contents=db.get_file(**msg['content']).read()
            socket.send(contents, copy=False, track=True).wait()
    elif msg['msg_type']=='set_device_pgid':
        # have to add the ssh account to this
        db.set_device_pgid(device=msg['content']['device'], 
                           account=sysargs.untrusted_account, 
                           pgid=msg['content']['pgid'])
        pipe.send(msg['content']['pgid'])
        socket.send_pyobj(None)
    else:
        if msg['msg_type'] in db.valid_untrusted_methods:
            socket.send_pyobj(getattr(db,msg['msg_type'])(**msg['content']))

def signal_handler(signal, frame, pgid):
    # TODO: handle the case where ctrl-c is pressed twice better
    # that's what this shutting_down variable is about
    global shutting_down
    if shutting_down:
        return
    else:
        shutting_down=True

    # exit process, but first, kill the device I just started
    # security implications: we're killing a pg id that the untrusted side sent us
    # however, we are making sure we ssh into that account first, so it can only affect things from that account
    print "Shutting down device...",
    cmd="""
python -c 'import os,signal; os.killpg(%d,signal.SIGKILL)'
exit
"""%int(pgid)
    # reset signal handler so we don't call ourselves again
    #signal.signal(signal.SIGINT, signal.SIG_DFL)
    p=Popen(["ssh", sysargs.untrusted_account],stdin=PIPE)
    p.stdin.write(cmd)
    p.stdin.flush()
    p.wait()
    print "done",
    sys.exit(0)

if __name__=='__main__':
    # We cannot use argparse until Sage's python is upgraded.
    from optparse import OptionParser
    parser=OptionParser(description="Starts a connection between a trusted and an untrusted process.")
    parser.add_option("--db", choices=["mongo","sqlite","sqlalchemy"], default="mongo", help="Database to use on trusted side")
    parser.add_option("-w", type=int, default=1, dest="workers", help="Number of workers to start.")
    parser.add_option("--print", action="store_true", dest="print_cmd", default=False, 
                        help="Print out command to launch workers instead of launching them automatically")
    parser.add_option("--untrusted-account", dest="untrusted_account", 
                      help="untrusted account; should be something you can ssh into without a password", default="")
    parser.add_option("--untrusted-python", dest="untrusted_python", default="python", 
                      help="the path to the python the untrusted user should use")
    parser.add_option("-q", action="store_true", dest="quiet", help="Turn off most logging")

    (sysargs,args)=parser.parse_args()

    if sysargs.untrusted_account is "":
        print "You must give an untrusted account we can ssh into using --untrusted-account"
        sys.exit(1)

    if sysargs.quiet:
        util.LOGGING=False
    db, fs = misc.select_db(sysargs)
    db_loop=MessageLoop(db)
    fs_loop=MessageLoop(fs, isFS=True)
    signal.signal(signal.SIGINT, signal_handler)

    cwd=os.getcwd()
    options=dict(cwd=cwd, workers=sysargs.workers, db_port=db_loop.port, fs_port=fs_loop.port,
                 quiet='-q' if sysargs.quiet else '',
                 untrusted_python=sysargs.untrusted_python)
    cmd="""cd %(cwd)s
%(untrusted_python)s device_process.py --db zmq --timeout 60 -w %(workers)s --dbaddress tcp://localhost:%(db_port)i --fsaddress=tcp://localhost:%(fs_port)i %(quiet)s\n"""%options
    if sysargs.print_cmd:
        print cmd
    else:
        p=Popen(["ssh", sysargs.untrusted_account],stdin=PIPE)
        p.stdin.write(cmd)
        p.stdin.flush()
        print "SSH process id: ",p.pid

    #TODO: use SSH forwarding
    log("trusted_db entering request loop")
    try:
        db_loop.process.join()
    except:
        signal_handler(None, None, db_loop.pgid())
