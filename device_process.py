r"""

The DEVICE process continuously polls the database for new cells and
evaluations on current sessions.  It also pulls messages from the
output queues and puts them into the database.

When the DEVICE starts up, it starts a queue manager and does a
serve_forever in order to get messages from the EXEC processes.  It
also sets up a shared secret for the EXEC output messages

.. note:: The EXEC processes all have the same shared secret for
   output messages.  This may lead to security problems if the
   EXEC_WORKER is compromised by the user code in the EXEC process.

Each time a new session is required for a computation, the DEVICE
starts up a DEVICE_WORKER process using a
:class:`multiprocessing.Pool`.  

The DEVICE_WORKER process creates a Listener object to communicate
with the EXEC process and starts the listener.  It then creates an SSH
connection to an unprivileged user and does something like::

    python
    import worker
    worker.exec_worker(MESSAGE_QUEUE, OUTPUT_QUEUE)

where ``MESSAGE_QUEUE`` and ``OUTPUT_QUEUE`` are both triples
``(address, port, password)`` (where address and password are strings and
port is an integer).

The EXEC_WORKER process creates a managed queue that hooks up to the
``OUTPUT_QUEUE`` manager and also creates a Client object that connects
to the Listener ``MESSAGE_QUEUE``.

Messages to the EXEC_WORKER process have the form ``('command',
dict_of_options)`` or ``('user', execute_request_JSON_message)``.

The EXEC_WORKER process sets up a temporary directory, sets up the output
object (which points the passed queue), and starts an EXEC process

The EXEC process listens for messages indicating either
``timeout_change`` commands or commands to execute in the user
namespace.  The EXEC process is responsible for sending back
``execute_reply`` messages through the global queue back to the DEVICE
process.  The EXEC process handles any errors that occur in the user
code by forming an error status message back.

.. todo::

  Untrusted:
  * Create an untrusted DB class which establishes a connection to the trusted DB server
  * set rlimits when we fork a DEVICE_WORKER process

  Trusted:
  * Create a trusted DB server class
  * Start up device and give a password for DB authentication

"""


import sys, time, traceback, StringIO, contextlib, random, uuid
import interact

user_code="""
import sys
sys._sage_messages=MESSAGE
def _get_interact_function(id):
    import interact
    return interact._INTERACTS[id]
"""

def log(device_id, code_id=None, message=None):
    print "%s   %s: %s"%(device_id,code_id, message)

class QueueOut(StringIO.StringIO):
    def __init__(self, session, queue, parent_header=None):
        StringIO.StringIO.__init__(self)
        self.session=session
        self.queue=queue
        self.parent_header=parent_header

    def raw_message(self, msg_type, content):
        """
        Send a message where you can change the outer IPython msg_type and completely specify the content.
        """
        msg = {'msg_type': msg_type,
               'parent_header': self.parent_header,
               # We don't transmit the session id in the header since
               # it should already be in the parent_header
               'header': {'msg_id':unicode(uuid.uuid4())},
               'content': content}
        self.queue.put(msg)
        sys.__stdout__.write("USER MESSAGE PUT IN QUEUE: %s\n"%(msg))

class ChannelQueue(QueueOut):
    def __init__(self, session, queue, channel, parent_header=None):
        QueueOut.__init__(self, session=session, queue=queue, parent_header=parent_header)
        self.channel=channel

    def write(self, output):
        self.raw_message(msg_type='stream',
                         content={'data': output, 'name':self.channel})

class QueueOutMessage(QueueOut):
    def __init__(self, session, queue):
        QueueOut.__init__(self, session=session, queue=queue)

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
    def __init__(self, session, queue):
        self.session=session
        self.queue=queue
        self.stdout_queue=ChannelQueue(self.session, self.queue, "stdout")
        self.stderr_queue=ChannelQueue(self.session, self.queue, "stderr")
        self.message_queue=QueueOutMessage(self.session, self.queue)

    def set_parent_header(self, parent_header):
        """
        Set the parent header on all output queues
        """
        for q in [self.stdout_queue, self.stderr_queue, self.message_queue]:
            q.parent_header=parent_header
    
    def __enter__(self):
        # remap stdout, stderr, set up a pyout display handler.  Also, return the message queue so the user can put messages into the system
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        self.old_display = sys.displayhook

        sys.stderr = self.stderr_queue
        sys.stdout = self.stdout_queue
        
        # TODO: this needs to be meshed nicely with the Sage display hook
        def displayQueue(obj):
            if obj is not None:
                import __builtin__
                __builtin__._ = obj
                self.message_queue.raw_message("pyout", 
                                               {"data": {"text/plain": repr(obj)}})

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

from multiprocessing import Pool, TimeoutError, Process, Queue, Lock, current_process, Manager

import uuid

