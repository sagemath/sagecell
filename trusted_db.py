import zmq
import misc
import os
from subprocess import Popen, PIPE
from util import log

if __name__=='__main__':
    try:
        from argparse import ArgumentParser
    except ImportError:
        from IPython.external import argparse
        ArgumentParser=argparse.ArgumentParser
    parser=ArgumentParser(description="Starts a connection between a trusted and an untrusted process.")
    parser.add_argument("--db", choices=["mongo","sqlite","sqlalchemy"], default="mongo", help="Database to use on trusted side")
    parser.add_argument("-w", type=int, default=1, dest="workers", help="Number of workers to start.")
    parser.add_argument("--print", action="store_true", dest="print_cmd", default=False, 
                        help="Print out command to launch workers instead of launching them automatically")
    sysargs=parser.parse_args()
    db, fs = misc.select_db(sysargs)

    context=zmq.Context()
    dbrep=context.socket(zmq.REP)
    dbport=dbrep.bind_to_random_port("tcp://127.0.0.1")
    fsrep=context.socket(zmq.REP)
    fsport=fsrep.bind_to_random_port("tcp://127.0.0.1")
    cwd=os.getcwd()
    cmd="""cd %(cwd)s
python device_process.py --db zmq --timeout 60 -w %(workers)s --dbaddress tcp://localhost:%(dbport)i --fsaddress=tcp://localhost:%(fsport)i\n"""%dict(cwd=cwd, workers=sysargs.workers, dbport=dbport, fsport=fsport)
    if sysargs.print_cmd:
        print cmd
    else:
        p=Popen(["ssh", "localhost"],stdin=PIPE)
        p.stdin.write(cmd)
        p.stdin.flush()
    #TODO: use SSH forwarding
    log("trusted_db entering request loop")
    poller=zmq.Poller()
    poller.register(dbrep,zmq.POLLIN)
    poller.register(fsrep,zmq.POLLIN)
    while True:
        socket_list=[s[0] for s in poller.poll(500)]
        for s in socket_list:
            x=s.recv_json()
            if x['msg_type']!='get_input_messages':
                log(x)
            if s is fsrep and x['msg_type']=='create_file':
                with fs.new_file(**x['content']) as f:
                    f.write(s.recv())
                fsrep.send('')
            else:
                sendTo=db if s is dbrep else fs
                if x['msg_type'] in sendTo.valid_untrusted_methods:
                    s.send_pyobj(getattr(sendTo,x['msg_type'])(**x['content']))
