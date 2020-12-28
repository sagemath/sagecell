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

    async def post(self):
        def encode(s):
            return base64.urlsafe_b64encode(
                zlib.compress(s.encode("utf8"))).decode("utf8")
            
        args = self.request.arguments
        logger.debug("Storing permalink %s", args)
        code = self.get_argument("code")
        language = self.get_argument("language", "sage")
        interacts = self.get_argument("interacts", "[]")
        retval = {}
        retval["zip"] = encode(code)
        retval["query"] = await self.application.db.add(
            code, language, interacts)
        retval["interacts"] = encode(interacts)
        if "n" in args:
            retval["n"] = int(self.get_argument("n"))
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

    async def get(self):
        q = self.get_argument("q")
        try:
            logger.debug("Looking up permalink %s", q)
            response = await self.application.db.get(q)
        except LookupError:
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
