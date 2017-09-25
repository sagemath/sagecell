#! /usr/bin/env python

import fcntl
import os
import signal
import socket
import struct

import psutil

from log import logger

import tornado.web
import zmq.eventloop
zmq.eventloop.ioloop.install()

import misc
import handlers
import permalink
from trusted_kernel_manager import TrustedMultiKernelManager


class SageCellServer(tornado.web.Application):
    def __init__(self, baseurl=""):
        # This matches a kernel id (uuid4 format) from a url
        _kernel_id_regex = r"(?P<kernel_id>\w+-\w+-\w+-\w+-\w+)"
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
            (r"/service", handlers.ServiceHandler),
            (r"/tos.html", handlers.TOSHandler),
            ] + handlers.KernelRouter.urls
        handlers_list = [[baseurl+i[0]]+list(i[1:]) for i in handlers_list]
        settings = dict(
            compress_response = True,
            template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
            static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
            static_url_prefix = baseurl+"/static/",
            static_handler_class = handlers.StaticHandler
            )
        self.km = TrustedMultiKernelManager(
            computers=self.config.get_config("computers"),
            tmp_dir=tmp_dir)
        db = __import__('db_'+self.config.get_config('db'))
        self.db = db.DB(self.config.get_config('db_config')['uri'])
        self.ioloop = zmq.eventloop.IOLoop.instance()

        # to check for blocking when debugging, uncomment the following
        # and set the argument to the blocking timeout in seconds
        self.ioloop.set_blocking_log_threshold(.5)
        self.completer = handlers.Completer(self.km)
        super(SageCellServer, self).__init__(handlers_list, **settings)


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
        
    pidlock.acquire(timeout=10)
    # TODO: clean out the router-ipc directory
    application = SageCellServer(baseurl=args.baseurl)
    listen = {'port': args.port, 'xheaders': True}
    if args.interface is not None:
        listen['address'] = get_ip_address(args.interface)
    logger.info("Listening configuration: %s", listen)

    def handler(signum, frame):
        logger.info("Received %s, shutting down...", signum)
        application.km.shutdown()
        application.ioloop.stop()
    
    signal.signal(signal.SIGHUP, handler)
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    application.listen(**listen)
    logger.warning('START')
    try:
        from systemd.daemon import notify
        logger.debug('notifying systemd that we are ready')
        notify('READY=1\nMAINPID={}'.format(os.getpid()), True)
    except ImportError:
        pass
    application.ioloop.start()
    logger.warning('SHUTDOWN')
    pidlock.release()
