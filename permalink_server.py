"""
Permalink web server

This Tornado server provides a permalink service with a convenient
post/get api for storing and retrieving code.
"""

import os
import signal

import psutil
import tornado.httpserver
import tornado.ioloop
import tornado.web

import permalink
from log import permalink_logger as logger


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
    import argparse
    parser = argparse.ArgumentParser(
        description='Launch a permalink database web server',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-p', '--port', type=int, default=8080,
                        help='port to launch the server')
    args = parser.parse_args()

    from lockfile.pidlockfile import PIDLockFile
    pidfile_path = PERMALINK_PID_FILE
    pidlock = PIDLockFile(pidfile_path)
    if pidlock.is_locked():
        old_pid = pidlock.read_pid()
        if os.getpid() != old_pid:
            try:
                old = psutil.Process(old_pid)
                if os.path.basename(__file__) in old.cmdline():
                    try:
                        old.terminate()
                        try:
                            old.wait(10)
                        except psutil.TimeoutExpired:
                            old.kill()
                    except psutil.AccessDenied:
                        pass
            except psutil.NoSuchProcess:
                pass
        pidlock.break_lock()
        
    pidlock.acquire(timeout=10)
    app = PermalinkServer()
    app.listen(port=args.port, xheaders=True)

    def handler(signum, frame):
        logger.info("Received %s, shutting down...", signum)
        ioloop = tornado.ioloop.IOLoop.current()
        ioloop.add_callback_from_signal(ioloop.stop)
    
    signal.signal(signal.SIGHUP, handler)
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    try:
        from systemd.daemon import notify
        notify('READY=1\nMAINPID={}'.format(os.getpid()), True)
    except ImportError:
        pass
        
    tornado.ioloop.IOLoop.current().start()
    pidlock.release()
