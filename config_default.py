import os.path

# location of a sage executable
sage = ""

# defaults if sage isn't set above
if sage == "":
    if 'SAGE_ROOT' in os.environ:
        # assume that the untrusted worker should run the same copy of sage
        # that is used to run the web server
        sage = os.path.join(os.environ["SAGE_ROOT"],"sage")
    else:
        # assume both the web server and the untrusted workers have sage in their paths
        sage = "sage"
# Require the user to accept terms of service before evaluation
requires_tos = True

db = "sqlalchemy"
db_config = {"uri": "sqlite:///sqlite.db"}

# db = "web"
# db_config = {"uri": "http://localhost:8889"}

permalink_server = {
    'db': 'sqlalchemy',
    'db_config': {'uri': 'sqlite:///sqlite.db'}
}

max_kernel_timeout = 60*10 # 10 minutes, for interacts
pid_file = 'sagecell.pid'
computers = []

_default_config = {"host": "localhost",
                  "username": None,
                  "python": sage + " -python",
                  "location": os.path.dirname(os.path.abspath(__file__)),
# The keys to resource_limits can be any available resources
# for the resource module. See http://docs.python.org/library/resource.html
# for more information (section 35.13.1)

# Note: RLIMIT_NPROC doesn't really work
# Note: RLIMIT_AS is more of a suggestion than a hard limit in Mac OS X
# Note: All other resource limits seem to be working, but besides RLIMIT_CPU and
# RLIMIT_AS they don't actually kill off offending processes
                  "resource_limits": {"RLIMIT_CPU": 30, # CPU time in seconds
                                      "RLIMIT_AS": 1024*(2**20), #Maximum address space in bytes; this sets 1024 MB
                                     },
# The log file will be in the home directory of the untrusted account
                  "log_file": "sagecell.log",
                  "max_kernels": 10,
                  "preforked_kernels": 5,
# These set paramaters for a heartbeat channel checking whether a given kernel is alive.
# Setting first_beat lower than 1.0 may cause javascript errors.
                  "beat_interval": 0.5,
                  "first_beat": 1.0}

for i in xrange(1):
    computers.append(_default_config)
