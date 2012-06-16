from untrusted_kernel_manager import UntrustedMultiKernelManager
import zmq
import sys

class Receiver:
    def __init__(self, port):
        self.port = port
        self.context = zmq.Context()
        self.km = UntrustedMultiKernelManager()

    def start(self):
        self.rep = self.context.socket(zmq.REP)
        self.rep.bind("tcp://127.0.0.1:%s" % self.port)
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


    """
    Message Handlers
    """
    def invalid_message(self, content):
        """Handler for unsupported messages."""
        return self._form_message({"status": "Invalid message!"}, error = True)

    def start_kernel(self, content):
        """Handler for start_kernel messages."""
        print "start kernel"
        content = self.km.start_kernel()
        print content
        return self._form_message(content)

    def kill_kernel(self, content):
        """Handler for kill_kernel messages."""
        kernel_id = content["kernel_id"]
        success = self.km.kill_kernel(kernel_id)

        content = {"status": "Kernel %s killed!"%(kernel_id)}
        if not success:
            content["status"] = "Could not kill kernel %s!"%(kernel_id)

        return self._form_message(content, error=(not success))
    
    def purge_kernels(self, content):
        """Handler for purge_kernels messages."""
        failures = []
        for kernel_id in self.km._kernels:
            success = self.km.kill_kernel(kernel_id)
            if not success:
                failures.append(kernel_id)

        content = {"status": "All kernels killed!"}
        success = (len(failures) > 0)
        if not success:
            content["status"] = "Could not kill kernels %s!"%(failures)
        return self._form_message(content, error=(not success))

    def restart_kernel(self, content):
        """Handler for restart_kernel messages."""
        kernel_id = content["kernel_id"]
        return self._form_message(self.km.restart_kernel(kernel_id))

    def interrupt_kernel(self, content):
        """Handler for interrupt_kernel messages."""
        kernel_id = content["kernel_id"]

        content = {"status": "Kernel %s interrupted!"%(kernel_id)}
        success = self.km.interrupt_kernel(kernel_id)
        if not success:
            content["status"] = "Could not interrupt kernel %s!"%(kernel_id)
        return self._form_message(content, error=(not success))

    def remove_computer(self, content):
        """Handler for remove_computer messages."""
        listen = False
        return self.purge_kernels(content)


port = sys.argv[1]
receiver = Receiver(port)
receiver.start()
