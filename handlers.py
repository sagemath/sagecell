import time, string, urllib, zlib, base64, uuid, json, os.path

import tornado.web
import tornado.websocket
import tornado.gen as gen
import sockjs.tornado
from zmq.eventloop import ioloop
from zmq.utils import jsonapi
try:
    from IPython.kernel.zmq.session import Session
except ImportError:
    # old IPython
    from IPython.zmq.session import Session

from misc import json_default, Timer
import logging
logger = logging.getLogger('sagecell')

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
    @tornado.web.asynchronous
    def get(self):
        db = self.application.db
        code = None
        language = None
        args = self.request.arguments

        if "lang" in args:
            language = args["lang"][0]

        if "c" in args:
            # If the code is explicitly specified
            code = "".join(args["c"])

        elif "z" in args:
            # If the code is base64-compressed
            try:
                z = "".join(args["z"])
                # We allow the user to strip off the ``=`` padding at the end
                # so that the URL doesn't have to have any escaping.
                # Here we add back the ``=`` padding if we need it.
                z += "=" * ((4 - (len(z) % 4)) % 4)
                code = zlib.decompress(base64.urlsafe_b64decode(z))
            except Exception as e:
                code = "# Error decompressing code %s"%e

        if "q" in args:
            # if the code is referenced by a permalink identifier
            q = "".join(args["q"])
            db.get_exec_msg(q, self.return_root)
        else:
            self.return_root(code, language)

    def return_root(self, code, language):
        autoeval = None
        if code is not None:
            if isinstance(code, unicode):
                code = code.encode("utf8")
            code = urllib.quote(code)
            autoeval = "false" if "autoeval" in self.request.arguments and self.get_argument("autoeval") == "false" else "true"
        self.render("root.html", code=code, lang=language, autoeval=autoeval)

class KernelHandler(tornado.web.RequestHandler):
    """
    Kernel startup request handler.
    
    This starts up an IPython kernel on an untrusted account
    and returns the associated kernel id and a url to request
    websocket connections for a websocket-ZMQ bridge back to
    the kernel in a JSON-compatible message.
    
    The returned websocket url is not entirely complete, in
    that it is the base url to be used for two different
    websocket connections (corresponding to the shell and
    iopub streams) of the IPython kernel. It is the
    responsiblity of the client to request the correct URLs
    for these websockets based on the following pattern:
    
    ``<ws_url>/iopub`` is the expected iopub stream url
    ``<ws_url>/shell`` is the expected shell stream url
    """
    @tornado.web.asynchronous
    @gen.engine
    def post(self):
        timer = Timer("Kernel handler for %s"%self.get_argument("notebook", uuid.uuid4()))
        proto = self.request.protocol.replace("http", "ws", 1)
        host = self.request.host
        ws_url = "%s://%s/" % (proto, host)
        km = self.application.km
        
        logger.info("Starting session: %s"%timer)
        kernel_id = yield gen.Task(km.new_session_async)
        data = {"ws_url": ws_url, "kernel_id": kernel_id}
        if "frame" not in self.request.arguments:
            self.set_header("Access-Control-Allow-Origin", "*");
        else:
            data = '<script>parent.postMessage(%r,"*");</script>' % (json.dumps(data),)
            self.set_header("Content-Type", "text/html")
        self.write(data)
        self.finish()

class KernelConnection(sockjs.tornado.SockJSConnection):
    def __init__(self, session):
        self.session = session
        super(KernelConnection, self).__init__(session)

    def on_open(self, request):
        self.channels = {}

    def on_message(self, message):
        prefix, message = message.split(",", 1)
        kernel, channel = prefix.split("/")
        if kernel not in self.channels:
            application = self.session.handler.application
            self.channels[kernel] = \
                {"shell": ShellSockJSHandler(kernel, self.send, application),
                 "iopub": IOPubSockJSHandler(kernel, self.send, application)}
            self.channels[kernel]["shell"].open(kernel)
            self.channels[kernel]["iopub"].open(kernel)
        self.channels[kernel][channel].on_message(message)

    def on_close(self):
        for channel in self.channels.itervalues():
            channel["shell"].on_close()
            channel["iopub"].on_close()

KernelRouter = sockjs.tornado.SockJSRouter(KernelConnection, "/sockjs")

class SageCellHandler(tornado.web.RequestHandler):
    """Handler for ``/sagecell.html``"""

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "sagecell.html")) as f:
        sagecell_html = f.read()
        sagecell_json = json.dumps(sagecell_html)

    def get(self):
        if len(self.get_arguments("callback")) == 0:
            self.write(self.sagecell_html);
            self.set_header("Access-Control-Allow-Origin", "*")
            self.set_header("Content-Type", "text/html")
        else:
            self.write("%s(%s);" % (self.get_argument("callback"), self.sagecell_json))
            self.set_header("Content-Type", "application/javascript")

class StaticHandler(tornado.web.StaticFileHandler):
    """Handler for static requests"""
    def set_extra_headers(self, path):
        self.set_header("Access-Control-Allow-Origin", "*")

