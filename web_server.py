#! /usr/bin/env python

# System imports
import os

from hashlib import sha1
# Sage Cell imports
import misc

from trusted_kernel_manager import TrustedMultiKernelManager as TMKM
from db_sqlalchemy import DB

import logging
logging.basicConfig(format='%(asctime)s %(name)s:%(levelname)s %(message)s',level=logging.INFO)

logger = logging.getLogger('sagecell')

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
            (r"/about.html", handlers.AboutHandler),
            (r"/kernel", handlers.KernelHandler),
            (r"/embedded_sagecell.js", tornado.web.RedirectHandler, {"url":"/static/embedded_sagecell.js"}),
            (r"/sagecell.html", handlers.SageCellHandler),
            (r"/kernel/%s/iopub" % _kernel_id_regex, handlers.IOPubWebHandler),
            (r"/kernel/%s/shell" % _kernel_id_regex, handlers.ShellWebHandler),
            (r"/kernel/%s/files/(?P<file_path>.*)" % _kernel_id_regex, handlers.FileHandler, {"path": "/tmp/sagecell/"}),
            (r"/permalink", handlers.PermalinkHandler),
            (r"/service", handlers.ServiceHandler),
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

        self.km = TMKM(computers=initial_comps, default_computer_config=default_comp,
                       kernel_timeout=kernel_timeout)
        self.db = DB(misc.get_db_file(self.config))
        self.ioloop = ioloop.IOLoop.instance()

        # to check for blocking when debugging, uncomment the following
        # and set the argument to the blocking timeout in seconds 
        self.ioloop.set_blocking_log_threshold(.5)

        super(SageCellServer, self).__init__(handlers_list, **settings)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Launch a SageCell web server',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-p', '--port', type=int, default=8888,
                        help='port to launch the server')
    parser.add_argument('-d', '--debug', action='store_true', help='debug messages')
    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    logger.info("starting tornado web server")
    application = SageCellServer()
    application.listen(args.port)
    try:
        application.ioloop.start()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, so I'm shutting down.")
        try:
            application.km.shutdown()
        except KeyboardInterrupt:
            logging.info("Received another KeyboardInterrupt while shutting down, so I'm giving up.  You'll have to clean up anything left over.")
