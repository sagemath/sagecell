# pid.py - module to help manage PID files
import os
import logging
import fcntl
import errno
 
def check(path):
    # try to read the pid from the pidfile
    try:
        logging.info("Checking pidfile '%s'", path)
        pid = int(open(path).read().strip())
    except IOError, (code, text):
        pid = None
        # re-raise if the error wasn't "No such file or directory"
        if code != errno.ENOENT:
            raise
 
    # try to kill the process
    try:
        if pid is not None:
            logging.info("Killing PID %s", pid)
            os.kill(pid, 9)
    except OSError, (code, text):
        # re-raise if the error wasn't "No such process"
        if code != errno.ESRCH:
            raise
 
def write(path):
    try:
        pid = os.getpid()
        pidfile = open(path, 'wb')
        # get a non-blocking exclusive lock
        fcntl.flock(pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # clear out the file
        pidfile.seek(0)
        pidfile.truncate(0)
        # write the pid
        pidfile.write(str(pid))
        logging.info("Writing PID %s to '%s'", pid, path)
    except:
        raise
    finally:
        try:
            pidfile.close()
        except:
            pass
 
def remove(path):
    try:
        # make sure we delete our pidfile
        logging.info("Removing pidfile '%s'", path)
        os.unlink(path)
    except:
        pass
