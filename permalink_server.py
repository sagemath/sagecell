"""
Permalink web server

This Tornado server provides a permalink service with a convenient
post/get api for storing and retrieving code.
"""

import os

import psutil
import tornado.httpserver
import tornado.ioloop
import tornado.web

from log import logger
import permalink


PERMALINK_DB = "sqlalchemy"
PERMALINK_URI = "sqlite:///permalinks.db"
PERMALINK_PID_FILE = "permalink.pid"


class PermalinkServer(tornado.web.Application):
    def __init__(self):
        handlers_list = [
            (r"/", permalink.PermalinkHandler),
            (r"/permalink", permalink.PermalinkHandler),
            ]
        db = __import__('db_' + PERMALINK_DB)
        self.db = db.DB(PERMALINK_URI)

        #self.ioloop = ioloop.IOLoop.instance()
        # to check for blocking when debugging, uncomment the following
        # and set the argument to the blocking timeout in seconds 
        #self.ioloop.set_blocking_log_threshold(.5)

        super(PermalinkServer, self).__init__(handlers_list)

if __name__ == "__main__":
    import tornado.options
    from tornado.options import define, options

    define("port", default=8080, help="run on the given port", type=int)
    tornado.options.parse_command_line()

    from lockfile.pidlockfile import PIDLockFile
    pidfile_path = PERMALINK_PID_FILE
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
                        logger.error("The process seems to be the same, but "
                                     "can not be stopped. Its command line: %s"
                                     % old.cmdline())
                else:
                    logger.info("Process does not seem to be the same.")
            except psutil.NoSuchProcess:
                pass
                logger.info("No such process exist anymore.")
        logger.info("Breaking old lock.")
        pidlock.break_lock()
    try:
        pidlock.acquire(timeout=10)
        application = PermalinkServer()
        http_server = tornado.httpserver.HTTPServer(application, xheaders=True)
        http_server.listen(options.port)
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, so I'm shutting down.")
    finally:
        pidlock.release()
        logger.warning('Permalink server shutdown')
