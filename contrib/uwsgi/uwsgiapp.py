from flask import Flask
application = Flask(__name__)
from flask import request
from contextlib import contextmanager, nested
from IPython.core.interactiveshell import InteractiveShell, InteractiveShellABC

class Shell(InteractiveShell):
    def __init__(self, config=None, ipython_dir=None, profile_dir=None,
             user_ns=None, user_module=None, custom_exceptions=((),None),
             usage=None, banner1=None, banner2=None, display_banner=None):

        super(Shell, self).__init__(
            config=config, profile_dir=profile_dir, user_ns=user_ns,
            user_module=user_module, custom_exceptions=custom_exceptions
        )

InteractiveShellABC.register(Shell)

from IPython.zmq.kernelmanager import KernelManager
class ForkingKernelManager(KernelManager):
    kernel = Any()
    



@contextmanager
def capture():
    import sys
    from cStringIO import StringIO
    oldout,olderr = sys.stdout, sys.stderr
    try:
        out=[StringIO(), StringIO()]
        sys.stdout,sys.stderr = out
        yield out
    finally:
        sys.stdout,sys.stderr = oldout, olderr
        out[0] = out[0].getvalue()
        out[1] = out[1].getvalue()

@app.route('/')
def hello_world():
    # I replace \r\n with \n...this might cause problems for code that has legitimate \r characters in it
    # (like in a string)
    code = request.values.get('c','').replace('\r\n','\n')
    if len(code)>0:
        s="Code<br/><pre>%r</pre><hr/>"%code
        try:
            a=InteractiveShell()
            with capture() as out:
                a.run_cell(code)
#            c=compile(code,'<string>','exec')
#            with capture() as out:
#                exec c
            s+="Standard out<br/><pre>%s</pre><hr/>Standard Error<br/><pre>%s</pre>"%tuple(out)
        except Exception as e:
            s+="Error: %s"%e
        return s
    return "<form><textarea name='c' cols='100' rows='20'></textarea><br/><input type='submit'></form>"

if __name__ == '__main__':
    application.run()
