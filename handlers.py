import base64
import collections
import json
import os.path
import re
import time
import urllib
import uuid
import zlib

import tornado.gen
import tornado.ioloop
import tornado.web
import tornado.websocket
import sockjs.tornado
from zmq.utils import jsonapi

from log import StatsMessage, logger, stats_logger


try:
    from sage.all import gap, gp, maxima, r, singular
    tab_completion = {
        "gap": gap._tab_completion(),
        "gp": gp._tab_completion(),
        "maxima": maxima._tab_completion(),
        "r": r._tab_completion(),
        "singular": singular._tab_completion()
    }
except ImportError:
    tab_completion = {}

import misc
config = misc.Config()


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
        logger.debug('RootHandler.get')
        args = self.request.arguments
        code = None
        language = args["lang"][0] if "lang" in args else None
        interacts = None
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
                if "interacts" in args:
                    interacts = "".join(args["interacts"])
                    interacts += "=" * ((4 - (len(interacts) % 4)) % 4)
                    interacts = zlib.decompress(base64.urlsafe_b64decode(interacts))
                code = zlib.decompress(base64.urlsafe_b64decode(z))
            except Exception as e:
                self.set_status(400)
                self.finish("Invalid zipped code: %s\n" % (e.message,))
                return
        if "q" in args:
            # The code is referenced by a permalink identifier.
            q = "".join(args["q"])
            try:
                self.application.db.get_exec_msg(q, self.return_root)
            except LookupError:
                self.set_status(404)
                self.finish("ID not found in permalink database")
        else:
            self.return_root(code, language, interacts)

    def return_root(self, code, language, interacts):
        autoeval = None
        if code is not None:
            if isinstance(code, unicode):
                code = code.encode("utf8")
            code = urllib.quote(code)
            autoeval = "false" if "autoeval" in self.request.arguments and self.get_argument("autoeval") == "false" else "true"
        if interacts is not None:
            if isinstance(interacts, unicode):
                interacts = interacts.encode("utf8")
            interacts = urllib.quote(interacts)
        self.render("root.html", code=code, lang=language, interacts=interacts, autoeval=autoeval)

    def options(self):
        self.set_status(200)


class HelpHandler(tornado.web.RequestHandler):
    """
    Render templates/help.html.
    """
    def get(self):
        self.render("help.html")


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
    @tornado.gen.engine
    def post(self, *args, **kwargs):
        method = self.get_argument("method", "POST")
        if method == "DELETE":
            self.delete(*args, **kwargs)
        elif method == "OPTIONS":
            self.options(*args, **kwargs)
        else:
            if config.get("requires_tos") and \
                    self.get_argument("accepted_tos", "false") != "true":
                self.set_status(403)
                self.finish()
                return
            logger.info('starting kernel for session '
                         + self.get_argument('CellSessionID', '(no ID)'))
            proto = self.request.protocol.replace("http", "ws", 1)
            host = self.request.host
            ws_url = "%s://%s/" % (proto, host)
            timeout = min(float(self.get_argument("timeout", 0)),
                          config.get("max_timeout"))
            kernel = yield tornado.gen.Task(
                self.application.kernel_dealer.get_kernel,
                rlimits=config.get("provider_settings")["preforked_rlimits"],
                lifespan=config.get("max_lifespan"),
                timeout=timeout)
            kernel.referer=self.request.headers.get('Referer', '')
            kernel.remote_ip=self.request.remote_ip
            data = {"ws_url": ws_url, "id": kernel.id}
            self.set_header("Jupyter-Kernel-ID", kernel.id)
            self.write(self.permissions(data))
            self.finish()

    def delete(self, kernel_id):
        self.application.kernel_dealer.kernel(kernel_id).stop()
        self.permissions()
        self.finish()

    def options(self, kernel_id=None):
        self.permissions()
        self.finish()

    def permissions(self, data=None):
        if "frame" not in self.request.arguments:
            if "Origin" in self.request.headers:
                self.set_header("Access-Control-Allow-Origin",
                                self.request.headers["Origin"])
                self.set_header("Access-Control-Allow-Credentials", "true")
                self.set_header("Access-Control-Allow-Methods",
                                "POST, GET, OPTIONS, DELETE")
                self.set_header("Access-Control-Allow-Headers", "Content-Type")
        else:
            data = '<script>parent.postMessage(%r,"*");</script>' % (json.dumps(data),)
            self.set_header("Content-Type", "text/html")
        return data


