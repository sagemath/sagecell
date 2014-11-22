#! /usr/bin/env python

import os
import logging
logger = logging.getLogger('sagecell')

# Sage Cell imports
import misc
from trusted_kernel_manager import TrustedMultiKernelManager as TMKM

# Tornado / zmq imports
from zmq.eventloop import ioloop
import tornado.web

ioloop.install()

# Globals
# This matches a kernel id (uuid4 format) from a url
_kernel_id_regex = r"(?P<kernel_id>\w+-\w+-\w+-\w+-\w+)"

# Tornado Web Server
import handlers
import permalink


class SageCellServer(tornado.web.Application):
    def __init__(self, baseurl=""):
        self.config = misc.Config()
        baseurl = baseurl.rstrip('/')
        handlers_list = [
            (r"/", handlers.RootHandler),
            (r"/kernel", handlers.KernelHandler),
            (r"/embedded_sagecell.js", tornado.web.RedirectHandler, {"url":baseurl+"/static/embedded_sagecell.js"}),
            (r"/sagecell.html", handlers.SageCellHandler),
            (r"/tos.html", handlers.TOSHandler),
            (r"/kernel/%s" % _kernel_id_regex, handlers.KernelHandler),
            (r"/kernel/%s/iopub" % _kernel_id_regex, handlers.IOPubWebHandler),
            (r"/kernel/%s/shell" % _kernel_id_regex, handlers.ShellWebHandler),
            (r"/kernel/%s/files/(?P<file_path>.*)" % _kernel_id_regex, handlers.FileHandler, {"path": tmp_dir}),
            (r"/permalink", permalink.PermalinkHandler),
            (r"/service", handlers.ServiceHandler),
            ] + handlers.KernelRouter.urls
        handlers_list = [[baseurl+i[0]]+list(i[1:]) for i in handlers_list]
        settings = dict(
            template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
            static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
            static_url_prefix = baseurl+"/static/",
            static_handler_class = handlers.StaticHandler
            )

        initial_comps = self.config.get_config("computers")
        default_comp = self.config.get_default_config("_default_config")
        max_kernel_timeout = self.config.get_config("max_kernel_timeout")
        self.km = TMKM(computers=initial_comps, default_computer_config=default_comp,
                       max_kernel_timeout=max_kernel_timeout, tmp_dir = tmp_dir)
        db = __import__('db_'+self.config.get_config('db'))
        self.db = db.DB(self.config.get_config('db_config')['uri'])
        self.ioloop = ioloop.IOLoop.instance()

        # to check for blocking when debugging, uncomment the following
        # and set the argument to the blocking timeout in seconds
        self.ioloop.set_blocking_log_threshold(.5)
        self.completer = handlers.Completer(self.km)
        super(SageCellServer, self).__init__(handlers_list, **settings)

import socket
import fcntl
import struct

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])


if __name__ == "__main__":
    config = misc.Config()

    import argparse
    parser = argparse.ArgumentParser(description='Launch a SageCell web server',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-p', '--port', type=int, default=8888,
                        help='port to launch the server')
    parser.add_argument('-d', '--debug', action='store_true', help='debug messages')
    parser.add_argument('-b', '--baseurl', default="", help="base url")
    parser.add_argument('--interface', default=None, help="interface to listen on (default all)")
    parser.add_argument('--tmp_dir', default=config.get_config("tmp_dir"), help="temporary directory for calculations")

    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("tornado.access").setLevel(logging.DEBUG)
        logging.getLogger("tornado.application").setLevel(logging.DEBUG)
        logging.getLogger("tornado.general").setLevel(logging.DEBUG)
        
    class TornadoFilter(logging.Filter):
        """
        Drop HA-Proxy healthchecks.
        """
        def filter(self, record):
            return len(record.args) != 3 or \
                record.args[:2] != (200, 'OPTIONS / (10.0.3.1)')
            
    logging.getLogger("tornado.access").addFilter(TornadoFilter())        

    tmp_dir = args.tmp_dir

    logger.info("starting tornado web server")
    from lockfile.pidlockfile import PIDLockFile
    pidfile_path = config.get_config('pid_file')
    pidlock = PIDLockFile(pidfile_path)
    if pidlock.is_locked():
        # try killing the process that has the lock
        pid = pidlock.read_pid()
        logger.info("Killing PID %d"%pid)
        try:
            os.kill(pid, 9)
        except OSError, (code, text):
            import errno
            if code != errno.ESRCH:
                raise
            else:
                # process doesn't exist anymore
                logger.info("Old process %d already gone"%pid)
                pidlock.break_lock()
    try:
        pidlock.acquire(timeout=10)
        # TODO: clean out the router-ipc directory
        application = SageCellServer(baseurl = args.baseurl)
        listen = {'port': args.port, 'xheaders': True}
        if args.interface is not None:
            listen['address']=get_ip_address(args.interface)
        logger.info("Listening configuration: %s"%(listen,))
        logger.warning('START')
        application.listen(**listen)
        application.ioloop.start()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, so I'm shutting down.")
        try:
            application.km.shutdown()
        except KeyboardInterrupt:
            logger.info("Received another KeyboardInterrupt while shutting down, so I'm giving up.  You'll have to clean up anything left over.")
    finally:
        pidlock.release()
        logger.warning('SHUTDOWN')
