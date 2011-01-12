import sys, time, traceback, StringIO

def run(db):
    """Run the compute device, querying the database and doing
    relevant work."""
    print "Starting device loop..."
    while True:
        # Evaluate all cells that don't have an output key.
        for X in db.get_unevaluated_cells():
            code = X['input']
            print "evaluating '%s'"%code
            try:
                output = execute_code(code)
            except:
                S = StringIO.StringIO()
                traceback.print_exc(file=S)
                S.seek(0)
                output = S.read()
            # Store the resulting output
            db.set_output(X['_id'], output)
        time.sleep(.1)


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
    string = string.splitlines()
    i = len(string)-1
    if i >= 0:
        while len(string[i]) > 0 and string[i][0] in ' \t':
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
    print code
    s0 = sys.stdout
    sys.stdout = StringIO.StringIO()
    exec code in namespace
    sys.stdout.seek(0)
    ans = str(sys.stdout.read())
    sys.stdout = s0
    return ans

if __name__ == "__main__":
    import misc
    db = misc.select_db(sys.argv)
    run(db)
