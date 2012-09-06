from untrusted_kernel_manager import UntrustedMultiKernelManager
import zmq
from zmq import ssh
import sys
from IPython.core.inputsplitter import IPythonInputSplitter

try:
    from sage.misc.interpreter import SageInputSplitter
    class SageIPythonInputSplitter(SageInputSplitter, IPythonInputSplitter):
        """
        This class merely exists so that the IPKernelApp.kernel.shell class does not complain.  It requires
        a subclass of IPythonInputSplitter, but SageInputSplitter is a subclass of InputSplitter instead.
        """
        pass
except ImportError:
    SageIPythonInputSplitter = None

class Receiver(object):
    def __init__(self, filename, ip):
        self.context = zmq.Context()
        self.dealer = self.context.socket(zmq.DEALER)
        self.port = self.dealer.bind_to_random_port("tcp://%s" % ip)
        print self.port
        sys.stdout.flush()
        self.sage_mode = self.setup_sage()
        print self.sage_mode
        sys.stdout.flush()
        self.km = UntrustedMultiKernelManager(filename, ip,
                update_function=self.update_dict_with_sage)
        self.filename = filename

    def start(self):
        self.listen = True
        while self.listen:
            source = self.dealer.recv()
            msg = self.dealer.recv_pyobj()

            msg_type = "invalid_message"
            if msg.get("type") is not None:
                msgtype = msg["type"]
                if hasattr(self, msgtype):
                    msg_type = msgtype

            if msg.get("content") is None:
                msg["content"] = {}

            handler = getattr(self, msg_type)
            response = handler(msg["content"])

            self.dealer.send(source, zmq.SNDMORE)
            self.dealer.send_pyobj(response)

    def _form_message(self, content, error=False):
        return {"content": content,
                "type": "error" if error else "success"}

    def setup_sage(self):
        try:
            import sage
            import sage.all
            sage.misc.misc.EMBEDDED_MODE = {'frontend': 'sagecell'}
            import StringIO
            # The first plot takes about 2 seconds to generate (presumably
            # because lots of things, like matplotlib, are imported).  We plot
            # something here so that worker processes don't have this overhead
            try:
                sage.all.plot(lambda x: x, (0,1)).save(StringIO.StringIO())
            except Exception as e:
                logging.debug('plotting exception: %s'%e)
            self.sage_dict = {'sage': sage}
            sage_code = """
from sage.all import *
from sage.calculus.predefined import x
from sage.misc.html import html
from sage.server.support import help
from sagenb.misc.support import automatic_names
"""
            exec sage_code in self.sage_dict
            return True
        except ImportError as e:
            self.sage_dict = {}
            return False

    def update_dict_with_sage(self, ka):
        import misc
        class TempClass(object):
            pass
        _sage_ = TempClass()
        _sage_.display_message = misc.display_message
        _sage_.kernel_timeout = 0.0
        _sage_.sent_files = {}
        def new_files(root='./'):
            import os
            import sys
            new_files = []
            for top,dirs,files in os.walk(root):
                for nm in files:
                    path = os.path.join(top,nm)
                    if path.startswith('./'):
                        path = path[2:]
                    mtime = os.stat(path).st_mtime
                    if path not in sys._sage_.sent_files or sys._sage_.sent_files[path] < mtime:
                        new_files.append(path)
                        sys._sage_.sent_files[path] = mtime
            ip = user_ns['get_ipython']()
            ip.payload_manager.write_payload({"new_files": new_files})
            return ''
        _sage_.new_files = new_files
        sys._sage_ = _sage_
        user_ns = ka.kernel.shell.user_ns
        # TODO: maybe we don't want to cut down the flush interval?
        sys.stdout.flush_interval = sys.stderr.flush_interval = 0.0
        if self.sage_mode:
            ka.kernel.shell.input_splitter = SageIPythonInputSplitter()
            user_ns.update(self.sage_dict)
            sage_code = """
sage.misc.session.init()

# Ensure unique random state after forking
set_random_seed()
"""
            exec sage_code in user_ns
        import interact_sagecell
        import interact_compatibility
        # overwrite Sage's interact command with our own
        user_ns["interact"] = interact_sagecell.interact_func(ka.session, ka.iopub_socket)
        user_ns.update(interact_sagecell.imports)
        user_ns.update(interact_compatibility.imports)
        sys._sage_.update_interact = interact_sagecell.update_interact

    """
    Message Handlers
    """
    def invalid_message(self, msg_content):
        """Handler for unsupported messages."""
        return self._form_message({"status": "Invalid message!"}, error = True)

    def start_kernel(self, msg_content):
        """Handler for start_kernel messages."""
        resource_limits = msg_content.get("resource_limits")
        reply_content = self.km.start_kernel(resource_limits=resource_limits)
        return self._form_message(reply_content)

    def kill_kernel(self, msg_content):
        """Handler for kill_kernel messages."""
        kernel_id = msg_content["kernel_id"]
        success = self.km.kill_kernel(kernel_id)

        reply_content = {"status": "Kernel %s killed!"%(kernel_id)}
        if not success:
            reply_content["status"] = "Could not kill kernel %s!"%(kernel_id)

        return self._form_message(reply_content, error=(not success))
    
    def purge_kernels(self, msg_content):
        """Handler for purge_kernels messages."""
        failures = self.km.purge_kernels()
        reply_content = {"status": "All kernels killed!"}
        success = (len(failures) == 0)
        if not success:
            reply_content["status"] = "Could not kill kernels %s!"%(failures)
        return self._form_message(reply_content, error=(not success))

    def restart_kernel(self, content):
        """Handler for restart_kernel messages."""
        kernel_id = content["kernel_id"]
        return self._form_message(self.km.restart_kernel(kernel_id))

    def interrupt_kernel(self, msg_content):
        """Handler for interrupt_kernel messages."""
        kernel_id = msg_content["kernel_id"]

        reply_content = {"status": "Kernel %s interrupted!"%(kernel_id)}
        success = self.km.interrupt_kernel(kernel_id)
        if not success:
            reply_content["status"] = "Could not interrupt kernel %s!"%(kernel_id)
        return self._form_message(reply_content, error=(not success))

    def remove_computer(self, msg_content):
        """Handler for remove_computer messages."""
        self.listen = False
        return self.purge_kernels(msg_content)


if __name__ == '__main__':
    filename = sys.argv[2]
    import logging
    import uuid
    logging.basicConfig(filename=filename,format=str(uuid.uuid4()).split('-')[0]+': %(asctime)s %(message)s',level=logging.DEBUG)
    logging.debug('started')
    ip = sys.argv[1]
    logging.basicConfig(filename=filename,format=str(uuid.uuid4()).split('-')[0]+': %(asctime)s %(message)s',level=logging.DEBUG)
    logging.debug('started')
    receiver = Receiver(filename, ip)
    receiver.start()
    logging.debug('ended')
