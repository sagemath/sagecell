import base64, json, math, os.path, re, time, urllib, uuid, zlib

from log import StatsMessage, logger, stats_logger

import tornado.gen
import tornado.ioloop
import tornado.web
import tornado.websocket
import sockjs.tornado
from zmq.utils import jsonapi

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
from misc import sage_json, Config
config = Config()


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
            if config.get_config("requires_tos") and \
                    self.get_argument("accepted_tos", "false") != "true":
                self.set_status(403)
                self.finish()
                return
            logger.info('starting kernel for session '
                         + self.get_argument('CellSessionID', '(no ID)'))
            proto = self.request.protocol.replace("http", "ws", 1)
            host = self.request.host
            ws_url = "%s://%s/" % (proto, host)
            timeout = self.get_argument("timeout", 0)
            kernel_id = yield tornado.gen.Task(
               self.application.km.new_session_async,
               referer=self.request.headers.get('Referer', ''),
               remote_ip=self.request.remote_ip,
               timeout=timeout)
            data = {"ws_url": ws_url, "id": kernel_id}
            self.set_header("Jupyter-Kernel-ID", kernel_id)
            self.write(self.permissions(data))
            self.finish()


    def delete(self, kernel_id):
        self.application.km.end_session(kernel_id)
        self.permissions()
        self.finish()

    def options(self, kernel_id=None):
        logger.debug("KernelHandler.options for kernel_id %s", kernel_id)
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

    def __init__(self, km):
        self.waiting = {}
        self.kernel_id = km.new_session(limited=False)
        self.session = km._sessions[self.kernel_id]
        self.stream = km.create_shell_stream(self.kernel_id)
        self.stream.on_recv(self.on_recv)

    def registerRequest(self, kc, msg):
        mode = msg["content"].get("mode", "sage")
        if mode in ("sage", "python"):
            self.waiting[msg["header"]["msg_id"]] = kc
            self.session.send(self.stream, msg)
            return
        match = Completer.name_pattern.search(
            msg["content"]["line"][:msg["content"]["cursor_pos"]])
        response = {
            "channel": "shell",
            "header": {
                "msg_id": str(uuid.uuid4()),
                "username": "",
                "session": self.kernel_id,
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
        kc.send("complete," + jsonapi.dumps(response))

    def on_recv(self, msg):
        msg = self.session.feed_identities(msg)[1]
        msg = self.session.unserialize(msg)
        msg_id = msg["parent_header"]["msg_id"]
        kc = self.waiting.pop(msg_id)
        kc.send("complete," + jsonapi.dumps(msg, default=sage_json))


class KernelConnection(sockjs.tornado.SockJSConnection):

    def on_open(self, request):
        self.channels = {}

    def on_message(self, message):
        prefix, json_message = message.split(",", 1)
        kernel_id = prefix.split("/", 1)[0]
        message = jsonapi.loads(json_message)
        logger.debug("KernelConnection.on_message: %s", message)
        application = self.session.handler.application
        if kernel_id == "complete":
            if message["header"]["msg_type"] in ("complete_request",
                                                 "object_info_request"):
                application.completer.registerRequest(self, message)
            return
        try:
            if kernel_id not in self.channels:
                # handler may be None in certain circumstances (it seems to only be set
                # in GET requests, not POST requests, so even using it here may
                # only work with JSONP because of a race condition)
                kernel_info = application.km.kernel_info(kernel_id)
                self.kernel_info = {'remote_ip': kernel_info['remote_ip'],
                                    'referer': kernel_info['referer'],
                                    'timeout': kernel_info['timeout']}
            if message["header"]["msg_type"] == "execute_request":
                stats_logger.info(StatsMessage(
                    kernel_id=kernel_id,
                    remote_ip=self.kernel_info['remote_ip'],
                    referer=self.kernel_info['referer'],
                    code=message["content"]["code"],
                    execute_type='request'))
            if kernel_id not in self.channels:
                self.channels[kernel_id] = SockJSChannelsHandler(self.send)
                self.channels[kernel_id].open(application, kernel_id)
            self.channels[kernel_id].on_message(json_message)
        except KeyError:
            # Ignore messages to nonexistent or killed kernels.
            import traceback
            logger.info("%s message sent to nonexistent kernel: %s\n%s" %
                        (message["header"]["msg_type"], kernel_id,
                        traceback.format_exc()))

    def on_close(self):
        for channel in self.channels.itervalues():
            channel.on_close()


KernelRouter = sockjs.tornado.SockJSRouter(KernelConnection, "/sockjs")


class TOSHandler(tornado.web.RequestHandler):
    """Handler for ``/tos.html``"""
    tos = config.get_config("requires_tos")
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
        if (config.get_config('requires_tos')
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
        self.kernel_id = yield tornado.gen.Task(
            self.application.km.new_session_async,
            referer=referer,
            remote_ip=remote_ip,
            timeout=0)
        sm = StatsMessage(
            kernel_id=self.kernel_id,
            remote_ip=remote_ip,
            referer=referer,
            code=code,
            execute_type='service')
        if remote_ip == '127.0.0.1' and self.kernel_id:
            stats_logger.debug(sm)
        else:
            stats_logger.info(sm)
        if not self.kernel_id:
            logger.error('could not obtain a valid kernel_id')
            self.set_status(503)
            self.finish()
            return
        self.zmq_handler = ZMQServiceHandler()
        self.zmq_handler.open(self.application, self.kernel_id)
        loop = tornado.ioloop.IOLoop.instance()
        
        def kernel_callback(msg):
            if msg['msg_type'] == 'execute_reply':
                loop.remove_timeout(self.timeout_handle)
                logger.debug('service request finished for %s', self.kernel_id)
                streams = self.zmq_handler.streams
                streams['success'] = msg['content']['status'] == 'ok'
                streams['execute_reply'] = msg['content']
                loop.add_callback(self.finish_request)
                
        self.zmq_handler.msg_from_kernel_callbacks.append(kernel_callback)
        
        def timeout_callback():
            logger.debug('service request timed out for %s', self.kernel_id)
            loop.add_callback(self.finish_request)

        self.timeout_handle = loop.call_later(30, timeout_callback)
        exec_message = {
            'channel': 'shell',
            'parent_header': {},
            'header': {
                'msg_id': str(uuid.uuid4()),
                'username': '',
                'session': self.kernel_id,
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
        self.zmq_handler.on_message(jsonapi.dumps(exec_message))

    def finish_request(self):
        self.application.km.end_session(self.kernel_id)
        self.zmq_handler.on_close()
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
        return jsonapi.dumps(msg, default=sage_json)

    def _on_zmq_reply(self, stream, msg_list):
        if stream.closed():
            return
        try:
            idents, msg_list = self.session.feed_identities(msg_list)
            msg = self.session.unserialize(msg_list)
            if all([f(msg) is not False
                    for f in self.msg_from_kernel_callbacks]):
                msg["channel"] = stream.channel
                self._output_message(msg)
        except ValueError as e:
            logger.exception("ValueError in _on_zmq_reply: %s", e.message)
        if stream.channel == "shell" and self.kill_kernel:
            self.channels["shell"].flush()
            self.kernel_died()

    def _reset_deadline(self, msg):
        if msg["header"]["msg_type"] in ("execute_reply",
                                         "sagenb.interact.update_interact_reply"):
            timeout = self.kernel["timeout"]
            if timeout == 0 and self.kernel["executing"] == 1:
                # kill the kernel before the heartbeat is able to
                self.kill_kernel = True
            else:
                self.kernel["deadline"] = min(
                    time.time() + timeout, self.kernel["hard_deadline"])
                self.kernel["executing"] -= 1
                logger.debug("decreased execution counter for %s to %s",
                             self.kernel_id, self.kernel["executing"])

    def _reset_timeout(self, msg):
        if msg["header"]["msg_type"] == "kernel_timeout":
            timeout = float(msg["content"]["timeout"])
            if timeout >= 0:
                self.kernel["timeout"] = min(
                    timeout, self.kernel["max_timeout"])
            return False

    def kernel_died(self):
        try: # in case kernel has already been killed
            self.channels["iopub"].flush()
            self.application.km.end_session(self.kernel_id)
        except IOError:
            pass
        msg = {
            "channel": "iopub",
            'header': {
                'msg_type': 'status',
                'session': self.kernel_id,
                'msg_id': str(uuid.uuid4()),
                'username': ''
            },
            'parent_header': {},
            'metadata': {},
            'content': {'execution_state': 'dead'}
        }
        self._output_message(msg)
        self.on_close()

    def on_close(self):
        for stream in self.channels.itervalues():
            if stream is not None and not stream.closed():
                stream.on_recv_stream(None)
                stream.close()
        if hasattr(self, "hb_stream") and not self.hb_stream.closed():
            self.stop_hb()
        self.application.km.end_session(self.kernel_id)

    def on_message(self, msg):
        # shell only, was just pass in iopub
        if self.application.km._kernels.get(self.kernel_id) is not None:
            msg = jsonapi.loads(msg)
            for f in self.msg_to_kernel_callbacks:
                f(msg)
            if msg['header']['msg_type'] in ('execute_request',
                                             'sagenb.interact.update_interact'):
                self.kernel["executing"] += 1
                logger.debug("increased execution counter for %s to %s",
                             self.kernel_id, self.kernel["executing"])
            self.session.send(self.channels["shell"], msg)

    def open(self, application, kernel_id):
        self.application = application
        self.kernel_id = kernel_id
        km = application.km
        self.session = km._sessions[kernel_id]
        self.kernel = km._kernels[kernel_id]
        self.msg_from_kernel_callbacks = [self._reset_deadline,
                                          self._reset_timeout]
        self.msg_to_kernel_callbacks = []
        
        # Useful but may be way to verbose even for debugging
        #def log_from(message): logger.debug("log_from %s", message)
        #self.msg_from_kernel_callbacks.insert(0, log_from)
        #def log_to(message): logger.debug("log_to %s", message)
        #self.msg_to_kernel_callbacks.insert(0, log_to)
        
        self.kill_kernel = False
        self.channels = {}
        for channel in ('shell', 'iopub'):  #, 'stdin'
            meth = getattr(km, 'create_' + channel + "_stream")
            self.channels[channel] = stream = meth(kernel_id)
            stream.channel = channel
            stream.on_recv_stream(self._on_zmq_reply)
        self.start_hb()

    def start_hb(self):
        """
        Starts a series of delayed callbacks to send and
        receive small messages from the heartbeat stream of
        an IPython kernel. The specific delay paramaters for
        the callbacks are set by configuration values in a
        kernel manager associated with the web application.
        """
        logger.debug("start_hb for %s", self.kernel_id)
        self._kernel_alive = True
        km = self.application.km
        self.hb_stream = km.create_hb_stream(self.kernel_id)

        def beat_received(message):
            self._kernel_alive = True

        self.hb_stream.on_recv(beat_received)

        def ping_or_dead():
            self.hb_stream.flush()
            if (self.kernel["executing"] == 0
                and time.time() > self.kernel["deadline"]):
                # only kill the kernel after all pending
                # execute requests have finished
                self._kernel_alive = False
            if self._kernel_alive:
                self._kernel_alive = False
                self.hb_stream.send(b'ping')
                # flush stream to force immediate socket send
                self.hb_stream.flush()
            else:
                self.kernel_died()
                self.stop_hb()

        beat_interval, first_beat = km.get_hb_info(self.kernel_id)
        loop = tornado.ioloop.IOLoop.instance()
        self._hb_periodic_callback = \
            tornado.ioloop.PeriodicCallback(
                ping_or_dead, beat_interval * 1000, loop)

        def delayed_start():
            # Make sure we haven't been closed during the wait.
            logger.debug("delayed_start for %s", self.kernel_id)
            if self._beating and not self.hb_stream.closed():
                self._hb_periodic_callback.start()

        self._start_hb_handle = loop.add_timeout(time.time() + first_beat, delayed_start)
        self._beating = True

    def stop_hb(self):
        """Stop the heartbeating and cancel all related callbacks."""
        logger.debug("stop_hb for %s", self.kernel_id)
        if self._beating:
            self._beating = False
            self._hb_periodic_callback.stop()
            tornado.ioloop.IOLoop.instance().remove_timeout(
                self._start_hb_handle)
            if not self.hb_stream.closed():
                self.hb_stream.on_recv(None)
                self.hb_stream.close()


class ZMQServiceHandler(ZMQChannelsHandler):

    def _output_message(self, msg):
        if msg["channel"] == "iopub":
            if msg["header"]["msg_type"] == "stream":
                self.streams[msg["content"]["name"]] += msg["content"]["text"]

    def open(self, application, kernel_id):
        super(ZMQServiceHandler, self).open(application, kernel_id)
        from collections import defaultdict
        self.streams = defaultdict(unicode)


class SockJSChannelsHandler(ZMQChannelsHandler):

    def __init__(self, callback):
        self.callback = callback

    def _output_message(self, msg):
        self.callback("%s/channels,%s" % (self.kernel_id, self._json_msg(msg)))


class WebChannelsHandler(ZMQChannelsHandler,
                         tornado.websocket.WebSocketHandler):

    def _output_message(self, msg):
        self.write_message(self._json_msg(msg))
        
    def open(self, kernel_id):
        super(WebChannelsHandler, self).open(self.application, kernel_id)


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
