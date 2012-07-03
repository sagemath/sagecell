#! /usr/bin/env python

# System imports
import uuid, os, json, urllib, string

# Flask imports
from flask import Flask, request, render_template, redirect, url_for, jsonify, send_file, json, Response, abort, make_response
from hashlib import sha1

# Sage Cell imports
import misc

from trusted_kernel_manager import TrustedMultiKernelManager as TMKM
from db_sqlalchemy import DB

# Flask webserver
app = Flask(__name__)

_VALID_QUERY_CHARS = set(string.letters+string.digits+"-")

@app.route("/")
def root():
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
    db = application.db
    options = {}
    if "c" in request.values:
        # If the code is explicitly specified
        options["code"] = request.values["c"]
    elif "z" in request.values:
        # If the code is base64 compressed
        import zlib, base64
        try:
            z = request.values["z"].encode("ascii")
            # We allow the user to strip off the = padding at the end
            # so that the URL doesn't have to have any escaping
            # here we add back the = padding if we need it
            z += "="*((4-(len(z)%4))%4)
            options["code"] = zlib.decompress(base64.urlsafe_b64decode(z))
        except Exception as e:
            options["code"] = "# Error decompressing code: %s"%e
    elif "q" in request.values and set(request.values["q"]).issubset(_VALID_QUERY_CHARS):
        # If the code is referenced by a permalink identifier
        options["code"] = db.get_exec_msg(request.values["q"])
    if "code" in options:
        if isinstance(options["code"], unicode):
            options["code"] = options["code"].encode("utf8")
        options["code"] = urllib.quote(options["code"])
        options["autoeval"] = False if "autoeval" in request.args and request.args["autoeval"] == "false" else True
    return render_template("root.html", **options)

@app.route("/kernel", methods=["POST"])
def main_kernel():
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

    ws_url = request.url_root.replace("http", "ws")

    km = application.km
    kernel_id = km.new_session()

    print "kernel started with id ::: %s" % kernel_id

    data = json.dumps({"ws_url": ws_url, "kernel_id": kernel_id})
    if (request.values.get("frame") is not None):
        return Response("<script>parent.postMessage(" + json.dumps(data) +
                ",\"*\");</script>")
    else:
        r = Response(data, mimetype="application/json")
        r.headers["Access-Control-Allow-Origin"] = "*"
        return r

_embedded_sagecell_cache = None
@app.route("/embedded_sagecell.js")
def embedded():
    global _embedded_sagecell_cache
    if _embedded_sagecell_cache is None:
        data = Response(render_template("embedded_sagecell.js"),
                        content_type='application/javascript')
        _embedded_sagecell_cache = (data, sha1(repr(data)).hexdigest())
    data,datahash = _embedded_sagecell_cache
    if request.environ.get('HTTP_IF_NONE_MATCH', None) == datahash:
        response = make_response('', 304)
    else:
        response = make_response(data)
        response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
        response.headers['Etag'] = datahash
    return response

@app.route("/permalink", methods=["POST"])
def get_permalink():
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
    rval = {"permalink": None}
    if request.values.get("message") is not None:
        db = application.db
        try:
            message = json.loads(request.values["message"])
            if message["header"]["msg_type"] == "execute_request":
                permalink = db.new_exec_msg(message)
                rval["permalink"] = permalink
        except:
            pass
    r = Response(json.dumps(rval), mimetype="application/json")
    return r
    

"""
Tornado / zmq imports
"""
import zmq
from zmq.eventloop import ioloop
from zmq.utils import jsonapi
import tornado.web
import tornado.wsgi
import tornado.websocket

# Tornado Handlers
from handlers import ShellHandler, IOPubHandler

ioloop.install()

# Allow Flask and Tornado to work together.
wsgi_app = tornado.wsgi.WSGIContainer(app)
# Globals
# This matches a kernel id (uuid4 format) from a url
_kernel_id_regex = r"(?P<kernel_id>\w+-\w+-\w+-\w+-\w+)"

# Tornado Web Server
# Web Server
class SageCellServer(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/kernel/%s/iopub" % _kernel_id_regex, IOPubHandler),
            (r"/kernel/%s/shell" % _kernel_id_regex, ShellHandler),
            (r".*", tornado.web.FallbackHandler, {'fallback': wsgi_app})
            ]
        self.config = misc.Config()

        initial_comps = self.config.get_config("computers")
        default_comp = self.config.get_default_config("_default_config")
        kernel_timeout = self.config.get_config("max_kernel_timeout")

        self.km = TMKM(computers = initial_comps, default_computer_config = default_comp, kernel_timeout = kernel_timeout)

        self.db = DB(misc.get_db_file(self.config))

        super(SageCellServer, self).__init__(handlers)

if __name__ == "__main__":
    application = SageCellServer()
    application.listen(8888)
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print "\nEnding processes."
        application.km.shutdown()