class ServiceHandler(tornado.web.RequestHandler):
    """
    Implements a blocking (to the client) web service to execute a single
    computation the server.  This should be non-blocking to Tornado.

    The code to be executed is given in the code request parameter.

    This handler is currently not production-ready.
    """
    @tornado.web.asynchronous
    @gen.engine
    def post(self):
        default_timeout = 30 # seconds
        code = "".join(self.get_arguments('code', strip=False))
        if code:
            km = self.application.km
            self.kernel_id = yield gen.Task(km.new_session_async)

            self.shell_handler = ShellServiceHandler(self.application)
            self.iopub_handler = IOPubServiceHandler(self.application)
            
            self.shell_handler.open(self.kernel_id)
            self.iopub_handler.open(self.kernel_id)

            loop = ioloop.IOLoop.instance()

            self.success = False
            def done(msg):
                if msg["msg_type"] == "execute_reply":
                    self.success = msg["content"]["status"] == "ok"
                    loop.remove_timeout(self.timeout_request)
                    loop.add_callback(self.finish_request)
            self.shell_handler.msg_from_kernel_callbacks.append(done)
            self.timeout_request = loop.add_timeout(time.time()+default_timeout, self.finish_request)
            exec_message = {"parent_header": {},
                            "header": {"msg_id": str(uuid.uuid4()),
                                       "username": "",
                                       "session": self.kernel_id,
                                       "msg_type": "execute_request",
                                       },
                            "content": {"code": code,
                                        "silent": False,
                                        "user_variables": [],
                                        "user_expressions": {},
                                        "allow_stdin": False,
                                        },
                            "metadata": {}
                            }
            self.shell_handler.on_message(jsonapi.dumps(exec_message))

    def finish_request(self):
        try: # in case kernel has already been killed
            self.application.km.end_session(self.kernel_id)
        except:
            pass

        retval = self.iopub_handler.streams
        self.shell_handler.on_close()
        self.iopub_handler.on_close()
        retval.update(success=self.success)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.write(retval)
        self.finish()

class ZMQStreamHandler(object):
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
        self.msg_from_kernel_callbacks = []
        self.msg_to_kernel_callbacks = []

    def _unserialize_reply(self, msg_list):
        """
        Converts a multipart list of received messages into
        one coherent JSON message.
        """
        idents, msg_list = self.session.feed_identities(msg_list)
        return self.session.unserialize(msg_list)

    def _json_msg(self, msg):
        """
        Converts a single message into a JSON string
        """
        # can't encode buffers, so let's get rid of them if they exist
        msg.pop("buffers", None)
        # json_default handles things like encoding dates
        return jsonapi.dumps(msg, default=json_default)

    def _on_zmq_reply(self, msg_list):
        try:
            msg = self._unserialize_reply(msg_list)
            for f in self.msg_from_kernel_callbacks:
                f(msg)
            self._output_message(msg)
        except:
            pass
    
    def _output_message(self, message):
        raise NotImplementedError

    def on_close(self):
        self.km.end_session(self.kernel_id)

class ShellHandler(ZMQStreamHandler):
    """
    This handles the websocket-ZMQ bridge for the shell
    stream of an IPython kernel.
    """
    def open(self, kernel_id):
        super(ShellHandler, self).open(kernel_id)
        self.kill_kernel = False
        self.shell_stream = self.km.create_shell_stream(self.kernel_id)
        self.shell_stream.on_recv(self._on_zmq_reply)
        self.msg_to_kernel_callbacks.append(self._request_timeout)
        self.msg_from_kernel_callbacks.append(self._reset_timeout)

    def _request_timeout(self, msg):
        if msg["header"]["msg_type"] in ("execute_request", "sagenb.interact.update_interact"):
            msg["content"].setdefault("user_expressions",{})
            msg["content"]["user_expressions"]["_sagecell_timeout"] = \
                "float('inf')" if msg["content"].get("linked", False) else "sys._sage_.kernel_timeout"

    def _reset_timeout(self, msg):
        if msg["header"]["msg_type"] in ("execute_reply",
                                         "sagenb.interact.update_interact_reply"):
            try:
                timeout = float(msg["content"]["user_expressions"].pop("_sagecell_timeout", 0.0))
            except:
                timeout = 0.0

            if timeout > self.kernel_timeout:
                timeout = self.kernel_timeout
            if timeout <= 0.0 and self.km._kernels[self.kernel_id]["executing"] == 1:
                # kill the kernel before the heartbeat is able to
                self.kill_kernel = True
            else:
                self.km._kernels[self.kernel_id]["timeout"] = (time.time()+timeout)
                self.km._kernels[self.kernel_id]["executing"] -= 1
        
    def on_message(self, message):
        if self.km._kernels.get(self.kernel_id) is not None:
            msg = jsonapi.loads(message)
            for f in self.msg_to_kernel_callbacks:
                f(msg)
            self.km._kernels[self.kernel_id]["executing"] += 1
            self.session.send(self.shell_stream, msg)

    def on_close(self):
        if self.shell_stream is not None and not self.shell_stream.closed():
            self.shell_stream.close()
        super(ShellHandler, self).on_close()

    def _on_zmq_reply(self, msg_list):
        """
        After receiving a kernel's final execute_reply, immediately kill the kernel
        and send that status to the client (rather than waiting for the message to
        be sent after the heartbeat fails. This prevents the user from attempting to
        execute code in a kernel between the time that the kernel is killed
        and the time that the browser receives the "kernel killed" message.
        """
        super(ShellHandler, self)._on_zmq_reply(msg_list)
        if self.kill_kernel:
            self.shell_stream.flush()
            self.km._kernels[self.kernel_id]["kill"]()

