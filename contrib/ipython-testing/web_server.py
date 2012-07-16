#! /usr/bin/env python

# System imports
import os

from hashlib import sha1
# Sage Cell imports
import misc

from trusted_kernel_manager import TrustedMultiKernelManager as TMKM
from db_sqlalchemy import DB

# Tornado / zmq imports
import zmq
from zmq.eventloop import ioloop
import tornado.web

ioloop.install()

# Globals
# This matches a kernel id (uuid4 format) from a url
_kernel_id_regex = r"(?P<kernel_id>\w+-\w+-\w+-\w+-\w+)"

# Tornado Web Server
import handlers

class SageCellServer(tornado.web.Application):
    def __init__(self):
        handlers_list = [
            (r"/", handlers.RootHandler),
            (r"/kernel", handlers.KernelHandler),
            (r"/embedded_sagecell.js", handlers.EmbeddedHandler),
            (r"/sagecell.html", handlers.SageCellHandler),
            (r"/kernel/%s/iopub" % _kernel_id_regex, handlers.IOPubWebHandler),
            (r"/kernel/%s/shell" % _kernel_id_regex, handlers.ShellWebHandler),
            (r"/permalink", handlers.PermalinkHandler),
            # (r"/service", handlers.ServiceHandler),
            ] + handlers.KernelRouter.urls
        settings = dict(
            template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
            static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
            static_handler_class = handlers.StaticHandler
            )
        self.config = misc.Config()

        initial_comps = self.config.get_config("computers")
        default_comp = self.config.get_default_config("_default_config")
        kernel_timeout = self.config.get_config("max_kernel_timeout")

        self.km = TMKM(computers=initial_comps, default_computer_config=default_comp, kernel_timeout=kernel_timeout)
        self.db = DB(misc.get_db_file(self.config))
        self.ioloop = ioloop.IOLoop.instance()

        super(SageCellServer, self).__init__(handlers_list, **settings)

if __name__ == "__main__":
    application = SageCellServer()
    application.listen(8888)
    try:
        application.ioloop.start()
    except KeyboardInterrupt:
        print "\nEnding processes."
        application.km.shutdown()
