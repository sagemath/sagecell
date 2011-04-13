import zmq
from time import sleep

class IPReceiver:
    """Receives messages from IPython's ZeroMQ channels."""
    def __init__(self, socketType, port):
        self.context=zmq.Context()
        self.socket=self.context.socket(socketType)
        self.socket.connect("tcp://localhost:%i"%(port,))
        if socketType==zmq.SUB:
            self.socket.setsockopt(zmq.SUBSCRIBE,"")
        self.messages=[]

    def getMessages(self, parent_header, block=False):
        """Receives all messages from IPython, returning the ones with
        the given parent_header property, and archiving the rest.
        The next time this function is called with the parent_header of an archived message,
        that message will be included in the messages returned.
        
        If block is True, wait until at least one message is found."""
        results=[]
        while True:
            while True:
                try:
                    self.messages.append(self.socket.recv_json(zmq.NOBLOCK))
                except zmq.core.error.ZMQError: # No more messages
                    break
            toDel=set()
            for i in range(len(self.messages)):
                if self.messages[i]['parent_header']==parent_header:
                    results.append(self.messages[i])
                    toDel.add(i)
            self.messages[:]=[self.messages[i] for i in range(len(self.messages)) if i not in toDel]
            if not block or len(results):
                break
        sleep(0.1)
        return results
