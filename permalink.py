"""
Permalink web server

This Tornado server provides a permalink service with a convenient
post/get api for storing and retrieving code.
"""

import base64
import json
import zlib

import tornado

from log import permalink_logger as logger


class PermalinkHandler(tornado.web.RequestHandler):
    """
    Permalink generation request handler.

    This accepts the code and language strings and stores
    these in the permalink database.  A zip and query string are returned.

    The specified id can be used to generate permalinks
    with the format ``<root_url>?q=<id>``.
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def post(self):
        args = self.request.arguments
        logger.debug("Storing permalink %s", args)
        if "code" not in args:
            self.send_error(400)
            return
        code = "".join(args["code"])
        language = "".join(args.get("language", ["sage"]))
        interacts = "".join(args.get("interacts", ["[]"]))
        retval = {}
        retval["zip"] = base64.urlsafe_b64encode(zlib.compress(code))
        retval["query"] = yield tornado.gen.Task(
            self.application.db.add, code, language, interacts)
        if "interacts" in args:
            retval["interacts"] = base64.urlsafe_b64encode(
                zlib.compress(interacts))
        if "n" in args:
            retval["n"] = int("".join(args["n"]))
        if "frame" in args:
            retval = ('<script>parent.postMessage(%r,"*");</script>'
                      % json.dumps(retval))
            self.set_header("Content-Type", "text/html")
        else:
            self.set_header("Access-Control-Allow-Origin",
                            self.request.headers.get("Origin", "*"))
            self.set_header("Access-Control-Allow-Credentials", "true")
        self.write(retval)
        self.finish()

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        try:
            q = "".join(self.request.arguments["q"])
            logger.debug("Looking up permalink %s", q)
            response = (yield tornado.gen.Task(self.application.db.get, q))[0]
        except (LookupError, KeyError):
            logger.warning("ID not found in permalink database %s", q)
            self.set_status(404)
            self.finish("ID not found in permalink database")
            return
        response = json.dumps(response)
        if self.get_arguments("callback"):
            self.write("%s(%r);" % (self.get_argument("callback"), response))
            self.set_header("Content-Type", "application/javascript")
        else:
            self.write(response)
            self.set_header("Access-Control-Allow-Origin",
                            self.request.headers.get("Origin", "*"))
            self.set_header("Access-Control-Allow-Credentials", "true")
            self.set_header("Content-Type", "application/json")
        self.finish()
