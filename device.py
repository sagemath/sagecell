import sys, time, traceback, StringIO, contextlib, random

def log(device_id, code_id=None, message=None):
    print "%s   %s: %s"%(device_id,code_id, message)

class QueueOut(StringIO.StringIO):
    def __init__(self, _id):
        StringIO.StringIO.__init__(self)
        self.cell_id=_id
    def write(self, output):
        outQueue.put((self.cell_id,output))

# based on a stackoverflow answer
@contextlib.contextmanager
def stdoutIO(stdout=None):
    """
    Reassign stdout to be a StringIO object.

    To use, do something like:
    
    with stdoutIO() as s:
        print "Hello world"

    print("Output: %s"%s.getvalue())

    Exceptions in the code should be re-raised and the stdout should
    correctly revert to what it was even if an error is raised.
    """
    old_stdout = sys.stdout
    if stdout is None:
        stdout = StringIO.StringIO()
    sys.stdout = stdout
    try:
        # code in the context is executed when we yield
        yield stdout
    except:
        # any exceptions in the code should get propogated
        raise
    finally:
        # Make sure that no matter what, the stdout reverts to what it
        # was before this context
        sys.stdout = old_stdout

from multiprocessing import Pool, TimeoutError, Process, Queue, Lock, current_process

def run(db, fs, workers=1, poll_interval=0.1):
    """Run the compute device, querying the database and doing
    relevant work."""
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
            results[X['_id']]=pool.apply_async(execute_code, (X['_id'], code))
            outputs[X['_id']]=""
        # Get whatever results are done
        finished=set(_id for _id, r in results.iteritems() if r.ready())
        changed=set()
        while not outQueue.empty():
            _id,out=outQueue.get()
            outputs[_id]+=out
            changed.add(_id)
        for _id in changed:
            db.set_output(_id, make_output_json(outputs[_id], _id in finished))
        for _id in finished-changed:
            db.set_output(_id, make_output_json(outputs[_id], True))
        # delete the output that I'm finished with
        for _id in finished:
            del results[_id]
            del outputs[_id]

        time.sleep(poll_interval)

STREAM_SEPARATOR='____NEW__STREAM____'
HEADER_SEPARATOR='____END_STREAM_HEADER___'

def new_stream(stream_type,printout=True,**kwargs):
    import sys
    if printout is True:
        out=sys.stdout
    else:
        out=StringIO.StringIO()
    out.write(STREAM_SEPARATOR)
    metadata={'type':stream_type}
    metadata.update(kwargs)
    out.write(json.dumps(metadata))
    out.write(HEADER_SEPARATOR)
    if printout is False:
        return out.getvalue()

import json

def make_output_json(s, closed):
    """
    This function takes a string representing the output of a computation.
    It constructs a dictionary which represents the output parsed into streams
    """
    s=s.split(STREAM_SEPARATOR)
    # at the top of each stream is some information about the stream
    order=0
    output=dict()

    if len(s[0])!=0 and HEADER_SEPARATOR not in s[0]:
        # If there is no header in the first stream,
        # assume it is a text stream.  This stream includes all 
        # output before the first new_stream() command.
        stream=dict()
        stream['type']='text'
        stream['order']=order
        stream['content']=s[0]
        output['stream_%s'%order]=stream
        order+=1

    for stream_string in s[1:]:
        stream=dict()
        header_string, body_string=stream_string.split(HEADER_SEPARATOR)
        header=json.loads(header_string)
        
        header['order']=order
        if 'type' not in header:
            header['type']='text'
            
        stream.update(header)
        stream['content']=body_string

        output['stream_%s'%order]=stream
        order+=1
    output['closed']=closed
    return output

def unicode_str(obj, encoding='utf-8'):
    """Takes an object and returns a unicode human-readable representation."""
    if isinstance(obj, str):
        return obj.decode(encoding, 'ignore')
    elif isinstance(obj, unicode):
        return obj
    return unicode(obj)

