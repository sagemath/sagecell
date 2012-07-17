import time, string, urllib, zlib, base64, uuid, json, os.path

import tornado.web
import tornado.websocket
import sockjs.tornado
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
    def get(self):
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
            options["autoeval"] = "false" if "autoeval" in self.request.arguments and self.get_argument("autoeval") == "false" else "true"
        else:
            options["code"] = None

        self.render("root.html", **options)

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
    def post(self):
        proto = self.request.protocol.replace("http", "ws", 1)
        host = self.request.host
        ws_url = "%s://%s/" % (proto, host)
        km = self.application.km
        kernel_id = km.new_session()
        data = {"ws_url": ws_url, "kernel_id": kernel_id}
        if self.request.headers["Accept"] == "application/json":
            self.set_header("Access-Control-Allow-Origin", "*");
        else:
            data = '<script>parent.postMessage(%s,"*");</script>' % (json.dumps(data),)
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

class PermalinkHandler(tornado.web.RequestHandler):
    """
    Permalink generation request handler.

    This accepts the string version of an IPython
    execute_request message, and stores the code associated
    with that request in a database linked to a unique id,
    which is returned to the requester in a JSON-compatible
    form.

    The specified id can be used to generate permalinks
    with the format ``<root_url>?q=<id>``.
    """
    def post(self):
        args = self.request.arguments

        retval = {"permalink": None}
        if "message" in args:
            db = self.application.db
            try:
                message = jsonapi.loads("".join(args["message"]))
                if message["header"]["msg_type"] == "execute_request":
                    retval["permalink"] = db.new_exec_msg(message)
            except:
                pass
        if self.request.headers["Accept"] == "application/json":
            self.set_header("Access-Control-Allow-Origin", "*");
        else:
            retval = '<script>parent.postMessage(%s,"*");</script>' % (json.dumps(retval),)
            self.set_header("Content-Type", "text/html")
        self.write(retval)
        self.finish()

class StaticHandler(tornado.web.StaticFileHandler):
    """Handler for static requests"""
    def set_extra_headers(self, path):
        self.set_header("Access-Control-Allow-Origin", "*")

class ServiceHandler(tornado.web.RequestHandler):
    """
    Implements a blocking web service to execute a single
    computation the server.

    The code to be executed can be specified using the
    URL format ``<root_url>/service?code=<code>``.

    This handler is currently not production-ready.
    """
    def post(self):
        retval = {"success": False,
                  "output": ""}
        args = self.request.arguments

        if "code" in args:
            code = "".join(args["code"])

            default_timeout = 30 # seconds
            poll_interval = 0.1 # seconds

            km = self.application.km
            kernel_id = km.new_session()

            shell_messages = []
            iopub_messages = []

            shell_handler = ShellServiceHandler(self.application)
            iopub_handler = IOPubServiceHandler(self.application)
            
            shell_handler.open(kernel_id, shell_messages)
            iopub_handler.open(kernel_id, iopub_messages)
            
            msg_id = str(uuid.uuid4())
            
            exec_message = {"parent_header": {},
                            "header": {"msg_id": msg_id,
                                       "username": "",
                                       "session": kernel_id,
                                       "msg_type": "execute_request",
                                       },
                            "content": {"code": code,
                                        "silent": False,
                                        "user_variables": [],
                                        "user_expressions": {},
                                        "allow_stdin": False,
                                        },
                            }
            
            shell_handler.on_message(jsonapi.dumps(exec_message))
            
            end_time = time.time()+default_timeout

            done = False
            while not done and time.time() < end_time:
                shell_handler.shell_stream.flush()
                iopub_handler.iopub_stream.flush()
                
                for msg_string in shell_messages:
                    msg = jsonapi.loads(msg_string)
                    msg_type = msg.get("msg_type")
                    content = msg["content"]
                    if msg_type == "execute_reply":
                        if content["status"] == "ok":
                            retval["success"] = True
                        done = True
                        break

                time.sleep(poll_interval)

            for msg_string in iopub_messages:
                msg = jsonapi.loads(msg_string)
                msg_type = msg.get("msg_type")
                content = msg["content"]
                
                if msg_type == "stream" and content["name"] == "stdout":
                    retval["output"] += content["data"]
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
            self._output_message(message)
        except:
            pass
    
    def _output_message(self, message):
        raise NotImplementedError

class ShellHandler(ZMQStreamHandler):
    """
    This handles the websocket-ZMQ bridge for the shell
    stream of an IPython kernel.
    """
    def open(self, kernel_id):
        super(ShellHandler, self).open(kernel_id)
        self.shell_stream = self.km.create_shell_stream(self.kernel_id)
        self.shell_stream.on_recv(self._on_zmq_reply)

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
                    if not self.km._kernels[self.kernel_id]["executing"]:
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
            self.application.km.end_session(self.kernel_id)
        except:
            pass
        self._output_message(json.dumps(
            {'header': {'msg_type': 'status'},
             'parent_header': {},
             'content': {'execution_state':'dead'}
            }
        ))
        self.on_close()

class ShellServiceHandler(ShellHandler):
    def __init__(self, application):
        self.application = application

    def open(self, kernel_id, output_list):
        super(ShellServiceHandler, self).open(kernel_id)
        self.output_list = output_list

    def _output_message(self, message):
        self.output_list.append(message)

class IOPubServiceHandler(IOPubHandler):
    def __init__(self, application):
        self.application = application

    def open(self, kernel_id, output_list):
        super(IOPubServiceHandler, self).open(kernel_id)
        self.output_list = output_list

    def _output_message(self, message):
        self.output_list.append(message)

class ShellWebHandler(ShellHandler, tornado.websocket.WebSocketHandler):
    def _output_message(self, message):
        self.write_message(message)

class IOPubWebHandler(IOPubHandler, tornado.websocket.WebSocketHandler):
    def _output_message(self, message):
        self.write_message(message)

class ShellSockJSHandler(ShellHandler):
    def __init__(self, kernel_id, callback, application):
        self.kernel_id = kernel_id
        self.callback = callback
        self.application = application

    def _output_message(self, message):
        self.callback("%s/shell,%s" % (self.kernel_id, message))

class IOPubSockJSHandler(IOPubHandler):
    def __init__(self, kernel_id, callback, application):
        self.kernel_id = kernel_id
        self.callback = callback
        self.application = application

    def _output_message(self, message):
        self.callback("%s/iopub,%s" % (self.kernel_id, message))

class FileHandler(tornado.web.StaticFileHandler):
    """
    Files handler
    
    This takes in a filename and returns the file
    """
    def get(self, kernel_id, file_path):
        super(FileHandler, self).get('%s/%s'%(kernel_id, file_path))
