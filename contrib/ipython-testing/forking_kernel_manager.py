import uuid
import zmq
import os
import signal
import tempfile
import json
import random
import sys
import resource
import interact_sagecell
import interact_compatibility
from IPython.zmq.ipkernel import IPKernelApp
from IPython.config.loader import Config
from multiprocessing import Process, Pipe
import logging
import sage
import sage.all
from sage.misc.interpreter import SageInputSplitter
from IPython.core.inputsplitter import IPythonInputSplitter


class SageIPythonInputSplitter(SageInputSplitter, IPythonInputSplitter):
    """
    This class merely exists so that the IPKernelApp.kernel.shell class does not complain.  It requires
    a subclass of IPythonInputSplitter, but SageInputSplitter is a subclass of InputSplitter instead.
    """
    pass

class ForkingKernelManager(object):
    def __init__(self, filename):
        self.kernels = {}
        self.filename = filename

    def fork_kernel(self, sage_dict, config, pipe, resource_limits, logfile):
        os.setpgrp()
        logging.basicConfig(filename=self.filename,format=str(uuid.uuid4()).split('-')[0]+': %(asctime)s %(message)s',level=logging.DEBUG)
        ka = IPKernelApp.instance(config=config)
        ka.initialize([])
        # this should really be handled in the config, not set separately.
        ka.kernel.shell.input_splitter = SageIPythonInputSplitter()
        user_ns = ka.kernel.shell.user_ns
        user_ns.update(sage_dict)
        user_ns.update(interact_sagecell.imports)
        user_ns.update(interact_compatibility.imports)
        sage_code = """
sage.misc.session.init()

# Ensure unique random state after forking
set_random_seed()
"""
        exec sage_code in user_ns
        if "sys" in user_ns:
            user_ns["sys"]._update_interact = interact_sagecell.update_interact
        else:
            sys._update_interact = interact_sagecell.update_interact
            user_ns["sys"] = sys
        try:
            user_ns["sage"].misc.html.HTML.eval = \
                eval_func(ka.session, ka.iopub_socket, user_ns["sage"].misc.html)
            user_ns["sage"].misc.html.HTML.table = table_func(ka.session, ka.iopub_socket)
        except:
            pass
        user_ns["interact"] = interact_sagecell.interact_func(ka.session, ka.iopub_socket)
        for r, limit in resource_limits.iteritems():
            resource.setrlimit(getattr(resource, r), (limit, limit))
        pipe.send({"ip": ka.ip, "key": ka.session.key, "shell_port": ka.shell_port,
                "stdin_port": ka.stdin_port, "hb_port": ka.hb_port, "iopub_port": ka.iopub_port})
        pipe.close()
        ka.start()

    def start_kernel(self, sage_dict=None, kernel_id=None, config=None, resource_limits=None, logfile = None):
        if sage_dict is None:
            sage_dict = {}
        if kernel_id is None:
            kernel_id = str(uuid.uuid4())
        if config is None:
            config = Config()
        if resource_limits is None:
            resource_limits = {}
        p, q = Pipe()
        proc = Process(target=self.fork_kernel, args=(sage_dict, config, q, resource_limits, logfile))
        proc.start()
        connection = p.recv()
        p.close()
        self.kernels[kernel_id] = (proc, connection)
        return {"kernel_id": kernel_id, "connection": connection}

    def kill_kernel(self, kernel_id):
        """Kill a running kernel."""
        success = False

        if kernel_id in self.kernels:
            proc = self.kernels[kernel_id][0]
            try:
                success = True
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.join()
            except Exception as e:
                # On Unix, we may get an ESRCH error if the process has already
                # terminated. Ignore it.
                from errno import ESRCH
                if e.errno !=  ESRCH:
                    success = False
        if success:
            del self.kernels[kernel_id]
        return success

    def interrupt_kernel(self, kernel_id):
        """Interrupt a running kernel."""
        success = False

        if kernel_id in self.kernels:
            try:
                os.kill(self.kernels[kernel_id][0].pid, signal.SIGINT)
                success = True
            except:
                pass

        return success

    def restart_kernel(self, sage_dict, kernel_id):
        ports = self.kernels[kernel_id][1]
        self.kill_kernel(kernel_id)
        return self.start_kernel(sage_dict, kernel_id, Config({"IPKernelApp": ports}))

def html_msg(html, session):
    """
    Create an IPython message that will cause the Sage Cell to output a block
    of HTML.

    :arg str html: a string containing the HTML code to print
    :arg IPython.zmq.session.Session session: an IPython session
    :returns: the message
    :rtype: dict
    """

    msg_id = str(uuid.uuid4())
    msg = {"header": {"msg_id": msg_id,
                      "username": session.username,
                      "session": session.session,
                      "msg_type": "extension"},
           "msg_id": msg_id,
           "msg_type": "extension",
           "parent_header": getattr(sys.stdout, "parent_header", {}),
           "content": {"msg_type": "display_data",
                       "content": {"type": "text/html",
                                   "data": '<span style="color:black">%s</span>' % html}}}
    if hasattr(sys.stdout, "interact_id"):
        msg["content"]["interact_id"] = sys.stdout.interact_id
    return msg

def eval_func(session, pub_socket, html):
    """
    Create a function to be used as ``HTML.eval`` in the user namespace,
    with the correct session and socket objects.

    :arg IPython.zmq.session.Session session: an IPython session
    :arg zmq.Socket pub_socket: the \xd8MQ PUB socket used for the IOPUB stream
    :arg module html: Sage's misc.html module
    :returns: the ``eval`` function
    :rtype: function
    """

    # Function modified from sage.misc.html
    def eval(self, s, globals=None, locals=None):
        if globals is None:
            globals = {}
        if locals is None:
            locals = {}
        s = str(s)
        s = html.math_parse(s)
        t = ''
        while len(s) > 0:
            i = s.find('<sage>')
            if i == -1:
                 t += s
                 break
            j = s.find('</sage>')
            if j == -1:
                 t += s
                 break
            t += s[:i] + '<script type="math/tex">%s</script>'%\
                     html.latex(html.sage_eval(s[6+i:j], locals=locals))
            s = s[j+7:]

        session.send(pub_socket, html_msg(t, session))
        return ''
    return eval

def table_func(session, pub_socket):
    """
    Create a function to be used as ``HTML.table`` in the user namespace,
    with the correct session and socket objects.

    :arg IPython.zmq.session.Session session: an IPython session
    :arg zmq.Socket pub_socket: the \xd8MQ PUB socket used for the IOPUB stream
    :returns: the ``table`` function
    :rtype: function
    """
    def table(self, x, header=False):
        r"""
        Print a nested list as a HTML table.  Strings of html
        will be parsed for math inside dollar and double-dollar signs.
        2D graphics will be displayed in the cells.  Expressions will
        be latexed.
        """
        session.send(pub_socket, html_msg(self.table_str(x, header=header), session))
    return table

if __name__ == "__main__":
    a = ForkingKernelManager()
    x=a.start_kernel()
    y=a.start_kernel()
    import time
    time.sleep(5)
    a.kill_kernel(x["kernel_id"])
    a.kill_kernel(y["kernel_id"])
