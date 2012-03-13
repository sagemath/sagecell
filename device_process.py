r"""
The DEVICE process continuously polls the database for new cells and
evaluations on current sessions. Each time a new session is required
for a computation, the DEVICE starts up a DEVICE_WORKER process by
executing it in a :class:`multiprocessing.pool.multiprocessing.Pool`.
This pool has a limited number of workers, so there is a maximum
number of simultaneous active sessions.

The DEVICE_WORKER creates a temporary directory for the executed code
to use for any files it creates. It then starts an EXEC process that
executes the code.

The EXEC process receives execution requests (both the initial message
and updates to interacts in the session) through a queue created by the
DEVICE_WORKER. Messages to the EXEC_WORKER process have the form
``('command', dict_of_options)``.

When the EXEC process receives an execution request, it runs it
in a minimal namespace. Any messages to stdout or stderr are
redirected into a global output queue. The EXEC process is also
responsible for sending back ``execute_reply`` messages through
the global queue.

If the code contains an :doc:`interact </interact_protocol>`, it will
increase the time limit on the EXEC process so that, when the user
updates the interact, the update will be sent to that process.
Whenever an interact's internal code is executed, all output messages
from that execution will include a field containing the interact's ID
number, which tells the user's browser to place that output in a
location associated with the interact (probably below the interact
control).

The DEVICE process polls the global output queue for messages. When it
receives a message, it inserts it into the database for the web server
to read.

.. warning::
  You can specify resource limits, but please note that the memory limit is *not* enforced on OSX, as RLIMIT_AS is a suggestion, not a hard cap.
"""

import sys, time, traceback, StringIO, contextlib, random, uuid
import util
import hmac
from util import log
# TODO: be smart about importing json
import json
from json import dumps, loads
from hashlib import sha1
import interact_sagecell
import sagecell_exec_config as CONFIG

try:
    import sage
    import sage.all
    CONFIG.EMBEDDED_MODE["enable_sage"] = enable_sage = True
    # The first plot takes about 2 seconds to generate (presumably
    # because lots of things, like matplotlib, are imported).  We plot
    # something here so that worker processes don't have this overhead
    # (I think what is happening is that we are priming the import
    # cache here).  After this fix, worker processes' first plot takes
    # something like 0.6 seconds (instead of 2 seconds).
    sage.all.plot(lambda x: x, (0,1)).save(StringIO.StringIO())
except ImportError as e:
    CONFIG.EMBEDDED_MODE["enable_sage"] = enable_sage = False

user_code="""
import sys
sys._sage_messages=MESSAGE
sys._sage_upload_file_pipe=_file_upload_send
def _update_interact(id, control_vals):
    import interact_sagecell
    interact_info = interact_sagecell._INTERACTS[id]
    kwargs = interact_info["state"].copy()
    controls = interact_info["controls"]
    for var,value in control_vals.items():
        c = controls[var]
        kwargs[var] = c.adapter(value, interact_info["globals"])
        if c.preserve_state:
            interact_info["state"][var]=kwargs[var]

    interact_sagecell._INTERACTS[id]["function"](control_vals=kwargs)
"""

user_code_sage="""
from sage.all import *
from sage.calculus.predefined import x
from sage.misc.html import html
from sage.server.support import help
from sagenb.misc.support import automatic_names
sage.misc.session.init()

# Ensure unique random state after forking
set_random_seed()

#try:
#    attach(os.path.join(os.environ['DOT_SAGE'], 'init.sage'))
#except (KeyError, IOError):
#    pass


# sagecell specific code:
from interact_sagecell import * # override the interact functionality
from interact_compatibility import * # override the interact functionality
import sage.misc.misc
import sagecell_exec_config
sage.misc.misc.EMBEDDED_MODE=sagecell_exec_config.EMBEDDED_MODE
"""+user_code

