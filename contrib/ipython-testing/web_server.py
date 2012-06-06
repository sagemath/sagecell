
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

from IPython.zmq.session import Session


wsgi_app = tornado.wsgi.WSGIContainer(app)


"""
Globals
"""

_kernel_id_regex = r"(?P<kernel_id>\w+-\w+-\w+-\w+-\w+)"

"""
Tornado Handlers
"""

class ZMQStreamHandler(tornado.websocket.WebSocketHandler):
    def open(self, kernel_id):
        self.km = self.application.km
        self.kernel_id = kernel_id
        self.session = Session()

    def _reserialize_reply(self, msg_list):
        idents, msg_list = self.session.feed_identities(msg_list)
        msg = self.session.unserialize(msg_list)
        try:
            msg["header"].pop("date")
        except KeyError:
            pass
        msg.pop("buffers")
        return jsonapi.dumps(msg)

    def _on_zmq_reply(self, msg_list):
        try:
            message = self._reserialize_reply(msg_list)
            print "IOPUB HANDLER MESSAGE RECEIVED: ", message
            self.write_message(message)
        except:
            pass
        

class ShellHandler(ZMQStreamHandler):
    def open(self, kernel_id):
        print "*"*10, " BEGIN SHELL HANDLER ", "*"*10

        super(ShellHandler, self).open(kernel_id)

        self.shell_stream = self.km.create_shell_stream(self.kernel_id)
        print "shell stream created for %s"%kernel_id
        print "*"*10, " END SHELL HANDLER ", "*"*10

    def on_message(self, message):
        print "SHELL HANDLER MESSAGE RECEIVED: ", message
        msg = json.loads(message)
        self.session.send(self.shell_stream, msg)
        self.set_status

    def on_close(self):
        if self.shell_stream is not None and not self.shell_stream.closed():
            self.shell_stream.close()

class IOPubHandler(ZMQStreamHandler):
    def open(self, kernel_id):
        print "*"*10, " BEGIN IOPUB HANDLER ", "*"*10
        super(IOPubHandler, self).open(kernel_id)

        self.iopub_stream = self.km.create_iopub_stream(self.kernel_id)
        self.iopub_stream.on_recv(self._on_zmq_reply)
        print "iopub_stream created for %s"%kernel_id
        print "*"*10, " END IOPUB HANDLER ", "*"*10

    def on_message(self, msg):
        pass

    def on_close(self):
        if self.iopub_stream is not None and not self.iopub_stream.closed():
            self.iopub_stream.on_recv(None)
            self.iopub_stream.close()



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