class Completer(object):
    
    name_pattern = re.compile(r"\b[a-z_]\w*$", re.IGNORECASE)

    def __init__(self, kernel_dealer):
        self.waiting = {}
        self.kernel = None
        
        def callback(kernel):
            self.kernel = kernel
            self.kernel.channels["shell"].on_recv(self.on_recv)
            
        kernel_dealer.get_kernel(callback)

    def registerRequest(self, addr, msg):
        content = msg["content"]
        mode = content.get("mode", "sage")
        if mode in ("sage", "python"):
            self.waiting[msg["header"]["msg_id"]] = addr
            if self.kernel is None:
                # It is highly unlikely that we get a completion request before
                # the kernel is ready, so we are not going to handle it.
                logger.exception("completer kernel is not available")
            self.kernel.session.send(self.kernel.channels["shell"], msg)
            return
        match = Completer.name_pattern.search(
            content["line"][:content["cursor_pos"]])
        response = {
            "channel": "shell",
            "header": {
                "msg_id": str(uuid.uuid4()),
                "username": "",
                "session": self.kernel.id,
                "msg_type": "complete_reply"
            },
            "parent_header": msg["header"],
            "metadata": {},
            "content": {
                "matches": [t for t in tab_completion.get(mode, [])
                            if t.startswith(match.group())],
                "cursor_start": match.start(),
            },
        }
        addr.send("complete," + jsonapi.dumps(response))

    def on_recv(self, msg):
        msg = self.kernel.session.feed_identities(msg)[1]
        msg = self.kernel.session.unserialize(msg)
        addr = self.waiting.pop(msg["parent_header"]["msg_id"])
        addr.send("complete," + jsonapi.dumps(msg, default=misc.sage_json))


class SockJSHandler(sockjs.tornado.SockJSConnection):

    def on_open(self, request):
        self.channels = {}

    def on_message(self, message):
        prefix, message = message.split(",", 1)
        id = prefix.split("/", 1)[0]
        message = jsonapi.loads(message)
        logger.debug("SockJSHandler.on_message: %s", message)
        msg_type = message["header"]["msg_type"]
        app = self.session.handler.application
        if id == "complete":
            if msg_type in ("complete_request", "object_info_request"):
                app.completer.registerRequest(self, message)
            return
        try:
            kernel = app.kernel_dealer.kernel(id)
        except KeyError:
            # Ignore messages to nonexistent or killed kernels.
            logger.warning("%s sent to nonexistent kernel %s", msg_type, id)
            return
        if id not in self.channels:
            self.channels[id] = SockJSChannelsHandler(self.send)
            self.channels[id].connect(kernel)
        if msg_type == "execute_request":
            stats_logger.info(StatsMessage(
                kernel_id=id,
                remote_ip=kernel.remote_ip,
                referer=kernel.referer,
                code=message["content"]["code"],
                execute_type="request"))
        self.channels[id].send(message)

    def on_close(self):
        while self.channels:
            self.channels.popitem()[1].disconnect()


KernelRouter = sockjs.tornado.SockJSRouter(SockJSHandler, "/sockjs")


class TOSHandler(tornado.web.RequestHandler):
    """Handler for ``/tos.html``"""
    tos = config.get("requires_tos")
    if tos:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "tos.html")
        with open(path) as f:
            tos_html = f.read()
            tos_json = json.dumps(tos_html)
    else:
        tos_html = "No Terms of Service Required"
        tos_json = json.dumps(tos_html)
    
    def post(self):
        if len(self.get_arguments("callback")) == 0:
            if self.tos:
                self.write(self.tos_html)
            else:
                self.set_status(204)
            if "Origin" in self.request.headers:
                self.set_header("Access-Control-Allow-Origin",
                                self.request.headers["Origin"])
                self.set_header("Access-Control-Allow-Credentials", "true")
            self.set_header("Content-Type", "text/html")
        else:
            resp = self.tos_json if self.tos else '""'
            self.write("%s(%s);" % (self.get_argument("callback"), resp))
            self.set_header("Content-Type", "application/javascript")

    def get(self):
        if self.tos:
            self.write(self.tos_html)
        else:
            raise tornado.web.HTTPError(404, 'No Terms of Service Required')


