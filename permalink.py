"""
Permalink web server

This Tornado server provides a permalink service with a convenient
post/get api for storing and retrieving code.
"""

import tornado.httpserver
import tornado.ioloop
import tornado.web
import misc
import json
import tornado.gen as gen


class PermalinkHandler(tornado.web.RequestHandler):
    """
    Permalink generation request handler.
    """
    @tornado.web.asynchronous
    @gen.engine
    def post(self):
        args = self.request.arguments
        retval = {"query": None}
        if "code" in args:
            code = ("".join(args["code"])).encode('utf8')
            language = "".join(args.get("language", ["sage"]))
        else:
            self.write_error(400)
        query = yield gen.Task(self.application.db.new_exec_msg, code, language)

        if "frame" not in self.request.headers:
            self.set_header("Access-Control-Allow-Origin", "*");
        else:
            retval = '<script>parent.postMessage(%s,"*");</script>' % (json.dumps(retval),)
            self.set_header("Content-Type", "text/html")

        self.write(query)
        self.finish()

    @tornado.web.asynchronous
    @gen.engine
    def get(self):
        q = "".join(self.request.arguments["q"])
        response = yield gen.Task(self.application.db.get_exec_msg, q)
        if "frame" not in self.request.headers:
            self.set_header("Access-Control-Allow-Origin", "*");
        else:
            retval = '<script>parent.postMessage(%s,"*");</script>' % (json.dumps(retval),)
            self.set_header("Content-Type", "text/html")

        self.write(json.dumps(response[0]))
        self.finish()

class PermalinkServer(tornado.web.Application):
    def __init__(self):
        handlers_list = [
            (r"/", PermalinkHandler),
            ]
        self.config = misc.Config()
        db = __import__('db_'+self.config.get_config('permalink_server')['db'])
        self.db = db.DB(self.config.get_config('permalink_server')['db_config']['uri'])

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
