#! /usr/bin/env python

"""
System imports
"""
import os

"""
Sagecell imports
"""
import misc

from trusted_kernel_manager import TrustedMultiKernelManager as TMKM
from db_sqlalchemy import DB
    

"""
Tornado / zmq imports
"""
import zmq
from zmq.eventloop import ioloop
ioloop.install()

import tornado.web

"""
Globals
"""
# This matches a kernel id (uuid4 format) from a url
_kernel_id_regex = r"(?P<kernel_id>\w+-\w+-\w+-\w+-\w+)"

"""
Tornado Handlers
"""
from handlers import ShellWebHandler, IOPubWebHandler, RootHandler, KernelHandler, PermalinkHandler, ServiceHandler

"""
Tornado Web Server
"""
class SageCellServer(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", RootHandler),
            (r"/kernel", KernelHandler),
            (r"/kernel/%s/iopub" % _kernel_id_regex, IOPubWebHandler),
            (r"/kernel/%s/shell" % _kernel_id_regex, ShellWebHandler),
            (r"/permalink", PermalinkHandler),
            (r"/service", ServiceHandler),
            ]

        settings = dict(
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            )

        self.config = misc.Config()

        initial_comps = self.config.get_config("computers")
        default_comp = self.config.get_default_config("_default_config")
        kernel_timeout = self.config.get_config("max_kernel_timeout")

        self.km = TMKM(computers = initial_comps, default_computer_config = default_comp, kernel_timeout = kernel_timeout)
        self.db = DB(misc.get_db_file(self.config))
        self.ioloop = ioloop.IOLoop.instance()

        super(SageCellServer, self).__init__(handlers, **settings)

if __name__ == "__main__":
    application = SageCellServer()
    application.listen(8888)
    try:
        application.ioloop.start()
    except KeyboardInterrupt:
        print "\nEnding processes."
        application.km.shutdown()
