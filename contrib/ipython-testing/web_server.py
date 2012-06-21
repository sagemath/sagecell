#! /usr/bin/env python

"""
System imports
"""
import uuid, os, json, urllib, string

"""
Flask imports
"""
from flask import Flask, request, render_template, redirect, url_for, jsonify, send_file, json, Response, abort, make_response

"""
Sagecell imports
"""
import misc

from trusted_kernel_manager import TrustedMultiKernelManager as TMKM
from db_sqlalchemy import DB

try:
    import config
except ImportError:
    import config_default as config

"""
Flask webserver
"""
app = Flask(__name__)

_VALID_QUERY_CHARS = set(string.letters+string.digits+"-")

@app.route("/")
def root():
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
        options["autoeval"] = "false" if "autoeval" in request.args and request.args["autoeval"] == "false" else "true"
    return render_template("root.html", **options)

@app.route("/kernel", methods=["POST"])
def main_kernel():
    print "%s BEGIN MAIN KERNEL HANDLER %s"%("*"*10, "*"*10)

    ws_url = request.url_root.replace("http","ws")

    km = application.km
    kernel_id = km.new_session()

    print "kernel started with id ::: %s"%kernel_id

    data = json.dumps({"ws_url": ws_url, "kernel_id": kernel_id})
    r = Response(data, mimetype="application/json")

    print "%s END MAIN KERNEL HANDLER %s"%("*"*10, "*"*10)
    return r

@app.route("/permalink", methods=["POST"])
def get_permalink():
    rval = {"permalink": None}
    if request.values.get("message") is not None:
        db = application.db
        try:
            message = json.loads(request.values["message"])
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
ioloop.install()

import tornado.web
import tornado.wsgi
import tornado.websocket

wsgi_app = tornado.wsgi.WSGIContainer(app)


"""
Globals
"""
_kernel_id_regex = r"(?P<kernel_id>\w+-\w+-\w+-\w+-\w+)"

"""
Tornado Handlers
"""
from handlers import ShellHandler, IOPubHandler

"""
Tornado Web Server
"""
class SageCellServer(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/kernel/%s/iopub" % _kernel_id_regex, IOPubHandler),
            (r"/kernel/%s/shell" % _kernel_id_regex, ShellHandler),
            (r".*", tornado.web.FallbackHandler, {'fallback': wsgi_app})
            ]

        self.config = misc.Config()

        initial_comps = self.config.get_config("computers")

        self.km = TMKM(comps = initial_comps)

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
