"""
Permalink web server

This Tornado server provides a permalink service with a convenient
post/get api for storing and retrieving code.
"""

import tornado.web
import tornado.gen as gen
import json

class PermalinkHandler(tornado.web.RequestHandler):
    """
    Permalink generation request handler.

    This accepts the code and language strings and stores
    these in the permalink database.  A zip and query string are returned.

    The specified id can be used to generate permalinks
    with the format ``<root_url>?q=<id>``.
    """
    @tornado.web.asynchronous
    @gen.engine
    def post(self):
        args = self.request.arguments
        retval = {"query": None, "zip": None}
        if "code" in args:
            code = ("".join(args["code"]))
            language = "".join(args.get("language", ["sage"]))
        else:
            self.send_error(400)
            return

        import zlib, base64
        retval["zip"] = base64.urlsafe_b64encode(zlib.compress(code))
        retval["query"] = yield gen.Task(self.application.db.new_exec_msg, code.decode('utf8'), language)

        if "frame" not in args:
            self.set_header("Access-Control-Allow-Origin", "*");
        else:
            retval = '<script>parent.postMessage(%r,"*");</script>' % (json.dumps(retval),)
            self.set_header("Content-Type", "text/html")

        self.write(retval)
        self.finish()

    @tornado.web.asynchronous
    @gen.engine
    def get(self):
        q = "".join(self.request.arguments["q"])
        response = yield gen.Task(self.application.db.get_exec_msg, q)
        # response_json is [code, language]
        response_json = json.dumps(response[0])
        if len(self.get_arguments("callback")) == 0:
            self.write(response_json)
            self.set_header("Access-Control-Allow-Origin", "*")
            self.set_header("Content-Type", "application/json")
        else:
            self.write("%s(%r);" % (self.get_argument("callback"), response_json))
            self.set_header("Content-Type", "application/javascript")
        self.finish()
