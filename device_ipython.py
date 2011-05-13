import sys, time, traceback, StringIO, contextlib, random

def log(device_id, code_id=None, message=None):
    print "%s   %s: %s"%(device_id,code_id, message)

from multiprocessing import Pool, TimeoutError, Process, Queue, Lock, current_process

def run_ip_pool(db, fs, workers=1, poll_interval=0.1):
    """Run the compute device, querying the database and doing
    relevant work.

    Open a ZMQ socket and pass the address in to the workers.  Hook the workers up to send everything to this socket. 
    
    Keep track of a sequence number for each worker.  Then just get all messages, attaching the right sequence number (based on the worker number or header id), and insert the messages into the database.

    """
    device_id=random.randrange(sys.maxint)
    log(device_id, message="Starting device loop for device %s..."%device_id)
    pool=Pool(processes=workers)
    results={}
    outputs={}
    while True:
        # Queue up all unevaluated cells we requested
        for X in db.get_unevaluated_cells(device_id):
            code = X['input']
            log(device_id, X['_id'],message="evaluating '%s'"%code)
            results[X['_id']]=pool.apply_async(run_ip_worker, [X])
            outputs[X['_id']]=""
        # Get whatever results are done
        # finished=set(_id for _id, r in results.iteritems() if r.ready())
        # changed=set()
        # #TODO: when we move the db insertion here,
        # # iterate through queued messages
        # while not outQueue.empty():
        #     _id,out=outQueue.get()
        #     outputs[_id]+=out
        #     changed.add(_id)
        # for _id in changed:
        #     db.set_output(_id, make_output_json(outputs[_id], _id in finished))
        # for _id in finished-changed:
        #     db.set_output(_id, make_output_json(outputs[_id], True))
        # # delete the output that I'm finished with
        # for _id in finished:
        #     del results[_id]
        #     del outputs[_id]

        time.sleep(poll_interval)


def run_ip_worker(request_msg):
    """
    Execute one block of input code and then exit

    INPUT: request_msg---a json message with the input code, in ipython messaging format
    """
    #TODO: db and fs are inherited from the parent process; is that thread safe?
    import uuid
    import zmq
    import os
    import shutil
    import tempfile
    from ip_receiver import IPReceiver
    from IPython.zmq.ipkernel import launch_kernel
    msg_id=str(request_msg['_id'])
    log(db, msg_id, message='Starting run_ip_worker')

    #TODO: launch the kernel by forking an already-running clean process
    kernel=launch_kernel()
    tempDir=tempfile.mkdtemp()
    log(db, msg_id, message="Temporary directory: %s"%tempDir)
    db.set_ipython_ports(kernel)
    sub=IPReceiver(zmq.SUB, kernel[2])
    context=zmq.Context()
    xreq=context.socket(zmq.XREQ)
    xreq.connect("tcp://localhost:%i"%(kernel[1],))
    log(db, msg_id, 'Finished setting up IPython kernel')
    sequence=0
    inputCode="import os\nos.chdir(%r)\n"%(tempDir,)+request_msg["input"]
    header={"msg_id": msg_id}
    xreq.send_json({"header": header, 
                    "msg_type": "execute_request", 
                    "content": {"code":inputCode,
                                "silent":False,
                                "user_variables":[], 
                                "user_expressions":{}} })
    log(db, msg_id, "Sent request, starting loop for output")
    while True:
        done=False
        new_messages=[]
        for msg in sub.getMessages(header):
            if msg["msg_type"] in ("stream", "display_data", "pyout", "extension","execute_reply","status"):
                msg['sequence']=sequence
                sequence+=1
                new_messages.append(msg)
            if msg["msg_type"]=="execute_reply" or \
               (msg["msg_type"]=="status" and msg["content"]["execution_state"]=="idle"):
                done=True
        if len(new_messages)>0:
            db.add_messages(request_msg["_id"],new_messages)
        if done:
            break
    file_list=[]
    for filename in os.listdir(tempDir):
        file_list.append(filename)
        fs_file=fs.new_file(request_msg["_id"], filename)
        with open(tempDir+"/"+filename) as f:
            fs_file.write(f.read())
            fs_file.close()
    if len(file_list)>0:
        file_list.sort()
        db.add_messages(request_msg["_id"],[{'parent_header':header, 'sequence':sequence, 'msg_type':'files',
                                             'content':{"files":file_list}}])
        shutil.rmtree(tempDir)
    #TODO: make polling interval a variable
    time.sleep(0.1)

if __name__ == "__main__":
    import misc
    try:
        from argparse import ArgumentParser
    except ImportError:
        from IPython.external import argparse
        ArgumentParser=argparse.ArgumentParser
    parser=ArgumentParser(description="Run one or more devices to process commands from the client.")
    parser.add_argument("--db", choices=["mongo","sqlite","sqlalchemy"], default="mongo", help="Database to use")
    parser.add_argument("-w", type=int, default=1, dest="workers", help="Number of workers to start.")
    sysargs=parser.parse_args()
    db, fs = misc.select_db(sysargs)
    run_ip_pool(db, fs, workers=sysargs.workers)