class QueueOut(StringIO.StringIO):
    """
    A class for sending messages to a global message queue,
    later to be transfered to the database.

    The message protocol is the same as IPython's protocol
    (see :ref:`ipython:messaging`), but with an additional
    ``extension`` message type, whose contents are
    customizable (usually another IPython-style message with a
    custom message type).

    :arg str session: the session ID to include in a message's header
    :arg multiprocessing.Queue queue: a global message queue
    :arg dict parent_header: the header of the message to which
        messages from this object are the reply
    """
    def __init__(self, session, queue, parent_header=None):
        StringIO.StringIO.__init__(self)
        self.session=session
        self.queue=queue
        self.parent_header=parent_header
        self.output_block=None

    def raw_message(self, msg_type, content):
        """
        Send a message where you can change the outer
        IPython ``msg_type`` and completely specify the content.

        :arg str msg_type: the message type
        :arg dict content: the ``content`` field of the IPython message
        """
        # We don't use uuid4() for the msg_id since there is a bug in
        # older python versions (fixed in 2.6.6, I think) on OSX
        # that leads to each session having exactly the same sequence of UUIDs
        # see http://bugs.python.org/issue8621
        msg_id = random.randrange(sys.maxint)
        msg = {'msg_type': msg_type,
               'parent_header': self.parent_header,
               # We don't transmit the session id in the header since
               # it should already be in the parent_header
               'header': {'msg_id':unicode(msg_id)},
               'output_block': self.output_block,
               'content': content}
        msg=dumps(msg)
        self.queue.put(msg)
        log("USER MESSAGE PUT IN QUEUE: %r\n"%(msg))

class ChannelQueue(QueueOut):
    """
    A sub-class of :class:`QueueOut` which, when written to as an
    :class:`StringIO.StringIO` object, adds an IPython-style
    stream message to the queue.

    :arg str session: the session ID to include in a message's header
    :arg multiprocessing.Queue queue: a global message queue
    :arg str channel: the name of the channel (such as ``"stdout"``)
    :arg dict parent_header: the header of the message to which
        messages from this object are the reply
    """
    def __init__(self, session, queue, channel, parent_header=None):
        QueueOut.__init__(self, session=session, queue=queue, parent_header=parent_header)
        self.channel=channel

    def write(self, output):
        """
        Write some data to the output stream.

        :arg str output: the string to add to the stream
        """
        self.raw_message(msg_type='stream',
                         content={'data': output, 'name':self.channel})

class QueueOutMessage(QueueOut):
    """
    A class that will send IPython messages with custom types,
    inside another message with the ``extension`` message type.

    :arg str session: the session ID to include in a message's header
    :arg multiprocessing.Queue queue: a global message queue
    :arg dict parent_header: the header of the message to which
        messages from this object are the reply
    """

    def __init__(self, session, queue, parent_header=None):
        QueueOut.__init__(self, session=session, queue=queue)

    def message(self, msg_type, content):
        """
        Send a user message with a specific type.  This will be wrapped in an IPython ``extension`` message and added to the queue.

        :arg msg_type: custom message type
        :type msg_type: str
        :arg content: The contents of the custom message
        :type content: dict
        """
        self.raw_message(msg_type='extension',
                         content={'content': content, 'msg_type': msg_type})

    def display(self, data):
        """
        Send a ``display_data`` message.

        :arg dict data: a dict of MIME types and data
        """
        self.raw_message(msg_type='display_data',
                         content={'data':data})

