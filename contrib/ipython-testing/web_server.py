
from trusted_kernel_manager import TrustedMultiKernelManager as TMKM


from flask import Flask, request, render_template, redirect, url_for, jsonify, send_file, json, Response, abort, make_response

import uuid, os

app = Flask(__name__)

@app.route("/")
def root():
    return render_template("root.html")

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


import zmq, os
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
Web Server
"""

class SageCellServer(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/kernel/%s/iopub" % _kernel_id_regex, IOPubHandler),
            (r"/kernel/%s/shell" % _kernel_id_regex, ShellHandler),
            (r".*", tornado.web.FallbackHandler, {'fallback': wsgi_app})
            ]

        self.km = TMKM()
        self.km.setup_initial_comps()
        
        super(SageCellServer, self).__init__(handlers)


if __name__ == "__main__":
    application = SageCellServer()
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
