#! /usr/bin/env python

import os

import psutil

# Sage Cell imports
from log import logger
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
            (r"/embedded_sagecell.js", tornado.web.RedirectHandler, {"url":baseurl+"/static/embedded_sagecell.js"}),
            (r"/help.html", handlers.HelpHandler),
            (r"/kernel", handlers.KernelHandler),
            (r"/kernel/%s" % _kernel_id_regex, handlers.KernelHandler),
            (r"/kernel/%s/channels" % _kernel_id_regex, handlers.WebChannelsHandler),
            (r"/kernel/%s/files/(?P<file_path>.*)" % _kernel_id_regex, handlers.FileHandler, {"path": tmp_dir}),
            (r"/permalink", permalink.PermalinkHandler),
            (r"/sagecell.html", handlers.SageCellHandler),
            (r"/service", handlers.ServiceHandler),
            (r"/tos.html", handlers.TOSHandler),
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
                       max_kernel_timeout=max_kernel_timeout, tmp_dir=tmp_dir)
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
    parser.add_argument('-b', '--baseurl', default="", help="base url")
    parser.add_argument('--interface', default=None, help="interface to listen on (default all)")
    parser.add_argument('--tmp_dir', default=config.get_config("tmp_dir"), help="temporary directory for calculations")

    args = parser.parse_args()

    tmp_dir = args.tmp_dir

    logger.info("starting tornado web server")
    from lockfile.pidlockfile import PIDLockFile
    pidfile_path = config.get_config('pid_file')
    pidlock = PIDLockFile(pidfile_path)
    if pidlock.is_locked():
        old_pid = pidlock.read_pid()
        logger.info("Lock file exists for PID %d." % old_pid)
        if os.getpid() == old_pid:
            logger.info("Stale lock since we have the same PID.")
        else:
            try:
                old = psutil.Process(old_pid)
                if os.path.basename(__file__) in old.cmdline():
                    try:
                        logger.info("Trying to terminate old instance...")
                        old.terminate()
                        try:
                            old.wait(10)
                        except psutil.TimeoutExpired:
                            logger.info("Trying to kill old instance.")
                            old.kill()
                    except psutil.AccessDenied:
                        logger.error("The process seems to be SageCell, but "
                                     "can not be stopped. Its command line: %s"
                                     % old.cmdline())
                else:
                    logger.info("Process does not seem to be SageCell.")
            except psutil.NoSuchProcess:
                pass
                logger.info("No such process exist anymore.")
        logger.info("Breaking old lock.")
        pidlock.break_lock()
    try:
        pidlock.acquire(timeout=10)
        # TODO: clean out the router-ipc directory
        application = SageCellServer(baseurl=args.baseurl)
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