class OutputIPython(object):
    """
    A context wrapper that causes any messages written to stdout to
    be redirected into the queue as IPython-style messages, to be
    written to the client.

    :arg str session: the session ID to include in a message's header
    :arg multiprocessing.Queue queue: a global message queue
    :arg dict parent_header: the header of the message to which
        messages from this object are the reply
    """
    def __init__(self, session, queue, parent_header=None):
        self.session=session
        self.queue=queue
        self.stdout_queue=ChannelQueue(self.session, self.queue, "stdout", parent_header)
        self.stderr_queue=ChannelQueue(self.session, self.queue, "stderr", parent_header)
        self.message_queue=QueueOutMessage(self.session, self.queue, parent_header)
        self.out_stack=[]

    def set_parent_header(self, parent_header):
        """
        Set the parent header on all output queues

        :arg dict parent_header: the new parent header
        """
        for q in [self.stdout_queue, self.stderr_queue, self.message_queue]:
            q.parent_header=parent_header

    def push_output_id(self, block):
        """
        Add an output block ID to the output stack. When a message is sent
        with one or more IDs in the stack, it will send the ID at the top
        of the stack as the ``output_block`` field of the message. This
        tells the client where to place the output (for example, in the
        case of an interact whose output is always directly below the
        interact controls). If a message is sent with the output stack
        empty (the default state), the ``output_block`` field is set to
        ``None`` and the message is assumed to go to the client's stdout.

        :arg str block: the ID of the output block (in the case of an
            interact, the interact ID)
        """
        self.out_stack.append(block)
        for q in [self.stdout_queue, self.stderr_queue, self.message_queue]:
            q.output_block=block

    def pop_output_id(self):
        """
        Pop one item off of the output stack and restore output to the
        previous block (or stdout if the stack is empty).
        """
        if len(self.out_stack)==0:
            return
        self.out_stack.pop()
        block=self.out_stack[-1] if len(self.out_stack)>0 else None
        for q in [self.stdout_queue, self.stderr_queue, self.message_queue]:
            q.output_block=block
    
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

        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout=self.old_stdout
        sys.stderr=self.old_stderr
        sys.displayhook = self.old_display
        #if exc_type is not None:
        #    import traceback
        #    self.stderr_queue.write(traceback.format_exc())
        # supress the exception
        return False

from multiprocessing import Pool, TimeoutError, Process, Queue, current_process, Manager, Pipe
from raw_queue import RawQueue
import uuid

