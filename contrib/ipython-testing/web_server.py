
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    print "Root URL Loaded!"

    return """

<div>Loaded!</div>

"""


import tornado.web
import tornado.wsgi
import tornado.websocket
import tornado.ioloop

wsgi_app = tornado.wsgi.WSGIContainer(app)


class TestHandler(tornado.websocket.WebSocketHandler):
    def test(self):
        pass


class SageCellServer(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/tornado-url", TestHandler),
            (r".*", tornado.web.FallbackHandler, {'fallback': wsgi_app})
            ]

        super(SageCellServer, self).__init__(handlers)


if __name__ == "__main__":
    application = SageCellServer()
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
