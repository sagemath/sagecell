from untrusted_kernel_manager import UntrustedMultiKernelManager
import zmq
from zmq import ssh
import sys

class Receiver:
    def __init__(self, filename):
        self.context = zmq.Context()
        self.km = UntrustedMultiKernelManager(filename)
        self.dealer = self.context.socket(zmq.DEALER)
        self.port = self.dealer.bind_to_random_port("tcp://127.0.0.1")
        self.filename = filename
        sys.stdout.write(str(self.port))
        sys.stdout.flush()

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
    filename = sys.argv[1]
    import logging
    import uuid
    logging.basicConfig(filename=filename,format=str(uuid.uuid4()).split('-')[0]+': %(asctime)s %(message)s',level=logging.DEBUG)
    logging.debug('started')
    receiver = Receiver(filename)
    receiver.start()
    logging.debug('ended')