def device(db, fs, workers, interact_timeout, keys, poll_interval=0.1, resource_limits=None):
    """
    This function is the main function. Its responsibility is to
    query the database for more work to do and put messages back into the
    database. We do this so that we can batch the communication with the
    database, which may be running on a different server or shared among
    several servers.  Another option is to the worker processes doing
    the database communication once a session is set up.  We don't
    know which is better for a highly scalable system.

    This function also creates the worker pool for doing the actual
    computations.

    :arg db_zmq.DB db: the untrusted database adaptor
    :arg filestore.FileStoreZMQ fs: the untrusted filestore adaptor
    :arg int workers: the number of worker processes to start
        in the pool
    :arg int interact_timeout: the timeout (in seconds) for a session
        containing an interact
    :arg tuple keys: a tuple of two strings to use to generate the
        shared secrets for the database and filestore
    :arg float poll_interval: the time between each iteration of polling
        the database and queue
    :arg list resource_limits: list of tuples of the form
        ``(resource, limit)``, to be passed as arguments to
        :func:`resource.setrlimit` in each EXEC process
    """
    device_id=unicode(uuid.uuid4())
    log("Starting device loop for device %s..."%device_id, device_id)
    db.register_device(device=device_id, account=None, workers=workers, pgid=os.getpgid(0))
    pool=Pool(processes=workers)
    sessions={}
    from collections import defaultdict
    sequence=defaultdict(int)

    manager = Manager()
    log("Getting new messages")
    hmacs={}
    while True:
        # TODO: be more intelligent about how many new sessions I can get
        # one option is to make limit=3*(workers-len(sessions)))
        for X in db.get_input_messages(device=device_id, limit=-1):
            # this gets both new session requests as well as execution
            # requests for current sessions.
            session=X['header']['session']
            if session not in sessions:
                # session has not been set up yet
                log("evaluating %r"%X['content']['code'], device_id+' '+session)
                while not db.create_secret(session=session):
                    time.sleep(0.1)

                keys[0]=sha1(keys[0]).digest()
                hmacs[session]=hmac.new(keys[0],digestmod=sha1)
                while not fs.create_secret(session=session):
                    time.sleep(0.1)
                keys[1]=sha1(keys[1]).digest()
                fs_secret={}
                fs_secret['']=keys[1]
                while not fs.create_secret(session=session+'upload'):
                    time.sleep(0.1)
                keys[1]=sha1(keys[1]).digest()
                fs_secret['upload']=keys[1]
                msg_queue=manager.Queue()
                args=(session, msg_queue, resource_limits, fs_secret)
                sessions[session]={'messages': msg_queue,
                                   'worker': pool.apply_async(worker,args),
                                   'parent_header': X['header']}
            # send execution request down the queue.
            sessions[session]['messages'].put(('exec',X))
            log("sent execution request", device_id+' '+session)
        # Get whatever sessions are done
        finished=set(i for i, r in sessions.iteritems() if r['worker'].ready())
        new_messages=[]
        last_message={}
        # TODO: should just get until there is a Queue.Empty error,
        # TODO: but should also have a max timeout for the message loop
        # TODO: or maybe just a max number of messages we can handle in one loop
        while not outQueue.empty():
            # TODO: don't use Queue, which unpickles the message.  Instead, use some sort of Pipe which just extracts bytes.
            try:
                # make sure we can decode the message
                msg=loads(outQueue.get())
            except Exception as e:
                # ignore the message
                # TODO: send a message to the user; can we extract a session identifier?
                log("Exception occurred while reading message: %s"%(msg,))
                continue
            try:
                session = msg['parent_header']['session']
                last_msg=last_message.get(session)
                # Consolidate session messages of stderr or stdout to same output block
                # channels
                if (last_msg is not None
                    and msg['msg_type'] == 'stream' and last_msg['msg_type']=='stream'
                    and msg['content']['name'] in ('stdout', 'stderr')
                    and msg['content']['name']==last_msg['content']['name']
                    and msg['output_block'] == last_msg['output_block']):

                    last_msg['content']['data']+=msg['content']['data']
                else:
                    msg['sequence']=sequence[session]
                    sequence[session]+=1
                    new_messages.append(msg)
                    last_message[session]=msg
            except KeyError:
                # something was formatted wrongly in msg, or some other problem happened with formatting the message
                # TODO: send an error back to the user
                continue
         # delete the output that I'm finished with
        for session in finished:
            msg={'content': {"msg_type":"session_end"},
                 "header":{"msg_id":unicode(uuid.uuid4())},
                 "parent_header":sessions[session]['parent_header'],
                 "msg_type":"extension",
                 "output_block":None,
                 "sequence":sequence[session]}
            new_messages.append(msg)
            del sequence[session]
            del sessions[session]
        if len(new_messages)>0:
            db.add_messages(messages=new_messages, hmacs=hmacs)
        for session in finished:
            db.close_session(device=device_id, session=session,hmac=hmacs[session])
            del hmacs[session]
        time.sleep(poll_interval)


def unicode_str(obj, encoding='utf-8'):
    """
    Takes an object and returns a Unicode human-readable representation.

    :arg obj: the object to encode into Unicode
    :arg str encoding: the encoding to use
    """
    if isinstance(obj, str):
        return obj.decode(encoding, 'ignore')
    elif isinstance(obj, unicode):
        return obj
    return unicode(obj)

