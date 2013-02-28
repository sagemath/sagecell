import tornado.httpserver
import tornado.ioloop
import tornado.web
import misc
from db_sqlalchemy import DB
import json
import hashlib
import tornado.gen as gen


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
    @tornado.web.asynchronous
    @gen.engine
    def post(self):
        args = self.request.arguments
        retval = {"query": None}
        print args
        if "code" in args:
            code = ("".join(args["code"])).encode('utf8')
            language = "".join(args.get("language", ["sage"]))
        else:
            self.write_error(400)
        query = yield gen.Task(self.application.db.new_exec_msg, code, language)

        if self.request.headers["Accept"] == "application/json":
            self.set_header("Access-Control-Allow-Origin", "*");
        else:
            query = '<script>parent.postMessage(%s,"*");</script>' % (json.dumps(query),)
            self.set_header("Content-Type", "text/html")
        self.write(query)
        self.finish()

    @tornado.web.asynchronous
    @gen.engine
    def get(self):
        print self.request.__dict__
        q = "".join(self.request.arguments["q"])
        response = yield gen.Task(self.application.db.get_exec_msg, q)
        if self.request.headers["Accept"] == "application/json":
            self.set_header("Access-Control-Allow-Origin", "*");
        else:
            retval = '<script>parent.postMessage(%s,"*");</script>' % (json.dumps(response),)
            self.set_header("Content-Type", "text/html")
        print "PERMALINK RESPONSE", response[0]
        self.write(json.dumps(response[0]))
        self.finish()

class PermalinkServer(tornado.web.Application):
    def __init__(self):
        handlers_list = [
            (r"/", PermalinkHandler),
            ]
        self.config = misc.Config()
        self.db = DB("sqlite:///sqlite.db")

        #self.ioloop = ioloop.IOLoop.instance()
        # to check for blocking when debugging, uncomment the following
        # and set the argument to the blocking timeout in seconds 
        #self.ioloop.set_blocking_log_threshold(.5)

        super(PermalinkServer, self).__init__(handlers_list)




if __name__ == "__main__":
    import tornado.options
    from tornado.options import define, options

    define("port", default=8889, help="run on the given port", type=int)
    tornado.options.parse_command_line()
    application = PermalinkServer()
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