class IOPubHandler(ZMQStreamHandler):
    """
    This handles the websocket-ZMQ bridge for the iopub
    stream of an IPython kernel. It also handles the
    heartbeat (hb) stream that same kernel, but there is no
    associated websocket connection. The iopub websocket is
    instead used to notify the client if the heartbeat
    stream fails.
    """
    def open(self, kernel_id):
        super(IOPubHandler, self).open(kernel_id)

        self._kernel_alive = True
        self._beating = False
        self.iopub_stream = None
        self.hb_stream = None

        self.iopub_stream = self.km.create_iopub_stream(self.kernel_id)
        self.iopub_stream.on_recv(self._on_zmq_reply)
        self.km._kernels[kernel_id]["kill"] = self.kernel_died

        self.hb_stream = self.km.create_hb_stream(self.kernel_id)
        self.start_hb(self.kernel_died)

    def on_message(self, msg):
        pass

    def on_close(self):
        if self.iopub_stream is not None and not self.iopub_stream.closed():
            self.iopub_stream.on_recv(None)
            self.iopub_stream.close()
        if self.hb_stream is not None and not self.hb_stream.closed():
            self.stop_hb()
        super(IOPubHandler, self).on_close()

    def start_hb(self, callback):
        """
        Starts a series of delayed callbacks to send and
        receive small messages from the heartbeat stream of
        an IPython kernel. The specific delay paramaters for
        the callbacks are set by configuration values in a
        kernel manager associated with the web application.
        """
        if not self._beating:
            self._kernel_alive = True

            def ping_or_dead():
                self.hb_stream.flush()
                try:
                    if self.km._kernels[self.kernel_id]["executing"] == 0:
                        # only kill the kernel after all pending
                        # execute requests have finished
                        timeout = self.km._kernels[self.kernel_id]["timeout"]

                        if time.time() > timeout:
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
            self.iopub_stream.flush()
            self.application.km.end_session(self.kernel_id)
        except:
            pass
        msg = {'header': {'msg_type': 'status'},
               'parent_header': {},
               'metadata': {},
               'content': {'execution_state':'dead'}}
        self._output_message(msg)
        self.on_close()

class ShellServiceHandler(ShellHandler):
    def __init__(self, application):
        self.application = application

    def _output_message(self, message):
        pass

class IOPubServiceHandler(IOPubHandler):
    def __init__(self, application):
        self.application = application

    def open(self, kernel_id):
        super(IOPubServiceHandler, self).open(kernel_id)
        from collections import defaultdict
        self.streams = defaultdict(unicode)

    def _output_message(self, msg):
        if msg["header"]["msg_type"] == "stream":
            self.streams[msg["content"]["name"]] += msg["content"]["data"]

class ShellWebHandler(ShellHandler, tornado.websocket.WebSocketHandler):
    def _output_message(self, message):
        self.write_message(self._json_msg(message))
    def allow_draft76(self):
        """Allow draft 76, until browsers such as Safari update to RFC 6455.
        
        This has been disabled by default in tornado in release 2.2.0, and
        support will be removed in later versions.
        """
        return True

class IOPubWebHandler(IOPubHandler, tornado.websocket.WebSocketHandler):
    def _output_message(self, message):
        self.write_message(self._json_msg(message))
    def allow_draft76(self):
        """Allow draft 76, until browsers such as Safari update to RFC 6455.
        
        This has been disabled by default in tornado in release 2.2.0, and
        support will be removed in later versions.
        """
        return True

class ShellSockJSHandler(ShellHandler):
    def __init__(self, kernel_id, callback, application):
        self.kernel_id = kernel_id
        self.callback = callback
        self.application = application

    def _output_message(self, message):
        self.callback("%s/shell,%s" % (self.kernel_id, self._json_msg(message)))

class IOPubSockJSHandler(IOPubHandler):
    def __init__(self, kernel_id, callback, application):
        self.kernel_id = kernel_id
        self.callback = callback
        self.application = application

    def _output_message(self, message):
        self.callback("%s/iopub,%s" % (self.kernel_id, self._json_msg(message)))

class FileHandler(tornado.web.StaticFileHandler):
    """
    Files handler
    
    This takes in a filename and returns the file
    """
    def get(self, kernel_id, file_path):
        super(FileHandler, self).get('%s/%s'%(kernel_id, file_path))
