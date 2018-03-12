import json
import logging
from logging.handlers import SysLogHandler
import sys


LOG_LEVEL = logging.DEBUG
LOG_VERSION = 0


class StatsMessage(object):
    def __init__(self, kernel_id, code, execute_type, remote_ip, referer):
        self.msg = [LOG_VERSION, remote_ip, referer, execute_type, kernel_id, code]
    def __str__(self):
        return json.dumps(self.msg)


syslog = SysLogHandler(address="/dev/log", facility=SysLogHandler.LOG_LOCAL3)
syslog.setFormatter(logging.Formatter(
    "%(asctime)s %(process)5d %(name)-23s: %(message)s"))

# Default logger for SageCell
logger = logging.getLogger("sagecell")
stats_logger = logger.getChild("stats")
# Intermediate loggers to be parents for actual receivers and kernels.
receiver_logger = logger.getChild("receiver")
kernel_logger = logger.getChild("kernel")
provider_logger = logger.getChild("provider")

root = logging.getLogger()
root.addHandler(syslog)
root.setLevel(LOG_LEVEL)

class TornadoFilter(logging.Filter):
    """
    Drop HA-Proxy healthchecks.
    """
    def filter(self, record):
        return len(record.args) != 3 or \
            record.args[:2] != (200, 'OPTIONS / (10.0.3.1)')

logging.getLogger("tornado.access").addFilter(TornadoFilter())


class StdLog(object):
    """
    A file-like object for sending stdout/stderr to a log.
    """
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        
    def flush(self):
        pass
        
    def write(self, data):
        self.logger.log(self.level, data)
        
        
def std_redirect(logger):
    """
    Redirect stdout and stderr to the given logger.
    
    Also set their underscore versions to make IPython happier.
    """
    sys.__stdout__ = sys.stdout = StdLog(
        logger.getChild("stdout"), logging.DEBUG)
    sys.__stderr__ = sys.stderr = StdLog(
        logger.getChild("stderr"), logging.WARNING)
