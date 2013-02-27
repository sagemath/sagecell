"""
SQLAlchemy Database Adapter
---------------------------
"""

"""
System library imports
"""
import json, uuid
from datetime import datetime
import string
import tornado
import tornado.httpclient
"""
Generic database adapter import
"""
import db
import urllib
valid_query_chars = set(string.letters+string.digits+"-")
from functools import partial

class DB(db.DB):
    """
    :arg URL str: the URL for the key-value store
    """

    def __init__(self, url):
        self.url = url

    def new_exec_msg(self, code, language, callback):
        """
        See :meth:`db.DB.new_exec_msg`
        """
        post_data = { 'code': code, 'language': language } #A dictionary of your post data
        body = urllib.urlencode(post_data) #Make it into a post request
        http_client = tornado.httpclient.AsyncHTTPClient()
        exec_callback = partial(self.return_exec_msg_id, callback)
        http_client.fetch(self.url, exec_callback, method="POST", body=body, headers={"Accept": "application/json"})

    def return_exec_msg_id(self, callback, response):
        # TODO: error handling
        print response.body
        callback(response.body)

    def get_exec_msg(self, key, callback):
        """
        See :meth:`db.DB.get_exec_msg`
        """
        print "URL", self.url
        http_client = tornado.httpclient.AsyncHTTPClient()
        exec_callback = partial(self.return_exec_msg_code, callback)
        http_client.fetch(self.url+"?q=%s"%key, exec_callback, method="GET", headers={"Accept": "application/json"})

    def return_exec_msg_code(self, callback, response):
        print "RESPONSE", response
        if response.code == 200:
            code, language = json.loads(response.body)
        else:
            raise LookupError("Code lookup produced error")
        print "GOT WEB CODE", (code, language)
        callback(code, language)
