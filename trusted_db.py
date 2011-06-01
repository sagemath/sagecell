import zmq
import misc
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
    dbreq=context.socket(zmq.REQ)
    dbport=dbreq.bind_to_random_port("tcp://127.0.0.1")
    fsreq=context.socket(zmq.REQ)
    fsport=fsreq.bind_to_random_port("tcp://127.0.0.1")
    p=Popen(["ssh", "localhost"],stdin=PIPE)
    p.stdin.write("""cd Documents/simple-python-db-compute/
python device_process.py --db zmq --dbaddress tcp://localhost:%i --fsaddress=tcp://localhost:%i\n"""%(dbport,fsport))
#device.run_zmq(workers=1,interact_timeout=60,db_address="tcp://localhost:%i",fsaddress=tcp://localhost:%i)
#"""%(dbport,fsport))
    #TODO: use SSH forwarding
    while True:
        try:
            x=req.recv_json()
            req.send_pyobj(getattr(db,x['msg-type'])(x['content']))
        except:
            pass