class ServiceHandler(tornado.web.RequestHandler):
    """
    Implements a blocking (to the client) web service to execute a single
    computation the server.  This should be non-blocking to Tornado.

    The code to be executed is given in the code request parameter.

    This handler is currently not production-ready. But it is used for health
    checks...
    """

    @tornado.web.asynchronous
    @tornado.gen.engine
    def post(self):
        if 'Origin' in self.request.headers:
            self.set_header(
                'Access-Control-Allow-Origin', self.request.headers['Origin'])
            self.set_header('Access-Control-Allow-Credentials', 'true')
        if (config.get('requires_tos')
                and self.get_argument('accepted_tos', 'false') != 'true'):
            self.set_status(403)
            self.finish(
                'When evaluating code, you must acknowledge your acceptance '
                'of the terms of service at /static/tos.html by passing the '
                'parameter accepted_tos=true\n')
            return
        code = ''.join(self.get_arguments('code', strip=False))
        if len(code) > 65000:
            self.set_status(413)
            self.finish('Max code size is 65000 characters')
            return
        remote_ip = self.request.remote_ip
        referer = self.request.headers.get('Referer', '')
        self.kernel = yield tornado.gen.Task(
            self.application.kernel_dealer.get_kernel,
            rlimits=config.get("provider_settings")["preforked_rlimits"],
            lifespan=config.get("max_lifespan"),
            timeout=0)
        sm = StatsMessage(
            kernel_id=self.kernel.id,
            remote_ip=remote_ip,
            referer=referer,
            code=code,
            execute_type='service')
        if remote_ip == '127.0.0.1':
            stats_logger.debug(sm)
        else:
            stats_logger.info(sm)
        self.zmq_handler = ZMQServiceHandler()
        streams = self.zmq_handler.streams
        self.zmq_handler.connect(self.kernel)
        loop = tornado.ioloop.IOLoop.instance()
        
        def kernel_callback(msg):
            if msg['msg_type'] == 'execute_reply':
                loop.remove_timeout(self.timeout_handle)
                streams['success'] = msg['content']['status'] == 'ok'
                streams['execute_reply'] = msg['content']
            if self.kernel.status == "idle" and 'success' in streams:
                logger.debug('service request finished for %s', self.kernel.id)
                loop.add_callback(self.finish_request)
                
        self.zmq_handler.msg_from_kernel_callbacks.append(kernel_callback)
        
        def timeout_callback():
            logger.debug('service request timed out for %s', self.kernel.id)
            self.kernel.stop()
            self.zmq_handler.streams['success'] = False
            loop.add_callback(self.finish_request)

        self.timeout_handle = loop.call_later(30, timeout_callback)
        exec_message = {
            'channel': 'shell',
            'parent_header': {},
            'header': {
                'msg_id': str(uuid.uuid4()),
                'username': '',
                'session': self.kernel.id,
                'msg_type': 'execute_request',
               },
            'content': {
                'code': code,
                'silent': False,
                'user_expressions':
                    jsonapi.loads(self.get_argument('user_expressions', '{}')),
                'allow_stdin': False,
                },
            'metadata': {},
            }
        self.zmq_handler.send(exec_message)

    def finish_request(self):
        self.finish(self.zmq_handler.streams)


