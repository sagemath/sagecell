u"""
Starts a worker on an untrusted user account, connected over \xd8MQ
to the database.
"""

import zmq
import misc
import os
import signal
import sys
import json
import pickle
from subprocess import Popen, PIPE
from multiprocessing import Process, Pipe, Lock
import hmac
from hashlib import sha1
from base64 import b64encode
from zmq.eventloop import ioloop, zmqstream
import util
from util import log
shutting_down=False

class AuthenticationException(Exception):
    """
    An exception that occurs if a message fails HMAC authentication
    """
    pass

class MessageLoop:
    u"""
    A \xd8MQ IO loop that runs in a separate process.
    It receives database commands over \xd8MQ, executes them,
    and sends the results back.

    :arg db.DB db: the database to send the commands to
    :arg list keys: keys with which to generate authentication codes
    :arg bool isFS: True if the database is a filestore; False if not
    """

    def __init__(self, db, key, isFS=False):
        conn,self.pipe=Pipe()
        self.process=Process(target=loop, args=(db, key, conn, isFS))
        self.process.start()
        self.port=self.pipe.recv()
        self._device_info = None

    def device_id(self):
        """
        Get the device id for the remote device.

        :return: the device id
        """
        if self._device_info is None:
            self._get_device_info()
        return self._device_info['device']

    def pgid(self):
        """
        Get the process group ID of the process group associated with
        the device

        :return: the PGID
        :rtype: int
        """
        if self._device_info is None:
            self._get_device_info()
        return self._device_info['pgid']

    def _get_device_info(self):
        """
        Get the device information and store it in ``self._device_info``.
        """
        self._device_info=self.pipe.recv()
        self.pipe.close()

def loop(db, key, pipe, isFS):
    u"""
    Create a \xd8MQ socket and an event loop listening for new messages.

    :arg db.DB db: the database to which to send the commands received
    :arg str key: a key with which to generate authentication codes
    :arg multiprocessing.Connection pipe: one end of a multiprocessing
         Pipe, for sending information back into the main process
    :arg bool isFS: True if the database is a filestore; False if not
    """
    db.new_context()
    context=zmq.Context()
    rep=context.socket(zmq.XREP if isFS else zmq.REP)
    pipe.send(rep.bind_to_random_port('tcp://127.0.0.1'))
    loop=ioloop.IOLoop()
    fs_auth_dict={}
    db_auth_dict={}
    stream=zmqstream.ZMQStream(rep,loop)
    key=[key]
    stream.on_recv(lambda msgs:callback(db,key,pipe,fs_auth_dict if isFS else db_auth_dict,rep,msgs,isFS), copy=False)
    loop.start()

def callback(db, key, pipe, auth_dict, socket, msgs, isFS):
    u"""
    Callback triggered by a new message received in the \xd8MQ socket.

    :arg db.DB db: the database to which to send the commands received
    :arg list key: a key (wrapped in a list) with which to generate
         authentication codes
    :arg multiprocessing.Connection pipe: one end of a multiprocessing
         Pipe, for sending information back into the main process
    :arg dict auth_dict: a dictionary of HMAC objects keyed by session ID
    :arg zmq.core.socket.Socket socket: \xd8MQ REP socket
    :arg list msgs: list of Message objects
    :arg bool isFS: True if the database is a filestore; False if not
    """
    send_finally=True
    to_send=None
    if isFS:
        sender=msgs[0].bytes
        msgs=msgs[1:]
    try:
        msg_str=msgs[0].bytes
        msg=json.loads(msg_str)
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
        if 'session' in msg['content']:
            auth_session=msg['content']['session']+msg['content'].get('session_auth_channel','')
        if (msg['msg_type'] not in ['create_secret','set_device_pgid','add_messages'] 
            and 'session' in msg['content']):
            authenticate(msg_str, msgs[1].bytes, auth_session, auth_dict)
        if msg['msg_type']=='create_secret':
            key[0]=sha1(key[0]).digest()
            auth_dict[auth_session]=hmac.new(key[0],digestmod=sha1)
            log("Create authkey: session: %r, key: %r"%(auth_session, auth_dict[auth_session].digest()))
            to_send=True
        elif isFS:
            c=msg['content']
            if msg['msg_type']=='create_file':
                with db.new_file(session=c['session'], filename=c['filename']) as f:
                    f.write(msgs[2].bytes)
            elif msg['msg_type']=='copy_file':
                reply=[sender,db.get_file(session=c['session'], filename=c['filename']).read()]
                socket.send_multipart(reply, copy=False, track=True).wait()
                send_finally=False
        elif msg['msg_type']=='register_device':
            db.register_device(device=msg['content']['device'], 
                               account=sysargs.untrusted_account, 
                               workers=sysargs.workers,
                               pgid=msg['content']['pgid'])
            pipe.send(msg['content'])
        elif msg['msg_type']=='add_messages':
            content=[(json.loads(m),d) for m,d in msg['content']['messages']]
            for i in range(len(content)):
                m,d=content[i]
                # we don't need the session_auth_channel field for messages, only for files
                authenticate(msg['content']['messages'][i][0],d,m['parent_header']['session'],auth_dict,True)
            db.add_messages([c[0] for c in content])
        elif msg['msg_type'] in db.valid_untrusted_methods:
            to_send=getattr(db,msg['msg_type'])(**msg['content'])
    except AuthenticationException:
        log("Authentication failed: %s"%msg)
    finally:
        if send_finally:
            if isFS:
                socket.send_multipart([sender,pickle.dumps(to_send)])
            else:
                socket.send_pyobj(to_send)