def displayhook_hack(string):
    """Modified version of string so that ``exec``'ing it results in
    displayhook possibly being called.
    """
    # This function is all so the last line (or single lines) will
    # implicitly print as they should, unless they are an assignment.
    # If anybody knows a better way to do this, please tell me!
    
    # The essential problem seems to be that exec executes the code as
    # if the code was in a file.  However, we want the last statement
    # to print out as if it was interactive.  So we have to generate
    # the code as if it was an interactive statement (by compiling a
    # "single" interactive statement) and executing that code object.

    # There is a patch on trac that uses the ast module to print out
    # each line's output or the last line's output.  Alternatively, we
    # could fork a python process and feed the code in as standard
    # input and just capture the stdout.

    string = string.splitlines()
    i = len(string)-1
    if i >= 0:
        # skip lines that are either empty or start with whitespace
        while len(string[i])==0 or string[i][0] in ' \t':
            i -= 1
        final_lines = unicode_str('\n'.join(string[i:]))
        if not final_lines.startswith('def '):
            try:
                compile(final_lines + '\n', '', 'single')
                string[i] = "exec compile(%r + '\\n', '', 'single')" % final_lines
                string = string[:i+1]
            except SyntaxError, msg:
                pass
    return '\n'.join(string)

import tempfile
import shutil
import os

def execProcess(cell_id, code):
    """Run the code, outputting into a pipe.
Meant to be run as a separate process."""
    # TODO: Have some sort of process limits on CPU time/memory
    with stdoutIO(QueueOut(cell_id)):
        try:
            exec code in {}
        except:
            new_stream("text")
            print traceback.format_exc()
        

def execute_code(cell_id, code):
    """Evaluate the given code in another process,
    Put the results and list of generated files into the global queue."""
    # the fs variable is inherited from the parent process
    code = displayhook_hack(code)
    curr_dir=os.getcwd()
    tmp_dir=tempfile.mkdtemp()
    print "Temp files in "+tmp_dir
    # We should at least document the side effects of 
    # just setting the daemon flag and creating subprocesses
    # What things does a user/developer need to be aware of?
    oldDaemon=current_process().daemon
    current_process().daemon=False
    # Daemonic processes cannot create children
    os.chdir(tmp_dir)
    result=""
    p=Process(target=execProcess, args=(cell_id, code))
    p.start()
    p.join()
    file_list=[]
    fslock.acquire()
    for filename in os.listdir(tmp_dir):
        file_list.append(filename)
        fs_file=fs.new_file(cell_id, filename)
        with open(filename) as f:
            fs_file.write(f.read())
        fs_file.close()
    fslock.release()
    if len(file_list)>0:
        outQueue.put((cell_id,new_stream('files',printout=False,files=file_list)))
    current_process().daemon=oldDaemon
    os.chdir(curr_dir)
    shutil.rmtree(tmp_dir)

def run_ip_device():
    import uuid
    import zmq
    from ip_receiver import IPReceiver
    from IPython.zmq.ipkernel import launch_kernel
    device_id=random.randrange(sys.maxint)
    kernel=launch_kernel()
    db.set_ipython_ports(kernel)
    sub=IPReceiver(zmq.SUB, kernel[2])
    context=zmq.Context()
    xreq=context.socket(zmq.XREQ)
    xreq.connect("tcp://localhost:%i"%(kernel[1],))
    while True:
        for X in db.get_unevaluated_cells(device_id):
            header={"msg_id":str(X["_id"])}
            xreq.send_json({"header":header, "msg_type":"execute_request", "content": { \
                        "code":X['input'], "silent":False,
                        "user_variables":[], "user_expressions":{}}})
            sequence=0
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
                    db.add_messages(X["_id"],new_messages)
                if done:
                    break
        time.sleep(0.1)

if __name__ == "__main__":
    import misc
    from argparse import ArgumentParser
    parser=ArgumentParser(description="Run one or more devices to process commands from the client.")
    parser.add_argument("--noipython", action="store_false", dest="ipython", help="Do not use ipython workers")
    parser.add_argument("--db", choices=["mongo","sqlite","sqlalchemy"], default="mongo", help="Database to use")
    parser.add_argument("-w", type=int, default=1, dest="workers", help="Number of workers to start.")
    sysargs=parser.parse_args()
    if sysargs.ipython:
        db, fs = misc.select_db(sysargs)
        run_ip_device()
    else:
        db, fs = misc.select_db(sysargs)
        outQueue=Queue()
        fslock=Lock()
        run(db, fs, workers=args.workers)
