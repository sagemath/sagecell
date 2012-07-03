from untrusted_kernel_manager import UntrustedMultiKernelManager
import zmq
from zmq import ssh
import sys
from sage.misc.interpreter import SageInputSplitter
from IPython.core.inputsplitter import IPythonInputSplitter
import interact


class SageIPythonInputSplitter(SageInputSplitter, IPythonInputSplitter):
    """
    This class merely exists so that the IPKernelApp.kernel.shell class does not complain.  It requires
    a subclass of IPythonInputSplitter, but SageInputSplitter is a subclass of InputSplitter instead.
    """
    pass

class Receiver:
    def __init__(self, filename):
        self.setup_sage()
        self.context = zmq.Context()
        self.km = UntrustedMultiKernelManager(filename, update_function = self.update_dict_with_sage)
        self.rep = self.context.socket(zmq.REP)
        self.port = self.rep.bind_to_random_port("tcp://127.0.0.1")
        self.filename = filename
        sys.stdout.write(str(self.port))
        sys.stdout.flush()

    def start(self):
        handshake = self.rep.recv()
        self.rep.send(handshake)
        
        self.listen = True
        while self.listen:
            msg = self.rep.recv_pyobj()
            msg_type = msg["type"]

            print msg

            if msg.get("content") is None:
                msg["content"] = {}

            if not hasattr(self, msg_type):
                msg_type = "invalid_message"

            handler = getattr(self, msg_type)
            response = handler(msg["content"])

            self.rep.send_pyobj(response)

    def _form_message(self, content, error=False):
        return {"content": content,
                "type": "error" if error else "success"}

    def setup_sage(self):
        try:
            logging.debug('initializing sage')
            import StringIO
            import sage
            import sage.all
            # The first plot takes about 2 seconds to generate (presumably
            # because lots of things, like matplotlib, are imported).  We plot
            # something here so that worker processes don't have this overhead
            logging.debug('plotting')
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

            logging.debug('set up sage')
        except ImportError as e:
            self.sage_dict = {}

    def update_dict_with_sage(self, user_ns, input_splitter, session, iopub_socket):
        input_splitter = SageIPythonInputSplitter()
        user_ns.update(self.sage_dict)
        user_ns.update(interact.classes)
        user_ns.update({"__kernel_timeout__": 0.0})
        sage_code = """
sage.misc.session.init()

# Ensure unique random state after forking
set_random_seed()
"""
        exec sage_code in user_ns
        if "sys" in user_ns:
            user_ns["sys"]._interacts = interact.interacts
        else:
            sys._interacts = interact.interacts
            user_ns["sys"] = sys
        user_ns["interact"] = interact.interact_func(session, iopub_socket)

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
        return self._form_message(repy_content, error=(not success))

    def remove_computer(self, msg_content):
        """Handler for remove_computer messages."""
        self.listen = False
        return self.purge_kernels(msg_content)


if __name__ == '__main__':
    filename = sys.argv[1]
    import logging
    import uuid
    logging.basicConfig(filename=filename,format=str(uuid.uuid4()).split('-')[0]+': %(asctime)s %(message)s',level=logging.DEBUG)
    logging.debug('started')
    receiver = Receiver(filename)
    receiver.start()
    logging.debug('ended')
