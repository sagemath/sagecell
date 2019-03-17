"""
Web Database Adapter
"""

import json
import urllib


import tornado.httpclient


import db


class DB(db.DB):
    """
    :arg URL str: the URL for the key-value store
    """

    def __init__(self, url):
        self.url = url

    def add(self, code, language, interacts, callback):
        """
        See :meth:`db.DB.add`
        """
        body = urllib.urlencode({
            "code": code.encode("utf8"),
            "language": language.encode("utf8"),
            "interacts": interacts.encode("utf8")})
            
        def cb(response):
            if response.code != 200:
                raise RuntimeError("Error in response")
            callback(json.loads(response.body)["query"])
            
        http_client = tornado.httpclient.AsyncHTTPClient()
        http_client.fetch(self.url, cb, method="POST", body=body,
                          headers={"Accept": "application/json"})

    def get(self, key, callback):
        """
        See :meth:`db.DB.get`
        """
        def cb(response):
            if response.code != 200:
                raise LookupError("Code lookup produced error")
            callback(*json.loads(response.body))

        http_client = tornado.httpclient.AsyncHTTPClient()
        http_client.fetch("{}?q={}".format(self.url, key), cb, method="GET",
                          headers={"Accept": "application/json"})
