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


def run(db, poll_interval=0.1):
    """Run the compute device, querying the database and doing
    relevant work."""
    device_id=random.randrange(sys.maxint)
    print "Starting device loop for device %s..."%device_id
    while True:
        # Evaluate all cells that don't have an output key.
        for X in db.get_unevaluated_cells(device_id, limit=1):
            code = X['input']
            print "evaluating '%s'"%code
            try:
                output = execute_code(code)
            except:
                output = traceback.format_exc()
            # Store the resulting output
            db.set_output(X['_id'], output)
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

namespace = {}

def execute_code(code):
    """Evalue the given code, returning what is sent to stdout."""
    code = displayhook_hack(code)
    with stdoutIO() as s:
        exec code in namespace
    return s.getvalue()

if __name__ == "__main__":
    import misc
    
    db = misc.select_db(sys.argv)
    run(db)