def device(db, fs, workers, interact_timeout, poll_interval=0.1, resource_limits=None):
    """
    This function is the main function. Its responsibility is to
    query the database for more work to do and put messages back into the
    database. We do this so that we can batch the communication with the
    database, which may be running on a different server or sharded among
    several servers.  Another option is to the worker processes doing
    the database communication once a session is set up.  We don't
    know which is better for a highly scalable system.

    This function also creates the worker pool for doing the actual
    computations.
    """
    device_id=unicode(uuid.uuid4())
    log(device_id, message="Starting device loop for device %s..."%device_id)
    pool=Pool(processes=workers)
    sessions={}
    from collections import defaultdict
    sequence=defaultdict(int)


    manager = Manager()
    log("Getting new messages")
    while True:
        # limit new sessions to the number of free workers we have
        # TODO: be more intelligent about how many new sessions I can get
        for X in db.get_input_messages(device=device_id, limit=workers-len(sessions)):
            # this gets both new session requests as well as execution
            # requests for current sessions.
            session=X['header']['session']
            if session not in sessions:
                # session has not been set up yet
                log(device_id, session,message="evaluating '%s'"%X['content']['code'])

                msg_queue=manager.Queue() # TODO: make this a pipe
                sessions[session]={'messages': msg_queue,
                                   'worker': pool.apply_async(worker,
                                                              (session,
                                                               msg_queue,
                                                               resource_limits))}
            # send execution request down the queue.
            sessions[session]['messages'].put(('exec',X))
            log(device_id, session, message="sent execution request")
        # Get whatever sessions are done
        finished=set(i for i, r in sessions.iteritems() if r['worker'].ready())
        new_messages=[]
        last_message={}
        # TODO: should just get until there is a Queue.Empty error,
        # TODO: but should also have a max timeout for the message loop
        # TODO: or maybe just a max number of messages we can handle in one loop
        while not outQueue.empty():
            msg=outQueue.get()
            session = msg['parent_header']['session']
            last_msg=last_message.get(session)
            # Consolidate session messages of stderr or stdout
            # channels
            if (last_msg is not None
                and msg['msg_type'] == 'stream' and last_msg['msg_type']=='stream'
                and msg['content']['name'] in ('stdout', 'stderr')
                and msg['content']['name']==last_msg['content']['name']):

                last_msg['content']['data']+=msg['content']['data']
            else:
                msg['sequence']=sequence[session]
                sequence[session]+=1
                new_messages.append(msg)
                last_message[session]=msg

            if (msg['msg_type']=='extension' 
                and msg['content']['msg_type']=="interact_start"):
                sessions[session]['messages'].put(('timeout_change', interact_timeout))

        # delete the output that I'm finished with
        for session in finished:
            # this message should be sent at the end of an execution
            # request, not at the end of a session
            msg={'content': {"msg_type":"session_end"},
                 "header":{"msg_id":unicode(uuid.uuid4())},
                 "parent_header":{"session":session},
                 "msg_type":"extension",
                 "sequence":sequence[session]}
            new_messages.append(msg)
            # should send back an execution_state: idle message too
            del sequence[session]
            del sessions[session]
            db.close_session(device=device_id, session=session)
        if len(new_messages)>0:
            db.add_messages(id=None, messages=new_messages)


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

def execProcess(cell_id, message_queue, output_handler, resource_limits):
    """Run the code, outputting into a pipe.
Meant to be run as a separate process."""
    # TODO: Have some sort of process limits on CPU time/memory
    import Queue
    global user_code
    # timeout has to be long enough so we don't miss the first message
    # and so that we don't miss a command that may come after the first message.
    # thus, this default timeout should be much longer than the polling interval
    # for the output queue
    timeout=1
    execution_count=1
    empty_times=0

    if resource_limits is None:
        resource_limits=[]
    from resource import setrlimit
    for r,l in resource_limits:
        setrlimit(r, l)

    while True:
        try:
            msg=message_queue.get(timeout=timeout)
        except Queue.Empty:
            empty_times+=1
            if empty_times>=2:
                break
            else:
                continue

        if msg[0]=="timeout_change":
            timeout=msg[1]
            continue
        elif msg[0]=="exec":
            msg=msg[1]
            
        # Now msg is an IPython message for the user session
        if msg['msg_type']!="execute_request":
            raise ValueError("Received invalid message: %s"%(msg,))

        # TODO: we probably ought not prepend our own code, in case the user has some 
        # "from __future__ import ..." statements, which *must* occur at the top of the code block
        # alternatively, we could move any such statements above our statements
        code=user_code+msg['content']['code']
        code = displayhook_hack(code)
        # always add a newline to avoid this bug in Python versions < 2.7: http://bugs.python.org/issue1184112
        code += '\n'
        print "Executing: ",code
        output_handler.set_parent_header(msg['header'])
        with output_handler as MESSAGE:
            try:
                exec code in {'MESSAGE': MESSAGE,
                              'interact': interact}
                # I've commented out fields we aren't using below to
                # save bandwidth
                output_handler.message_queue.raw_message("execute_reply", 
                                                         {"status":"ok",
                                                          #"execution_count":execution_count,
                                                          #"payload":[],
                                                          #"user_expressions":{},
                                                          #"user_variables":{}
                                                          })

            except:
                # Using IPython 0.11 - change code to: import IPython.core.ultratb
                # Using IPython 0.10:
                import ultraTB # Modified version of ultraTB that shipped with IPython 0.10 to acheive traceback output compatibility with 0.11
                (etype, evalue, etb) = sys.exc_info()
                # Using IPython 0.11 - change code to: err = IPython.core.ultratb.VerboseTB(include_vars = "false")
                # Using IPython 0.10:
                err = ultraTB.VerboseTB(include_vars = 0, tb_offset=1)
                try: # Check whether the exception has any further details
                    error_value = evalue[0]
                except:
                    error_value = ""
                # Using IPython 0.11 - change code to:
                # err_msg={"ename":
                # etype.__name__, "evalue": error_value,
                # "traceback": err.structured_traceback(etype,
                # evalue, etb, context = 3)})

                #TODO: docs have this as exc_name and exc_value,
                #but it seems like IPython returns ename and
                #evalue!

                err_msg={"ename": etype.__name__, "evalue": error_value,
                         "traceback": err.text(etype, evalue, etb, context=3)}
                #output_handler.message_queue.raw_message("pyerr",err_msg)
                err_msg.update(status="error",
                               execution_count=execution_count)
                output_handler.message_queue.raw_message("execute_reply", 
                                                         err_msg)

            execution_count+=1

        print "Done executing code: ", code
    
        

