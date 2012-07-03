import time

import tornado.web
import tornado.websocket

from zmq.eventloop import ioloop
from zmq.utils import jsonapi

from IPython.zmq.session import Session

class ZMQStreamHandler(tornado.websocket.WebSocketHandler):
    """
    Base class for a websocket-ZMQ bridge using ZMQStream.

    At minimum, subclasses should define their own ``open``,
    ``on_close``, and ``on_message` functions depending on
    what type of ZMQStream is used.
    """
    def open(self, kernel_id):
        self.km = self.application.km
        self.kernel_id = kernel_id
        self.session = self.km._sessions[self.kernel_id]
        self.kernel_timeout = self.km.kernel_timeout

    def _reserialize_reply(self, msg_list):
        """
        Converts a multipart list of received messages into
        one coherent JSON message.
        """
        idents, msg_list = self.session.feed_identities(msg_list)
        msg = self.session.unserialize(msg_list)

        try:
            msg["header"].pop("date")
        except KeyError:
            pass
        try:
            msg["parent_header"].pop("date")
        except KeyError:
            pass
        try:
            msg["header"].pop("started")
        except KeyError:
            pass
        msg.pop("buffers")

        retval = jsonapi.dumps(msg)

        if "execute_reply" == msg["msg_type"]:
            timeout = msg["content"]["user_expressions"].get("timeout")

            try:
                timeout = float(timeout) # in case user manually puts in a string
            # also handles the case where a KeyError is raised if no timeout is specified
            except:
                timeout = 0.0

            if timeout > self.kernel_timeout:
                timeout = self.kernel_timeout
            if timeout <= 0.0: # kill the kernel before the heartbeat is able to
                self.km.end_session(self.kernel_id)
            else:
                self.km._kernels[self.kernel_id]["timeout"] = (time.time()+timeout)
                self.km._kernels[self.kernel_id]["executing"] = False

        return retval

    def _on_zmq_reply(self, msg_list):
        try:
            message = self._reserialize_reply(msg_list)
            self.write_message(message)
        except:
            pass

class ShellHandler(ZMQStreamHandler):
    """
    This handles the websocket-ZMQ bridge for the shell
    stream of an iPython kernel.
    """
    def open(self, kernel_id):
        print "*"*10, " BEGIN SHELL HANDLER ", "*"*10
        super(ShellHandler, self).open(kernel_id)
        self.shell_stream = self.km.create_shell_stream(self.kernel_id)
        self.shell_stream.on_recv(self._on_zmq_reply)
        print "*"*10, " END SHELL HANDLER ", "*"*10

    def on_message(self, message):
        if self.km._kernels.get(self.kernel_id) is not None:
            msg = jsonapi.loads(message)
            if "execute_request" == msg["header"]["msg_type"]:
                msg["content"]["user_expressions"] = {"timeout": "sys._sage_.kernel_timeout"}
                self.km._kernels[self.kernel_id]["executing"] = True
                self.session.send(self.shell_stream, msg)

    def on_close(self):
        if self.shell_stream is not None and not self.shell_stream.closed():
            self.shell_stream.close()

class IOPubHandler(ZMQStreamHandler):
    """
    This handles the websocket-ZMQ bridge for the iopub
    stream of an iPython kernel. It also handles the
    heartbeat (hb) stream that same kernel, but there is no
    associated websocket connection. The iopub websocket is
    instead used to notify the client if the heartbeat
    stream fails.
    """
    def open(self, kernel_id):
        print "*"*10, " BEGIN IOPUB HANDLER ", "*"*10

        super(IOPubHandler, self).open(kernel_id)

        self._kernel_alive = True
        self._beating = False
        self.iopub_stream = None
        self.hb_stream = None

        self.iopub_stream = self.km.create_iopub_stream(self.kernel_id)
        self.iopub_stream.on_recv(self._on_zmq_reply)

        self.hb_stream = self.km.create_hb_stream(self.kernel_id)
        self.start_hb(self.kernel_died)

        print "*"*10, " END IOPUB HANDLER ", "*"*10

    def on_message(self, msg):
        pass

    def on_close(self):
        if self.iopub_stream is not None and not self.iopub_stream.closed():
            self.iopub_stream.on_recv(None)
            self.iopub_stream.close()
        if self.hb_stream is not None and not self.hb_stream.closed():
            self.stop_hb()

    def start_hb(self, callback):
        """
        Starts a series of delayed callbacks to send and
        receive small messages from the heartbeat stream of
        an iPython kernel. The specific delay paramaters for
        the callbacks are set by configuration values in a
        kernel manager associated with the web application.
        """
        if not self._beating:
            self._kernel_alive = True

            def ping_or_dead():
                self.hb_stream.flush()
                try:
                    if not self.km._kernels[self.kernel_id]["executing"]:
                        timeout = self.km._kernels[self.kernel_id]["timeout"]

                        if time.time() > timeout:
                            print "Kernel %s timeout reached." %(self.kernel_id)
                            self._kernel_alive = False
                except:
                    self._kernel_alive = False

                if self._kernel_alive:
                    self._kernel_alive = False
                    self.hb_stream.send(b'ping')
                    # flush stream to force immediate socket send
                    self.hb_stream.flush()
                else:
                    try:
                        callback()
                    except:
                        pass
                    finally:
                        self.stop_hb()

            def beat_received(msg):
                self._kernel_alive = True

            self.hb_stream.on_recv(beat_received)

            loop = ioloop.IOLoop.instance()
 
            (self.beat_interval, self.first_beat) = self.km.get_hb_info(self.kernel_id)

            self._hb_periodic_callback = ioloop.PeriodicCallback(ping_or_dead, self.beat_interval*1000, loop)

            loop.add_timeout(time.time()+self.first_beat, self._really_start_hb)
            self._beating= True

    def _really_start_hb(self):
        """
        callback for delayed heartbeat start
        Only start the hb loop if we haven't been closed during the wait.
        """
        if self._beating and not self.hb_stream.closed():
            self._hb_periodic_callback.start()

    def stop_hb(self):
        """Stop the heartbeating and cancel all related callbacks."""
        if self._beating:
            self._beating = False
            self._hb_periodic_callback.stop()
            if not self.hb_stream.closed():
                self.hb_stream.on_recv(None)
                self.hb_stream.close()

    def kernel_died(self):
        try: # in case kernel has already been killed
            self.application.km.end_session(self.kernel_id)
        except:
            pass
        self.write_message(
            {'header': {'msg_type': 'status'},
             'parent_header': {},
             'content': {'execution_state':'dead'}
            }
        )
        self.on_close()



