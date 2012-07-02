import time, string, urllib, zlib, base64

import tornado.web
import tornado.websocket

from zmq.eventloop import ioloop
from zmq.utils import jsonapi

from IPython.zmq.session import Session

class RootHandler(tornado.web.RequestHandler):
    """
    Root URL request handler.
    
    This renders templates/root.html, which optionally inserts
    specified preloaded code during the rendering process.
    
    There are three ways currently supported to specify
    preloading code:
    
    ``<root_url>?c=<code>`` loads 'plaintext' code
    ``<root_url>?z=<base64>`` loads base64-compressed code
    ```<root_url>?q=<uuid>`` loads code from a database based
    upon a unique identifying permalink (uuid4-based)
    """
    def _root_url(self):
        valid_query_chars = set(string.letters+string.digits+"-")
        db = self.application.db
        options = {}

        args = self.request.arguments

        if "c" in args:
            # If the code is explicitly specified
            options["code"] = "".join(args["c"])

        elif "z" in args:
            # If the code is base64-compressed
            try:
                z = "".join(args["z"])
                # We allow the user to strip off the ``=`` padding at the end
                # so that the URL doesn't have to have any escaping.
                # Here we add back the ``=`` padding if we need it.
                z += "=" * ((4 - (len(z) % 4)) % 4)
                print z
                options["code"] = zlib.decompress(base64.urlsafe_b64decode(z))
            except Exception as e:
                options["code"] = "# Error decompressing code %s"%e

        elif "q" in args:
            # if the code is referenced by a permalink identifier
            q = "".join(args["q"])
            if set(q).issubset(valid_query_chars):
                options["code"] = db.get_exec_msg(q)

        if "code" in options:
            if isinstance(options["code"], unicode):
                options["code"] = options["code"].encode("utf8")
            options["code"] = urllib.quote(options["code"])
            options["autoeval"] = False if "autoeval" in self.request.arguments and self.get_argument("autoeval") == "false" else True
        else:
            options["code"] = None

        self.render("root.html", **options)

    def get(self):
        return self._root_url()

class KernelHandler(tornado.web.RequestHandler):
    """
    Kernel startup request handler.
    
    This starts up an iPython kernel on an untrusted account
    and returns the associated kernel id and a url to request
    websocket connections for a websocket-ZMQ bridge back to
    the kernel in a JSON-compatible message.
    
    The returned websocket url is not entirely complete, in
    that it is the base url to be used for two different
    websocket connections (corresponding to the shell and
    iopub streams) of the iPython kernel. It is the
    responsiblity of the client to request the correct URLs
    for these websockets based on the following pattern:
    
    ``<ws_url>/iopub`` is the expected iopub stream url
    ``<ws_url>/shell`` is the expected shell stream url
    """
    def _start_kernel(self):
        print "%s BEGIN MAIN KERNEL HANDLER %s"%("*"*10, "*"*10)

        proto = self.request.protocol.replace("http", "ws")
        host = self.request.host

        ws_url = "%s://%s/" % (proto, host)

        km = self.application.km
        
        kernel_id = km.new_session()
        
        print "kernel started with id ::: %s"%kernel_id
        
        data = {"ws_url": ws_url, "kernel_id": kernel_id}

        print "%s END MAIN KERNEL HANDLER %s"%("*"*10, "*"*10)

        self.write(data)
        self.finish()

    def post(self):
        return self._start_kernel()

class PermalinkHandler(tornado.web.RequestHandler):
    """
    Permalink generation request handler.

    This accepts the string version of an iPython
    execute_request message, and stores the code associated
    with that request in a database linked to a unique id,
    which is returned to the requester in a JSON-compatible
    form.

    The specified id can be used to generate permalinks
    with the format ``<root_url>?q=<id>``.
    """

    def _get_permalink(self):
        """
        """

        args = self.request.arguments

        rval = {"permalink": None}
        if "message" in args:
            db = self.application.db
            try:
                message = jsonapi.loads("".join(args["message"]))
                if message["header"]["msg_type"] == "execute_request":
                    rval["permalink"] = db.new_exec_msg(message)
            except:
                pass
        self.write(rval)
        self.finish()

    def get(self):
        return self._get_permalink()
    def post(self):
        return self._get_permalink()

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
            timeout = msg["content"]["user_variables"].get("__kernel_timeout__")

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
        except:
            pass
        else:
            self.write_message(message)

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
        msg = jsonapi.loads(message)
        if "execute_request" == msg["header"]["msg_type"]:
            msg["content"]["user_variables"] = ['__kernel_timeout__']
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