def worker(session, message_queue, resource_limits):
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
    curr_dir=os.getcwd()
    tmp_dir=tempfile.mkdtemp()
    print "Temp files in "+tmp_dir
    #TODO: We should have a process that cleans up any children
    # that may hang around, similar to the sage-cleaner process.
    oldDaemon=current_process().daemon
    # Daemonic processes cannot create children
    current_process().daemon=False
    os.chdir(tmp_dir)
    # we need the output handler here so we can add messages about
    # files later
    output_handler=OutputIPython(session, outQueue)
    # listen on queue and send send execution requests to execProcess
    args=(session, message_queue, output_handler, resource_limits)

    p=Process(target=execProcess, args=args)
    p.start()
    p.join()
    current_process().daemon=oldDaemon
    file_list=[]
    fslock.acquire() #TODO: do we need this lock?
    for filename in os.listdir(tmp_dir):
        file_list.append(filename)
        fs_file=fs.new_file(session, filename)
        with open(filename) as f:
            fs_file.write(f.read())
        fs_file.close()
    fslock.release()
    if len(file_list)>0:
        output_handler.message_queue.message('files', {'files': file_list})
    os.chdir(curr_dir)
    shutil.rmtree(tmp_dir)


def run_zmq(db_address, fs_address, workers, interact_timeout, resource_limits=None):
    """
    Set up things and call the main device process
    """
    import db_zmq, filestore
    import zmq
    context=zmq.Context()
    db = db_zmq.DB(context=context, socket=dbaddress)
    fs = filestore.FileStoreZMQ(context=context, socket=fsaddress)
    #fs = filestore.FileStoreZMQ(socket=fsaddress)
    device(db=db, fs=fs, workers=workers, interact_timeout=interact_timeout, 
           resource_limits=resource_limits)

if __name__ == "__main__":
    # We don't use argparse because Sage has an old version of python.  This will probably be upgraded
    # sometime in the summer of 2011, and then we can move this to use argparse.
    from optparse import OptionParser
    parser = OptionParser(description="Run one or more devices to process commands from the client.")
    parser.add_option("--db", choices=["mongo","sqlite","sqlalchemy", "zmq"], default="zmq", help="Database to use")
    parser.add_option("--dbaddress", dest="dbaddress", help="ZMQ address for db connection; only for --db zmq")
    parser.add_option("--fsaddress", dest="fsaddress", help="ZMQ address for fs connection; only for --db zmq")
    parser.add_option("-w", type=int, default=1, dest="workers",
                      help="Number of workers to start")
    parser.add_option("-t", "--timeout", type=int, default=60,
                      dest="interact_timeout",
                      help="Worker idle timeout if an interact command is detected")
    parser.add_option("--cpu", type=float, default=-1,
                      dest="cpu_limit",
                      help="CPU time (seconds) allotted to each session (hard limit)")
    parser.add_option("--mem", type=float, default=-1,
                      dest="memory_limit",
                      help="Memory (MB) allotted to each session (hard limit)")
    (sysargs, args) = parser.parse_args()

    resource_limits=[]
    if sysargs.cpu_limit>=0:
        resource_limits.append((resource.RLIMIT_CPU, (sysargs.cpu_limit, sysargs.cpu_limit)))
    if sysargs.memory_limit>=0:
        mem_bytes=sysargs.memory_limit*1048576
        resource_limits.append((resource.RLIMIT_AS, (mem_bytes, mem_bytes)))

    outQueue=Queue()
    import misc
    import zmq
    db, fs = misc.select_db(sysargs,context=zmq.Context())

    device(db=db, fs=fs, workers=sysargs.workers, interact_timeout=sysargs.interact_timeout, resource_limits=resource_limits)
