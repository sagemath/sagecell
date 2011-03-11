import sys, time, traceback, StringIO, contextlib, random

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


from multiprocessing import Pool, TimeoutError

def run(db, fs, workers=1, poll_interval=0.1):
    """Run the compute device, querying the database and doing
    relevant work."""
    device_id=random.randrange(sys.maxint)
    print "Starting device loop for device %s..."%device_id
    pool=Pool(processes=workers)
    results={}

    while True:
        # Queue up all unevaluated cells we requested
        for X in db.get_unevaluated_cells(device_id):
            code = X['input']
            print "evaluating '%s'"%code
            results[X['_id']]=pool.apply_async(execute_code, (X['_id'], code,))
        # Get whatever results are done
        finished=[]
        for _id, result in results.iteritems():
            try:
                # see if the result is ready right now
                output=result.get(timeout=0)
            except TimeoutError:
                # not done yet, go to the next result
                continue
            except:
                # some exception was raised in execution
                output=traceback.format_exc()
            # Store the resulting output
            db.set_output(_id, make_output_json(output))
            finished.append(_id)

        # delete the output that I'm finished with
        for _id in finished:
            del results[_id]

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

def make_output_json(s):
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

namespace = {}
namespace['new_stream']=new_stream
import tempfile
import shutil
import os

def execute_code(cell_id, code):
    """Evaluate the given code, returning what is sent to stdout."""
    # the fs variable is inherited from the parent process
    code = displayhook_hack(code)
    curr_dir=os.getcwd()
    tmp_dir=tempfile.mkdtemp()
    print "Temp files in "+tmp_dir
    try:
        os.chdir(tmp_dir)
        # We really should exec in a new process so that the execed code can't
        # modify things in our current process.  See the multiprocessing module
        with stdoutIO() as s:
            exec code in namespace
        output=s.getvalue()
        os.chdir(tmp_dir)
        file_list=[]
        for filename in os.listdir(tmp_dir):
            file_list.append(filename)
            fs_file=fs.new_file(cell_id, filename)
            with open(filename) as f:
                fs_file.write(f.read())
            fs_file.close()
        if len(file_list)>0:
            output+=new_stream('files',printout=False,files=file_list)
    finally:
        os.chdir(curr_dir)
        shutil.rmtree(tmp_dir)
    return output

if __name__ == "__main__":
    # argv[1] is number of workers
    # argv[2] is "mongo" (default) or "sqlite"
    import misc
    db, fs = misc.select_db([""] if len(sys.argv)<3 else ["", sys.argv[2]])
    if len(sys.argv)<=1:
        workers=1
    else:
        workers=int(sys.argv[1])
    run(db, fs, workers=workers)
