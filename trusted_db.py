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
    parser=ArgumentParser(description="Starts a connection between a trusted and an untrusted process.")
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
    import time
    while True:
        x=dbrep.recv_json()
        print "***********Received: ", x
        result=getattr(db,x['msg_type'])(**x['content'])
        print "***********Sending: ",result
        dbrep.send_pyobj(result)
        time.sleep(0.5)
