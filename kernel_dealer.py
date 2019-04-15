import time

import jupyter_client.session
import zmq

from log import logger
import misc


config = misc.Config()


class KernelConnection(object):
    """
    Kernel from the dealer point of view.
    
    Handles connections over ZMQ sockets to compute kernels.
    """
    
    def __init__(self, dealer, id, connection, lifespan, timeout):
        self._on_stop = None
        self._dealer = dealer
        self.id = id
        self.executing = 0
        self.status = "starting"
        now = time.time()
        self.hard_deadline = now + lifespan
        self.timeout = timeout
        if timeout > 0:
            self.deadline = now + self.timeout
        self.session = jupyter_client.session.Session(key=connection["key"])
        self.channels = {}
        context = zmq.Context.instance()
        address = connection["ip"]
        if ":" in address:
            address = "[{}]".format(address)
        for channel, socket_type in (
                ("shell", zmq.DEALER), ("iopub", zmq.SUB), ("hb", zmq.REQ)):
            socket = context.socket(socket_type)
            socket.connect("tcp://{}:{}".format(address, connection[channel]))
            stream = zmq.eventloop.zmqstream.ZMQStream(socket)
            stream.channel = channel
            self.channels[channel] = stream
        self.channels["iopub"].socket.subscribe(b"")
        self.start_hb()
        logger.debug("KernelConnection initialized")
        
    def on_stop(self, callback):
        self._on_stop = callback
        
    def start_hb(self):
        logger.debug("start_hb for %s", self.id)
        hb = self.channels["hb"]
        ioloop = zmq.eventloop.IOLoop.current()

        def pong(message):
            #logger.debug("pong for %s", self.id)
            self._expecting_pong = False

        hb.on_recv(pong)
        self._expecting_pong = False

        def ping():
            #logger.debug("ping for %s", self.id)
            now = ioloop.time()
            if self._expecting_pong:
                logger.warning("kernel %s died unexpectedly", self.id)
                self.stop()
            elif now > self.hard_deadline:
                logger.info("hard deadline reached for %s", self.id)
                self.stop()
            elif (self.timeout > 0
                    and now > self.deadline
                    and self.status == "idle"):
                logger.info("kernel %s timed out", self.id)
                self.stop()
            else:
                hb.send(b'ping')
                self._expecting_pong = True

        self._hb_periodic_callback = zmq.eventloop.ioloop.PeriodicCallback(
            ping, config.get("beat_interval") * 1000)

        def start_ping():
            logger.debug("start_ping for %s", self.id)
            if self.alive:
                self._hb_periodic_callback.start()

        self._start_ping_handle = ioloop.call_later(
            config.get("first_beat"), start_ping)
        self.alive = True

    def stop(self):
        logger.debug("stopping kernel %s", self.id)
        if not self.alive:
            logger.warning("not alive already")
            return
        self.stop_hb()
        if self._on_stop:
            self._on_stop()
        for stream in self.channels.itervalues():
            stream.close()
        self._dealer.stop_kernel(self.id)
        
    def stop_hb(self):
        logger.debug("stop_hb for %s", self.id)
        self.alive = False
        self._hb_periodic_callback.stop()
        zmq.eventloop.IOLoop.current().remove_timeout(self._start_ping_handle)
        self.channels["hb"].on_recv(None)


class KernelDealer(object):
    r"""
    Kernel Dealer handles compute kernels on the server side.
    """
    
    def __init__(self, provider_settings):
        self.provider_settings = provider_settings
        self._available_providers = []
        self._connected_providers = {}  # provider address: last message time
        self._expected_kernels = []
        self._get_queue = []
        self._kernel_origins = {}   # id: provider address
        self._kernels = {}  # id: KernelConnection
        context = zmq.Context.instance()
        context.IPV6 = 1
        socket = context.socket(zmq.ROUTER)
        self.port = socket.bind_to_random_port("tcp://*")
        # Can configure perhaps interface/IP/port
        self._stream = zmq.eventloop.zmqstream.ZMQStream(socket)
        self._stream.on_recv(self._recv)
        logger.debug("KernelDealer initialized")
        
    def _try_to_get(self):
        r"""
        Send a get request if possible AND needed.
        """
        while self._available_providers and self._get_queue:
            self._stream.send(self._available_providers.pop(0), zmq.SNDMORE)
            self._stream.send_json(["get", self._get_queue.pop(0)])
            logger.debug("sent get request to a provider")
        if self._available_providers:
            logger.debug("%s available providers are idling",
                len(self._available_providers))
        if self._get_queue:
            logger.debug("%s get requests are waiting for providers",
                len(self._get_queue))
        
    def _recv(self, msg):
        logger.debug("received %s", msg)
        assert len(msg) == 2
        addr = msg[0]
        self._connected_providers[addr] = time.time()
        msg = zmq.utils.jsonapi.loads(msg[1])
        if msg == "get settings":
            self._stream.send(addr, zmq.SNDMORE)
            self._stream.send_json(["settings", self.provider_settings])
        elif msg == "ready":
            self._available_providers.append(addr)
            self._try_to_get()
        elif msg[0] == "kernel":
            msg = msg[1]
            for i, (rlimits, callback) in enumerate(self._expected_kernels):
                if rlimits == msg["rlimits"]:
                    self._kernel_origins[msg["id"]] = addr
                    self._expected_kernels.pop(i)
                    callback(msg)
                    break
            
    def get_kernel(self, callback,
                   rlimits={}, lifespan=float("inf"), timeout=float("inf")):

        def cb(d):
            d.pop("rlimits")
            d["lifespan"] = lifespan
            d["timeout"] = timeout
            kernel = KernelConnection(self, **d)
            self._kernels[kernel.id] = kernel
            logger.debug("tracking %d kernels", len(self._kernels))
            logger.info("dealing kernel %s", kernel.id)
            callback(kernel)
            
        self._expected_kernels.append((rlimits, cb))
        self._get_queue.append(rlimits)
        self._try_to_get()
        
    def kernel(self, id):
        return self._kernels[id]
        
    def stop(self):
        r"""
        Stop all kernels and disconnect all providers.
        """
        self._stream.stop_on_recv()
        for k in self._kernels.values():
            k.stop()
        for addr in self._connected_providers:
            logger.debug("stopping %r", addr)
            self._stream.send(addr, zmq.SNDMORE)
            self._stream.send_json("disconnect")
        self._stream.flush()

    def stop_kernel(self, id):
        addr = self._kernel_origins.pop(id)
        self._stream.send(addr, zmq.SNDMORE)
        self._stream.send_json(["stop", id])
        self._kernels.pop(id)