class ZMQChannelsHandler(object):
    """
    This handles the websocket-ZMQ bridge to an IPython kernel.

    It also handles the heartbeat (hb) stream that same kernel, but there is no
    associated websocket connection. The websocket is instead used to notify
    the client if the heartbeat stream fails.
    """

    def _json_msg(self, msg):
        """
        Converts a single message into a JSON string
        """
        # can't encode buffers, so let's get rid of them if they exist
        msg.pop("buffers", None)
        # sage_json handles things like encoding dates and sage types
        return jsonapi.dumps(msg, default=misc.sage_json)

    def connect(self, kernel):
        self.kernel = kernel
        self.msg_from_kernel_callbacks = []
        self.msg_to_kernel_callbacks = []
        for channel in ["iopub", "shell"]:
            kernel.channels[channel].on_recv_stream(self.on_recv)
        kernel.on_stop(self.kernel_stopped)

    def disconnect(self):
        for channel in ["iopub", "shell"]:
            if not self.kernel.channels[channel].closed():
                self.kernel.channels[channel].on_recv_stream(None)

    def kernel_stopped(self):
        msg = {
            "channel": "iopub",
            'header': {
                'msg_type': 'status',
                'session': self.kernel.id,
                'msg_id': str(uuid.uuid4()),
                'username': ''
            },
            'parent_header': {},
            'metadata': {},
            'content': {'execution_state': 'dead'}
        }
        self.output_message(msg)
        self.disconnect()

    def on_recv(self, stream, msg_list):
        kernel = self.kernel
        msg_list = kernel.session.feed_identities(msg_list)[1]
        msg = kernel.session.unserialize(msg_list)
        msg["channel"] = stream.channel
        # Useful but may be way too verbose even for debugging
        #logger.debug("received from kernel %s", msg)
        msg_type = msg["msg_type"]
        if msg_type == "status":
            kernel.status = msg["content"]["execution_state"]
        if msg_type in ("execute_reply",
                        "sagenb.interact.update_interact_reply"):
            kernel.executing -= 1
            logger.debug("decreased execution counter for %s to %s",
                         kernel.id, kernel.executing)
        if msg_type == "kernel_timeout":
            timeout = float(msg["content"]["timeout"])
            logger.debug("reset timeout for %s to %f", kernel.id, timeout)
            if timeout >= 0:
                kernel.timeout = min(timeout, config.get("max_timeout"))
        else:
            for callback in self.msg_from_kernel_callbacks:
                callback(msg)
            self.output_message(msg)
        if kernel.timeout > 0:
            kernel.deadline = time.time() + kernel.timeout
        elif kernel.executing == 0 and kernel.status == "idle":
            logger.debug("stopping on %s, %s", stream.channel, msg_type)
            kernel.stop()

    def send(self, msg):
        # Useful but may be way too verbose even for debugging
        #logger.debug("sending to kernel %s", msg)
        for f in self.msg_to_kernel_callbacks:
            f(msg)
        kernel = self.kernel
        if msg['header']['msg_type'] in ('execute_request',
                                         'sagenb.interact.update_interact'):
            kernel.executing += 1
            logger.debug("increased execution counter for %s to %s",
                kernel.id, kernel.executing)
        kernel.session.send(kernel.channels["shell"], msg)


class ZMQServiceHandler(ZMQChannelsHandler):
    
    def __init__(self):
        super(ZMQServiceHandler, self).__init__()
        self.streams = collections.defaultdict(unicode)

    def output_message(self, msg):
        if msg["channel"] == "iopub" and msg["header"]["msg_type"] == "stream":
            self.streams[msg["content"]["name"]] += msg["content"]["text"]


class SockJSChannelsHandler(ZMQChannelsHandler):

    def __init__(self, callback):
        self.callback = callback

    def output_message(self, msg):
        self.callback("%s/channels,%s" % (self.kernel.id, self._json_msg(msg)))


class WebChannelsHandler(ZMQChannelsHandler,
                         tornado.websocket.WebSocketHandler):

    def on_close(self):
        self.disconnect()

    def on_message(self, msg):
        self.send(jsonapi.loads(msg))

    def open(self, kernel_id):
        self.connect(self.application.kernel_dealer.kernel(kernel_id))

    def output_message(self, msg):
        self.write_message(self._json_msg(msg))
        

class StaticHandler(tornado.web.StaticFileHandler):
    """Handler for static requests"""
    
    def set_extra_headers(self, path):
        if "Origin" in self.request.headers:
            self.set_header("Access-Control-Allow-Origin",
                            self.request.headers["Origin"])
            self.set_header("Access-Control-Allow-Credentials", "true")


class FileHandler(StaticHandler):
    """
    Files handler

    This takes in a filename and returns the file
    """
    
    def compute_etag(self):
        # tornado.web.StaticFileHandler uses filenames for etag, but then
        # updated user files get the same one even if recomputed in linked
        # cells. Dropping etag still makes use of modification time.
        return None
        
    def get(self, kernel_id, file_path):
        super(FileHandler, self).get('%s/%s'%(kernel_id, file_path))

    def set_extra_headers(self, path):
        super(FileHandler, self).set_extra_headers(path)
        self.set_header('Cache-Control', 'no-cache')