def displayhook_hack(string):
    u"""
    Modified version of string so that ``exec``\u2019ing it results in
    displayhook possibly being called.

    :arg str string: the code string to modify
    :returns: the modified code
    :rtype: str
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
        # or are comments
        while (len(string[i])==0 # empty line
               or string[i][0] in ' \t#' # indented or comment
               or (i>0 and len(string[i-1])>0 and string[i-1][-1]=='\\')): # previous line is a continuation
            i -= 1

        if i==-1: i=0
        final_lines = unicode_str('\n'.join(string[i:]))
        if not (final_lines.startswith('def ') or final_lines.startswith('class ')):
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

def execProcess(session, message_queue, output_handler, resource_limits, sysargs, fs_secret):
    """
    Run the code, outputting into a pipe.
    Meant to be run as a separate process.

    :arg str session: the ID of the session running the code
    :arg multiprocessing.Queue message_queue: a queue through which
        this process will be passed input messages
    :arg device_process.OutputIPython output_handler: the context wrapper in which
        to execute the code
    :arg list resource_limits: list of tuples of the form
        ``(resource, limit)``, to be passed as arguments to
        :func:`resource.setrlimit`.
    """
    # we need a new context since we just forked
    global fs
    fs.new_context()
    from Queue import Empty
    global user_code
    # Since the user can set a timeout, we safeguard by having a maximum timeout
    MAX_TIMEOUT=60
    timeout=0.1

    upload_recv, upload_send=Pipe()
    file_parent, file_child=Pipe()
    file_upload_process=Process(target=upload_files, args=(upload_recv, file_child, session, fs_secret['upload']))
    file_upload_process.start()

    fs_hmac=hmac.new(fs_secret[''], digestmod=sha1)
    del fs_secret
    if resource_limits is None:
        resource_limits=[]
    from resource import setrlimit
    for r,l in resource_limits:
        setrlimit(r, l)
    while True:
        try:
            msg=message_queue.get(timeout=timeout)
        except Empty:
            break

        if msg[0]=="exec":
            msg=msg[1]
        else:
            break

        # Now msg is an IPython message for the user session
        if msg['msg_type']!="execute_request":
            raise ValueError("Received invalid message: %s"%(msg,))

        # TODO: we probably ought not prepend our own code, in case the user has some 
        # "from __future__ import ..." statements, which *must* occur at the top of the code block
        # alternatively, we could move any such statements above our statements
        code=""

        CONFIG.EMBEDDED_MODE["sage_mode"] =  sage_mode = msg['content']['sage_mode']
        if enable_sage and sage_mode:
            from sage.misc.preparser import preparse_file
            code = user_code_sage + "\n" + preparse_file(msg['content']['code'].encode('utf8'))
        elif sage_mode:
            code = "print 'NOTE: Sage Mode is unavailable, which may cause errors if using Sage-specific syntax.'\n" + user_code + msg['content']['code']
        else:
            code = user_code + msg['content']['code']
        code = displayhook_hack(code)
        # always add a newline to avoid this bug in Python versions < 2.7: http://bugs.python.org/issue1184112
        code += '\n'
        log("Executing: %r"%code)
        output_handler.set_parent_header(msg['header'])
        old_files=dict([(f,os.stat(f).st_mtime) for f in os.listdir(os.getcwd())])
        if 'files' in msg['content']:
            for filename in msg['content']['files']:
                with open(filename,'w') as f:
                    fs.copy_file(f,filename=filename, session=session, hmac=fs_hmac)
                old_files[filename]=-1
        file_parent.send(True)
        with output_handler as MESSAGE:
            try:
                locals={'MESSAGE': MESSAGE,
                        'interact_sagecell': interact_sagecell,
                        '_file_upload_send': upload_send}
                if enable_sage and sage_mode:
                    locals['sage'] = sage

                exec code in locals
                # I've commented out fields we aren't using below to
                # save bandwidth
                output_handler.message_queue.raw_message("execute_reply", 
                                                         {"status":"ok",
                                                          #"payload":[],
                                                          #"user_expressions":{},
                                                          #"user_variables":{}
                                                          })
                # technically should send back an execution_state: idle message too

            except:

                (etype, evalue, etb) = sys.exc_info()

                # Modified version of ultraTB from IPython 0.10 with IPython 0.11 tracebacks
                import ultraTB_10
                err = ultraTB_10.VerboseTB(include_vars = 0, tb_offset=1)
                
                # Using IPython 0.11 - change code to: import IPython.core.ultratb
                # Using IPython 0.11 - change code to: err = IPython.core.ultratb.VerboseTB(include_vars = "false")

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
                         "traceback": err.text(etype, evalue, etb, context=3),
                         "status": "error"}
                output_handler.message_queue.raw_message("execute_reply", 
                                                         err_msg)
        upload_send.send_bytes(json.dumps({'msg_type': 'end_exec'}))
        new_files=file_parent.recv()
        old_files.update(new_files)
        # TODO: security implications here calling something that the user had access to.
        timeout=max(0,min(float(interact_sagecell.__sage_cell_timeout__), MAX_TIMEOUT))

        file_list=[]
        for filename in os.listdir(os.getcwd()):
            if filename not in old_files or old_files[filename]!=os.stat(filename).st_mtime:
                file_list.append(filename)
                try:
                    with open(filename) as f:
                        fs.create_file(f, session=session, filename=filename, hmac=fs_hmac)
                except Exception as e:
                    sys.stdout.write("An exception occurred: %s\n"%(e,))
        if len(file_list)>0:
            output_handler.message_queue.message('files', {'files': file_list})

        log("Done executing code: %r"%code)
    upload_send.send_bytes(json.dumps({'msg_type': 'end_session'}))
    file_upload_process.join()

def worker(session, message_queue, resource_limits, fs_secret):
    u"""
    This function is executed by a worker process. It executes the
    given code in a separate process. This function may start a
    process on another computer, even, and communicate with that
    process over SSH.

    The result of this function is a list of messages in the global
    device queue.  These messages represent the output and results of
    executing the code.

    :arg str session: the ID of the session running the code
    :arg multiprocessing.Queue message_queue: a queue through which
        this process will be passed input messages
    :arg list resource_limits: list of tuples of the form
        ``(resource, limit)``, to be passed as arguments to
        :func:`resource.setrlimit`.
    :arg str fs_secret: a string to serve as the initial secret message
        with which to call :func:`hmac.new` and communicate with the
        trusted filestore object over \xd8MQ. The trusted filestore
        must be given the same secret.
    """
    curr_dir=os.getcwd()
    tmp_dir=tempfile.mkdtemp()
    log("Temp files in "+tmp_dir)
    oldDaemon=current_process().daemon
    # Daemonic processes cannot create children
    current_process().daemon=False
    os.chdir(tmp_dir)
    output_handler=OutputIPython(session, outQueue)
    output_handler.set_parent_header({'session':session})
    args=(session, message_queue, output_handler, resource_limits, sysargs, fs_secret)
    p=Process(target=execProcess, args=args)
    p.start()
    p.join()
    current_process().daemon=oldDaemon
    os.chdir(curr_dir)
    shutil.rmtree(tmp_dir)

def upload_files(upload_recv, file_child, session, fs_secret):
    """
    The user can pass in a list of filenames as a json message.  These will get uploaded.
    When the upload_queue gets an "end_exec" message, it then sends the hmac down the 
    file_child pipe and exits
    """
    # for some reason, doing fs.new_context hangs on the statement when fs._xreq is assigned
    from filestore import FileStoreZMQ
    global fs
    fs=FileStoreZMQ(fs.address)

    fs_hmac=hmac.new(fs_secret, digestmod=sha1)
    log("starting fs secret for upload_files: %r"%fs_hmac.digest())
    del fs_secret

    file_list={}
    while True:
        # The problem with using a Pipe is that if the user is writing file messages from several
        # threads, there can be a problem.  Maybe we should use normal sockets or a special file?
        try:
            msg=json.loads(upload_recv.recv_bytes())
        except Exception as e:
            log("An exception occurred in receiving file message: %s\n"%(e,))
            upload_recv.send_bytes("error")
            continue
        # note: check for basestring since json stuff comes back as unicode strings
        if isinstance(msg, list) and all(isinstance(i,basestring) for i in msg):
            # TODO: sanitize pathnames to only upload files below the current directory
            for filename in msg:
                try:
                    file_list[filename]=os.stat(filename).st_mtime
                    with open(filename) as f:
                        # TODO: for some reason, switching the cell_id below to be session=session causes an authentication error
                        # TODO: figure out why.
                        fs.create_file(f, cell_id=session, session_auth_channel='upload', filename=filename, hmac=fs_hmac)
                except Exception as e:
                    log("An exception occurred in uploading files: %s\n"%(e,))
            upload_recv.send_bytes("success")
        elif isinstance(msg, dict) and 'msg_type' in msg and msg['msg_type']=='end_exec':
            file_child.send(file_list)
            # we recv just to make sure that we are synchronized with the execing process
            file_child.recv()
        elif isinstance(msg, dict) and 'msg_type' in msg and msg['msg_type']=='end_session':
            break


def run_zmq(db_address, fs_address, workers, interact_timeout, resource_limits=None):
    u"""
    Set up things and call the main device process

    :arg str db_address: the URL (including port number) that the untrusted
        database adaptor can use to communicate over \xd8MQ with the trusted
        database adaptor
    :arg str fs_address: the URL for the filestore's \xd8MQ connection
    :arg int workers: the number of workers allow to run simultaneously
    :arg int interact_timeout: the timeout (in seconds) for a session
        containing an interact
    :arg list resource_limits: list of tuples of the form
        ``(resource, limit)``, to be passed as arguments to
        :func:`resource.setrlimit` in each EXEC process
    """
    import db_zmq, filestore
    import zmq
    context=zmq.Context()
    db = db_zmq.DB(context=context, socket=dbaddress)
    fs = filestore.FileStoreZMQ(context=context, socket=fsaddress)
    device(db=db, fs=fs, workers=workers, interact_timeout=interact_timeout, 
           resource_limits=resource_limits)

if __name__ == "__main__":
    # We don't use argparse because Sage has an old version of python.  This will probably be upgraded
    # sometime in the summer of 2011, and then we can move this to use argparse.
    import os
    os.setsid()
    print "PROCESS GROUP ID: ",os.getpgid(0)
    from optparse import OptionParser
    parser = OptionParser(description="Run one or more devices to process commands from the client.")
    parser.add_option("--db", choices=["mongo","sqlite","sqlalchemy", "zmq"], default="mongo", help="Database to use")
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
    parser.add_option("--keyfile", dest="keyfile")
    parser.add_option("-q", action="store_true", dest="quiet", help="Turn off most logging")
    (sysargs, args) = parser.parse_args()

    if sysargs.quiet:
        util.LOGGING=False

    import resource
    resource_limits=[]
    if sysargs.cpu_limit>=0:
        resource_limits.append((resource.RLIMIT_CPU, (sysargs.cpu_limit, sysargs.cpu_limit)))
    if sysargs.memory_limit>=0:
        mem_bytes=sysargs.memory_limit*(2**20)
        # on OSX 10.7, RLIMIT_AS is an alias for RLIMIT_RSS, which is just a *suggestion* 
        # about how much memory to use.
        resource_limits.append((resource.RLIMIT_AS, (mem_bytes, mem_bytes)))
        #resource_limits.append((resource.RLIMIT_DATA, (mem_bytes, mem_bytes)))
        #resource_limits.append((resource.RLIMIT_STACK, (mem_bytes, mem_bytes)))

    outQueue=RawQueue()

    filename=sysargs.keyfile
    with open(filename,"rb") as f:
        keys=[s.rstrip() for s in f.readlines()]
    os.remove(filename)

    import misc
    db, fs = misc.select_db(sysargs)

    device(db=db, fs=fs, workers=sysargs.workers, interact_timeout=sysargs.interact_timeout,
           keys=keys, resource_limits=resource_limits)
