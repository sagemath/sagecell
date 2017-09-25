import os.path


# Location of the Sage executable
if 'SAGE_ROOT' in os.environ:
    # Assume that the worker should run the same Sage
    # that is used to run the web server
    sage = os.path.join(os.environ["SAGE_ROOT"], "sage")
else:
    # Assume both the web server and the worker have Sage in their paths
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

pid_file = 'sagecell.pid'
permalink_pid_file = 'sagecell_permalink_server.pid'
tmp_dir = "/tmp/sagecell"

_default_config = {
    "host": "localhost",
    "username": None,
    "python": sage + " -python",
    "location": os.path.dirname(os.path.abspath(__file__)),
    # The keys to resource_limits can be any available resources
    # for the resource module. See http://docs.python.org/library/resource.html
    # for more information (section 35.13.1)
    # Note: RLIMIT_NPROC doesn't really work
    # Note: RLIMIT_AS is more of a suggestion than a hard limit in Mac OS X
    # Also, Sage may allocate huge AS, making this limit pointless:
    # https://groups.google.com/d/topic/sage-devel/1MM7UPcrW18/discussion
    # Note: All other resource limits seem to be working, but besides RLIMIT_CPU
    # and RLIMIT_AS they don't actually kill off offending processes
    "resource_limits": {
        "RLIMIT_CPU": 120, # CPU time in seconds
        },
    "max_lifespan" : 60 * 90, # From the session start
    "max_timeout" : 60 * 90, # Idling between interactions
    "max_kernels": 10,
    "preforked_kernels": 1,
    # These set parameters for a heartbeat channel checking whether a given
    # kernel is alive.
    # Setting first_beat lower than 1.0 may cause javascript errors.
    "beat_interval": 0.5,
    "first_beat": 1.0,
    }

computers = [_default_config]
