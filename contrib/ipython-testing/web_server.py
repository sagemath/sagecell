#! /usr/bin/env python
from trusted_kernel_manager import TrustedMultiKernelManager as TMKM
from flask import Flask, request, render_template, redirect, url_for, jsonify, send_file, json, Response, abort, make_response
import uuid
import os
from hashlib import sha1

app = Flask(__name__)

import string
_VALID_QUERY_CHARS = set(string.letters + string.digits + '-')
@app.route("/")
def root():
    options = {}
    if 'q' in request.values and set(request.values['q']).issubset(_VALID_QUERY_CHARS):
        options['code'] = db.get_input_message_by_shortened(request.values['q'])
    if 'code' in options:
        if isinstance(options['code'], unicode):
            options['code'] = options['code'].encode('utf8')
        options['code'] = quote(options['code'])
        options['autoeval'] = 'false' if 'autoeval' in request.args and request.args['autoeval'] == 'false' else 'true'
    return render_template('root.html', **options)

@app.route("/kernel", methods=["POST"])
def main_kernel():
    print "%s BEGIN MAIN KERNEL HANDLER %s" % ("*" * 10, "*" * 10)

    ws_url = request.url_root.replace("http", "ws")

    km = application.km
    kernel_id = km.new_session()

    print "kernel started with id ::: %s" % kernel_id

    data = json.dumps({"ws_url": ws_url, "kernel_id": kernel_id})
    r = Response(data, mimetype="application/json")

    print "%s END MAIN KERNEL HANDLER %s"%("*" * 10, "*" * 10)
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

import zmq, os
from zmq.eventloop import ioloop
from zmq.utils import jsonapi
import tornado.web
import tornado.wsgi
import tornado.websocket
from handlers import ShellHandler, IOPubHandler

ioloop.install()
wsgi_app = tornado.wsgi.WSGIContainer(app)
_kernel_id_regex = r"(?P<kernel_id>\w+-\w+-\w+-\w+-\w+)"


#Web Server
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
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print "\nEnding processes."
        application.km.shutdown()
