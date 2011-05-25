import sys, time, traceback, StringIO, contextlib, random
import interact

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

    def display(self, data):
        """
        Send a display_data message.  Content should be a dict of mime types and data
        """
        self.raw_message(msg_type='display_data',
                         content={'data':data})

class OutputIPython(object):
    def __init__(self, _id, queue):
        self.cell_id=_id
        self.queue=queue
        self.stdout_queue=QueueOut(self.cell_id, self.queue, "stdout")
        self.stderr_queue=QueueOut(self.cell_id, self.queue, "stderr")
        self.pyout_queue=QueueOut(self.cell_id, self.queue, "pyout")
        self.message_queue=QueueOutMessage(self.cell_id, self.queue)
    
    def __enter__(self):
        # remap stdout, stderr, set up a pyout display handler.  Also, return the message queue so the user can put messages into the system
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        self.old_display = sys.displayhook

        sys.stderr = self.stderr_queue
        sys.stdout = self.stdout_queue
        
        def displayQueue(obj):
            if obj is not None:
                import __builtin__
                __builtin__._ = obj
                sys.stdout = self.pyout_queue
                print repr(obj)
                sys.stdout = self.stdout_queue

        sys.displayhook = displayQueue

        return self.message_queue
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout=self.old_stdout
        sys.stderr=self.old_stderr
        sys.displayhook = self.old_display
        #if exc_type is not None:
        #    import traceback
        #    self.stderr_queue.write(traceback.format_exc())
        # supress the exception
        return False

from multiprocessing import Pool, TimeoutError, Process, Queue, Lock, current_process

def run(db, fs, workers=1, poll_interval=0.1):
    """
    This function is the main function. Its responsibility is to
    query the database for more work to do and put messages back into the
    database. We do this so that we can batch the communication with the
    database, which may be running on a different server or sharded among
    several servers.

    This function also creates the worker pool for doing the actual
    computations.
    """
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
                 "header":{"msg_id":random.random()},
                 "parent_header":{"msg_id":_id},
                 "msg_type":"execute_reply",
                 "sequence":sequence[_id]}
            new_messages.append(msg)
            msg={'content': {"msg_type":"comp_end"},
                 "header":{"msg_id":random.random()},
                 "parent_header":{"msg_id":_id},
                 "msg_type":"extension",
                 "sequence":sequence[_id]+1}
            new_messages.append(msg)
            # should send back an execution_state: idle message too
            del sequence[_id]
            del results[_id]
        if len(new_messages)>0:
            db.add_messages(None, new_messages)


        time.sleep(poll_interval)


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

def execProcess(cell_id, code, output_handler):
    """Run the code, outputting into a pipe.
Meant to be run as a separate process."""
    # TODO: Have some sort of process limits on CPU time/memory
    code="import sys\nsys._sage_messages=MESSAGE\n"+code
    with output_handler as MESSAGE:
        try:
            exec code in {'MESSAGE': MESSAGE,'interact': interact}
        except:
            # Using IPython 0.11 - change code to: import IPython.core.ultratb
            # Using IPython 0.10:
            import ultraTB # Modified version of ultraTB that shipped with IPython 0.10 to acheive traceback output compatibility with 0.11
            (etype, evalue, etb) = sys.exc_info()
            # Using IPython 0.11 - change code to: err = IPython.core.ultratb.VerboseTB(include_vars = "false")
            # Using IPython 0.10:
            err = ultraTB.VerboseTB(include_vars = 0, tb_offset=1)
            pyerr_queue = QueueOut(cell_id, outQueue, "pyerr")
            try: # Check whether the exception has any further details
                error_value = evalue[0]
            except:
                error_value = ""
            # Using IPython 0.11 - change code to: pyerr_queue.raw_message("pyerr", {"ename": etype.__name__, "evalue": error_value, "traceback": err.structured_traceback(etype, evalue, etb, context = 3)})
            pyerr_queue.raw_message("pyerr", {"ename": etype.__name__, "evalue": error_value, "traceback": err.text(etype, evalue, etb, context = 3)})
    print "Done executing code: ", code
    
        

def execute_code(cell_id, code):
    """
    This function is executed by a worker process. It executes the
    given code in a separate process. This function may start a
    process on another computer, even, and communicate with that
    process over ssh.

    The result of this function is a list of messages in the global
    device queue.  These messages represent the output and results of
    executing the code.
    """
    # the fs variable is inherited from the parent process
    code = displayhook_hack(code)
    curr_dir=os.getcwd()
    tmp_dir=tempfile.mkdtemp()
    print "Temp files in "+tmp_dir
    #TODO: We should have a process that cleans up any children
    # that may hang around, similar to the sage-cleaner process.
    oldDaemon=current_process().daemon
    # Daemonic processes cannot create children
    current_process().daemon=False
    os.chdir(tmp_dir)
    # we need the output handler here so we can add messages about files later
    output_handler=OutputIPython(cell_id, outQueue)
    p=Process(target=execProcess, args=(cell_id, code, output_handler))
    p.start()
    p.join()
    current_process().daemon=oldDaemon
    file_list=[]
    fslock.acquire() #TODO: do we need this lock?
    for filename in os.listdir(tmp_dir):
        file_list.append(filename)
        fs_file=fs.new_file(cell_id, filename)
        with open(filename) as f:
            fs_file.write(f.read())
        fs_file.close()
    fslock.release()
    if len(file_list)>0:
        output_handler.message_queue.message('files', {'files': file_list})
    os.chdir(curr_dir)
    shutil.rmtree(tmp_dir)

if __name__ == "__main__":
    # We don't use argparse because Sage has an old version of python.  This will probably be upgraded
    # sometime in the summer of 2011, and then we can move this to use argparse.
    from optparse import OptionParser
    parser = OptionParser(description="Run one or more devices to process commands from the client.")
    parser.add_option("--db", choices=["mongo","sqlite","sqlalchemy"], default="mongo", help="Database to use")
    parser.add_option("-w", type=int, default=1, dest="workers", help="Number of workers to start.")
    (sysargs, args) = parser.parse_args()

    import misc
    db, fs = misc.select_db(sysargs)
    outQueue=Queue()
    fslock=Lock() #TODO: do we need this lock?
    run(db, fs, workers=sysargs.workers)
