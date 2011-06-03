import zmq
import misc
import os
from subprocess import Popen, PIPE

if __name__=='__main__':
    try:
        from argparse import ArgumentParser
    except ImportError:
        from IPython.external import argparse
        ArgumentParser=argparse.ArgumentParser
    parser=ArgumentParser(description="Starts a connection between a trusted andn an untrusted process.")
    parser.add_argument("--db", choices=["mongo","sqlite","sqlalchemy"], default="mongo", help="Database to use")
    parser.add_argument("-w", type=int, default=1, dest="workers", help="Number of workers to start.")
    sysargs=parser.parse_args()
    db, fs = misc.select_db(sysargs)

    context=zmq.Context()
    dbrep=context.socket(zmq.REP)
    dbport=dbrep.bind_to_random_port("tcp://127.0.0.1")
    fsrep=context.socket(zmq.REP)
    fsport=fsrep.bind_to_random_port("tcp://127.0.0.1")
    cwd=os.getcwd()
    p=Popen(["ssh", "localhost"],stdin=PIPE,bufsize=0 )
    p.stdin.write("""cd %s
python device_process.py --db zmq --timeout 60 --dbaddress tcp://localhost:%i --fsaddress=tcp://localhost:%i\n"""%(cwd,dbport,fsport))
    #TODO: use SSH forwarding
    print "trusted_db entering request loop"
    poller=zmq.Poller()
    poller.register(dbrep,zmq.POLLIN)
    poller.register(fsrep,zmq.POLLIN)
    file_next=False
    while True:
        socket_list=[s[0] for s in poller.poll(500)]
        for s in socket_list:
            x=s.recv_json()
            if s is fsrep and x['msg_type']=='create_file':
                with fs.new_file(**x['content']) as f:
                    f.write(fsrep.recv())
                fsrep.send('')
            else:
                sendTo=db if s is dbrep else fs
                s.send_pyobj(getattr(sendTo,x['msg_type'])(**x['content']))
