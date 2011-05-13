import sys, time, traceback, StringIO, contextlib, random

def log(device_id, code_id=None, message=None):
    print "%s   %s: %s"%(device_id,code_id, message)

class QueueOut(StringIO.StringIO):
    def __init__(self, _id, queue, channel):
        StringIO.StringIO.__init__(self)
        self.cell_id=_id
        self.channel=channel
        self.queue=queue

    def raw_message(self, msg_type, content):
        """
        Send a message where you can change the outer IPython msg_type and completely specify the content.
        """
        msg = {'msg_type': msg_type,
               'parent_header': {'msg_id': self.cell_id},
               'header': {'msg_id':random.random()},
               'content': content}
        self.queue.put(msg)
        sys.__stdout__.write("USER MESSAGE PUT IN QUEUE (channel %s): %s\n"%(self.channel, msg))

    def write(self, output):
        self.raw_message(msg_type='stream',
                         content={'data': output, 'name':self.channel})

class QueueOutMessage(QueueOut):
    def __init__(self, _id, queue):
        QueueOut.__init__(self, _id, queue, 'extension')

    def message(self, msg_type, content):
        """
        Send a user message with a specific type.  This will be wrapped in an IPython 'extension' message and sent to the client.
        """
        self.raw_message(msg_type='extension',
                         content={'content': content, 'msg_type': msg_type})

class OutputIPython(object):
    def __init__(self, _id, queue):
        self.cell_id=_id
        self.queue=queue
    
    def __enter__(self):
        # remap stdout, stderr, set up a pyout display handler.  Also, return the message queue so the user can put messages into the system
        self.stdout_queue=QueueOut(self.cell_id, self.queue, "stdout")
        self.stderr_queue=QueueOut(self.cell_id, self.queue, "stderr")
        self.pyout_queue=QueueOut(self.cell_id, self.queue, "pyout")
        self.pyerr_queue=QueueOut(self.cell_id, self.queue, "pyerr")
        self.message_queue=QueueOutMessage(self.cell_id, self.queue)
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        #old_display = sys.displayhook
        #old_err = sys.excepthook
        
        # replace sys.displayhook
        
        # replace sys.excepthook
        
        sys.stderr = self.stderr_queue
        sys.stdout = self.stdout_queue
        return self.message_queue
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout=self.old_stdout
        sys.stderr=self.old_stderr
        #if exc_type is not None:
        #    import traceback
        #    self.stderr_queue.write(traceback.format_exc())
        # supress the exception
        return False

from multiprocessing import Pool, TimeoutError, Process, Queue, Lock, current_process

def run(db, fs, workers=1, poll_interval=0.1):
    """Run the compute device, querying the database and doing
    relevant work."""
    device_id=random.randrange(sys.maxint)
    log(device_id, message="Starting device loop for device %s..."%device_id)
    pool=Pool(processes=workers)
    results={}
    sequence={}
    while True:
        # Queue up all unevaluated cells we requested
        for X in db.get_unevaluated_cells(device_id):
            # change for ipython messages
            _id = str(X['_id'])
            code = X['input']
            log(device_id, _id,message="evaluating '%s'"%code)
            results[_id]=pool.apply_async(execute_code, (_id, code))
            sequence[_id]=0
        # Get whatever results are done
        finished=set(i for i, r in results.iteritems() if r.ready())
        new_messages=[]
        while not outQueue.empty():
            msg=outQueue.get()
            cell_id = msg['parent_header']['msg_id']
            msg['sequence']=sequence[cell_id]
            sequence[cell_id]+=1
            new_messages.append(msg)
        # delete the output that I'm finished with
        for _id in finished:
            msg={'content': {"status":"ok",
                             "execution_count":1,
                             "payload":[],
                             "user_expressions":{},
                             "user_variables":{}},
                 "header":{"username":"","msg_id":random.random(),"session":""},
                 "parent_header":{"msg_id":_id,"username":"","session":""},
                 "msg_type":"execute_reply",
                 "sequence":sequence[_id]}
            new_messages.append(msg)
            # should send back an execution_state: idle message too
            del sequence[_id]
            del results[_id]
        if len(new_messages)>0:
            db.add_messages(None, new_messages)


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
    with OutputIPython(cell_id, outQueue) as MESSAGE:
        exec code in {'MESSAGE': MESSAGE}
    print "Done executing code: ", code
    
        

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
        #Make an ipython message.
        outQueue.put((cell_id,new_stream('files',printout=False,files=file_list)))
    current_process().daemon=oldDaemon
    os.chdir(curr_dir)
    shutil.rmtree(tmp_dir)

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
    outQueue=Queue()
    fslock=Lock()
    run(db, fs, workers=sysargs.workers)
