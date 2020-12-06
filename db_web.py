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

    async def add(self, code, language, interacts):
        """
        See :meth:`db.DB.add`
        """
        body = urllib.parse.urlencode({
            "code": code.encode("utf8"),
            "language": language.encode("utf8"),
            "interacts": interacts.encode("utf8")})
        http_client = tornado.httpclient.AsyncHTTPClient()
        response = await http_client.fetch(
            self.url, method="POST", body=body,
            headers={"Accept": "application/json"})
        return json.loads(response.body)["query"]

    async def get(self, key):
        """
        See :meth:`db.DB.get`
        """
        http_client = tornado.httpclient.AsyncHTTPClient()
        response = await http_client.fetch(
            "{}?q={}".format(self.url, key), method="GET",
            headers={"Accept": "application/json"})
        return json.loads(response.body)