def authenticate(msg_str, digest, session, auth_dict, hexdigest=False):
    """
    Authenticate a message using HMAC

    :arg str msg_str: the message, in string form
    :arg str digest: the digest, as claimed by the sender
    :arg str session: the session ID
    :arg dict auth_dict: a dict of HMAC objects, indexed by session ID
    :arg bool hexdigest: True if the digest was generated by
         ``hmac.hexdigest``, False if by ``hmac.digest``
    :raises AuthenticationException: upon a failed authentication
    :rtype: None
    """
    old_hmac=auth_dict[session].copy()
    auth_dict[session].update(msg_str)
    real_digest=auth_dict[session].hexdigest() if hexdigest else auth_dict[session].digest()
    if real_digest!=digest:
        auth_dict[session]=old_hmac
        log("Authentication problem: msg: %r\nreal_digest: %r\nsentdigest: %r\nold_digest: %r"%(msg_str, real_digest, digest, old_hmac.digest()))
        raise AuthenticationException

def signal_handler(signal, frame):
    """
    A cleanup function that runs when the user presses Ctrl+C
    """
    print "Shutting down in response to signal ", signal
    from signal import SIGKILL

    # TODO: handle the case where ctrl-c is pressed twice better
    # that's what this shutting_down variable is about
    global shutting_down
    if shutting_down:
        print "already shutting down"
        return
    else:
        print "setting shutdown"
        shutting_down=True

    print "Cleaning up device"
    cleanup_device(device=db_loop.device_id(), pgid=db_loop.pgid())
    print "Killing db and fs loops"
    for p in (db_loop.process, fs_loop.process):
        pid=p.pid
        print "Killing process %d"%p.pid
        p.terminate()
        # Just in case, SIGKILL it
        try:
            os.kill(pid, SIGKILL)
            os.waitpid(pid, os.WNOHANG)
        except OSError as e:
            print e
    print "Exiting"
    sys.exit(0)


def cleanup_device(device, pgid):
    """
    Stop a device and all of its subprocesses

    :arg str device: the device ID
    :arg int pgid: the process group ID associated with the device
    """
    # exit process, but first, kill the device I just started
    # TODO: security implications: we're killing a pg id that the untrusted side sent us
    # however, we are making sure we ssh into that account first, so it can only affect things from that account
    print "Shutting down device...",
    cmd="""
python -c 'import os,signal,time
os.killpg(%d,signal.SIGTERM)
time.sleep(2)
try:
    os.killpg(%d,signal.SIGKILL)
except:
    pass
'
exit
"""%(pgid,pgid)
    p=Popen(["ssh", sysargs.untrusted_account],stdin=PIPE)
    p.stdin.write(cmd)
    p.stdin.flush()
    p.wait()
    db.delete_device(device=device)
    print "done"

