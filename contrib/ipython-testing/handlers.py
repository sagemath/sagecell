import time

import tornado.web
import tornado.websocket

from zmq.eventloop import ioloop
from zmq.utils import jsonapi

from IPython.zmq.session import Session

class ZMQStreamHandler(tornado.websocket.WebSocketHandler):
    def open(self, kernel_id):
        self.km = self.application.km
        self.kernel_id = kernel_id
        self.session = self.km._sessions[self.kernel_id]

    def _reserialize_reply(self, msg_list):
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

        return jsonapi.dumps(msg)

    def _on_zmq_reply(self, msg_list):
        try:
            message = self._reserialize_reply(msg_list)
        except:
            pass
        else:
            self.write_message(message)

class ShellHandler(ZMQStreamHandler):
    def open(self, kernel_id):
        print "*"*10, " BEGIN SHELL HANDLER ", "*"*10
        super(ShellHandler, self).open(kernel_id)
        self.shell_stream = self.km.create_shell_stream(self.kernel_id)
        self.shell_stream.on_recv(self._on_zmq_reply)
        print "*"*10, " END SHELL HANDLER ", "*"*10

    def on_message(self, message):
        msg = jsonapi.loads(message)
        self.session.send(self.shell_stream, msg)
        self.set_status

    def on_close(self):
        if self.shell_stream is not None and not self.shell_stream.closed():
            self.shell_stream.close()

class IOPubHandler(ZMQStreamHandler):
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
        if not self._beating:
            self._kernel_alive = True

            def ping_or_dead():
                self.hb_stream.flush()
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
        """callback for delayed heartbeat start
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
        self.application.km.end_session(self.kernel_id)
        self.write_message(
            {'header': {'msg_type': 'status'},
             'parent_header': {},
             'content': {'execution_state':'dead'}
            }
        )
        self.on_close()



