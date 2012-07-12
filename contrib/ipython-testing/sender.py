import uuid
import threading
import zmq

class AsyncSender(object):
    """
    Manages asynchronous communication between a trusted
    manager with multiple threaded requests and multiple
    untrusted devices.
    """
    def __init__(self):
        self._dealers = {}

        context = zmq.Context()
        self.router = context.socket(zmq.ROUTER)
        self.router.bind("ipc://routing.ipc")

        self.poll = zmq.Poller()
        self.poll.register(self.router, zmq.POLLIN)

        self.poller = threading.Thread(target = self._run)
        self.poller.daemon = True
        self.poller.start()

    def _run(self):
        """
        Background polling mechanism to send / receive
        messages to and from the ROUTER socket and various
        untrusted DEALER sockets.

        When the ROUTER receives a message, it sends that to
        the designated DEALER or sends the received message
        back to the original sender if the designated DEALER
        is not registered.

        When a registered DEALER receives a message, it is
        sent using the ROUTER to the correct recipient
        (the original sender).

        This method should *always* be run in a separate
        thread, and no other threads should try to use or
        monitor the bound ROUTER socket or any connected
        registered DEALER sockets since ZMQ sockets are not
        thread-safe.
        """
        while True:
            sockets = dict(self.poll.poll())

            # If the ROUTER socket has received anything
            if sockets.get(self.router) == zmq.POLLIN:
                (source, sink, msg) = self.router.recv_multipart()
                if sink in self._dealers:
                    sock = self._dealers[sink]
                    sock.send_multipart([source, msg])
                else:
                    self.router.send_multipart([source, source, msg])

            # If any DEALER socket has received anything
            for dealer_id in self._dealers.keys():
                sock = self._dealers[dealer_id]
                if sockets.get(sock) == zmq.POLLIN:
                    (dest, msg) = sock.recv_multipart()
                    self.router.send_multipart([dest, dealer_id, msg])

    def register_computer(self, host, port, comp_id = None):
        """
        This registers an untrusted computer and sets up a
        DEALER socket to the specified host:port over TCP.

        :arg str host: The host of the untrusted machine
        :arg Int port: Port on the untrusted machine that
            has a DEALER socket bound for communication
        :arg str comp_id: A unique ID for the registered
            DEALER socket. This is set to a uuid if it is
            not specified
        :returns: the unique ID ``comp_id``
        :rtype: str
        """
        if comp_id is None:
            comp_id = str(uuid.uuid4())

        context = zmq.Context()
        sock = context.socket(zmq.DEALER)
        sock.connect("tcp://%s:%s"%(host,port))

        self._dealers[comp_id] = sock

        self.poll.register(sock, zmq.POLLIN)

        return comp_id

    def send_msg(self, msg, comp_id):
        """
        Sends a message to a given untrusted computer and
        returns the reply.

        A short-lived in-process ZMQ socket is created to
        the Sender's ROUTER socket and multipart messages
        are used to asynchronously send the message to the
        correct untrusted DEALER socket and return the
        correct reply message.

        :arg dict msg: message to send
        :arg str comp_id: identifier returned by
            register_computer corresponding to a unique
        :returns: reply message from the untrusted side, or
            an None if an invalid ID was specified
        """

        _id = str(uuid.uuid4())
        context = zmq.Context()
        sock = context.socket(zmq.DEALER)
        sock.setsockopt(zmq.IDENTITY, _id)
        sock.connect("ipc://routing.ipc")
        sock.send(comp_id, zmq.SNDMORE)
        sock.send_pyobj(msg)

        source = sock.recv()
        reply = sock.recv_pyobj()
        retval = None
        if source == comp_id:
            retval = reply

        sock.close()

        return retval