if __name__=='__main__':
    from argparse import ArgumentParser
    try:
        import sagecell_config
    except ImportError:
        import sagecell_config_default as sagecell_config
    parser=ArgumentParser(description="Starts a connection between a trusted and an untrusted process.")
    parser.add_argument("--db", choices=["mongo", "sqlalchemy"], help="Database to use on trusted side")
    parser.add_argument("-w", "--workers", type=int, default=1, help="Number of workers to start.")
    parser.add_argument("--print", action="store_true", dest="print_cmd", default=False, 
                        help="Print out command to launch workers instead of launching them automatically")
    parser.add_argument("--pidfile",
                      help="pidfile to write the pid", default="")
    parser.add_argument("--untrusted-account", dest="untrusted_account", 
                      help="untrusted account; should be something you can ssh into without a password", default="")
    parser.add_argument("--untrusted-python", dest="untrusted_python",
                      default=sagecell_config.device_config['untrusted-python'], 
                      help="the path to the Python the untrusted user should use")
    parser.add_argument("--untrusted-cpu", dest="untrusted_cpu", type=float,
                      default=sagecell_config.device_config.get('untrusted-cpu',-1.0), 
                      help="CPU time (seconds) allotted to each session")
    parser.add_argument("--untrusted-mem", dest="untrusted_mem", type=float,
                      default=sagecell_config.device_config.get('untrusted-mem',-1.0), 
                      help="Memory (MB) allotted to each session")
    parser.add_argument("-q", "--quiet", action="store_true", help="Turn off most logging")

    sysargs=parser.parse_args()

    if sysargs.untrusted_account is "":
        print "You must give an untrusted account we can ssh into using --untrusted-account"
        sys.exit(1)

    if sysargs.quiet:
        util.LOGGING=False
    print "PID: ", os.getpid()
    if sysargs.pidfile:
        if os.path.isfile(sysargs.pidfile):
            raise RuntimeError('pid file found: %s'%sysargs.pidfile)
        with open(sysargs.pidfile, 'w') as f:
            f.write("%s\n"%os.getpid())
    db, fs = misc.select_db(sysargs)
    keys=[b64encode(os.urandom(32)) if sysargs.print_cmd else os.urandom(32) for _ in (0,1)]
    db_loop=MessageLoop(db, keys[0])
    fs_loop=MessageLoop(fs, keys[1], isFS=True)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    cwd=os.getcwd()
    # We pass the key using a file to address security issues
    # see, for example, http://hub.opensolaris.org/bin/view/Community+Group+arc/passwords-cli
    #
    # TODO: use normal temp file tools to do this; the tricky thing is that we need a temp file on
    # the target system as well.
    #import tempfile
    #keyfile=tempfile.NamedTemporaryFile(delete=False)
    #filename=keyfile.name+"%i"
    import uuid
    filename="/tmp/%s"%uuid.uuid4()
    options=dict(cwd=cwd, 
                 workers=sysargs.workers, 
                 db_port=db_loop.port, 
                 fs_port=fs_loop.port,
                 quiet='-q' if sysargs.quiet or util.LOGGING is False else '',
                 untrusted_python=sysargs.untrusted_python,
                 untrusted_cpu=sysargs.untrusted_cpu,
                 untrusted_mem=sysargs.untrusted_mem,
                 keyfile=filename+"_copy")

    cmd="""cd %(cwd)s
%(untrusted_python)s device_process.py --db zmq --timeout 60 -w %(workers)s --cpu %(untrusted_cpu)f --mem %(untrusted_mem)f --dbaddress tcp://localhost:%(db_port)i --fsaddress tcp://localhost:%(fs_port)i --keyfile %(keyfile)s %(quiet)s\n"""%options
    if sysargs.print_cmd:
        print
        print "echo %s%s%s > %s_copy"%(keys[0],'KEY_SEPARATOR',keys[1],filename)
        print cmd
    else:
        # we use os.open so we can specify the file permissions
        with os.fdopen(os.open(filename, os.O_WRONLY|os.O_EXCL|os.O_CREAT, 0600), 'w') as f:
            f.write('KEY_SEPARATOR'.join(keys))
        # transferred with -p to keep the restrictive permissions
        Popen(["scp","-p",filename,sysargs.untrusted_account+":"+filename+"_copy"],stdin=PIPE,stdout=PIPE).wait()
        os.remove(filename)
        p=Popen(["ssh", sysargs.untrusted_account],stdin=PIPE)
        p.stdin.write(cmd)
        p.stdin.flush()
        print "SSH process id: ",p.pid

    #TODO: use SSH forwarding
    log("trusted_db entering request loop")
    try:
        db_loop.process.join()
    except:
        print "IN EXCEPT"
        signal_handler(signal.SIGTERM,None)
        print "Done"
    sys.exit(0)
