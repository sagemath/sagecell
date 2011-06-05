import zmq
import misc
import os
import signal
import sys
from subprocess import Popen, PIPE
import util
from util import log
shutting_down=False

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

    context=zmq.Context()
    dbrep=context.socket(zmq.REP)
    dbport=dbrep.bind_to_random_port("tcp://127.0.0.1")
    fsrep=context.socket(zmq.REP)
    fsport=fsrep.bind_to_random_port("tcp://127.0.0.1")


    def signal_handler(signal, frame):
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
"""%int(device_pgid)
        # reset signal handler so we don't call ourselves again
        #signal.signal(signal.SIGINT, signal.SIG_DFL)
        p=Popen(["ssh", sysargs.untrusted_account],stdin=PIPE)
        p.stdin.write(cmd)
        p.stdin.flush()
        p.wait()
        print "done",
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)


    cwd=os.getcwd()
    options=dict(cwd=cwd, workers=sysargs.workers, dbport=dbport, fsport=fsport,
                 quiet='-q' if sysargs.quiet else '',
                 untrusted_python=sysargs.untrusted_python)
    cmd="""cd %(cwd)s
%(untrusted_python)s device_process.py --db zmq --timeout 60 -w %(workers)s --dbaddress tcp://localhost:%(dbport)i --fsaddress=tcp://localhost:%(fsport)i %(quiet)s\n"""%options
    if sysargs.print_cmd:
        print cmd
    else:
        p=Popen(["ssh", sysargs.untrusted_account],stdin=PIPE)
        p.stdin.write(cmd)
        p.stdin.flush()
        print "SSH process id: ",p.pid

    #TODO: use SSH forwarding
    log("trusted_db entering request loop")
    poller=zmq.Poller()
    poller.register(dbrep,zmq.POLLIN)
    poller.register(fsrep,zmq.POLLIN)
    try:
        while True:
            socket_list=[s[0] for s in poller.poll(500)]
            for s in socket_list:
                x=s.recv_json()
                sendTo=db if s is dbrep else fs
                if x['msg_type']!='get_input_messages':
                    log(x)
                if s is fsrep and x['msg_type']=='create_file':
                    with fs.new_file(**x['content']) as f:
                        f.write(s.recv())
                    s.send('')
                elif s is dbrep and x['msg_type']=='set_device_pgid':
                    # have to add the ssh account to this
                    sendTo.set_device_pgid(device=x['content']['device'], 
                                           account=sysargs.untrusted_account, 
                                           pgid=x['content']['pgid'])
                    device_pgid=x['content']['pgid']
                    s.send_pyobj(None)
                else:
                    if x['msg_type'] in sendTo.valid_untrusted_methods:
                        s.send_pyobj(getattr(sendTo,x['msg_type'])(**x['content']))
    except:
        signal_handler(None, None)
