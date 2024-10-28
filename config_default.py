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

dir = "/tmp/sagecell"

# Parameters for heartbeat channels checking whether a given kernel is alive.
# Setting first_beat lower than 1.0 may cause JavaScript errors.
beat_interval = 0.5
first_beat = 1.0

# Allowed idling between interactions with a kernel
max_timeout = 60 * 15
# Even an actively used kernel will be killed after this time
max_lifespan = 60 * 30

# Recommended settings for kernel providers
provider_settings = {
    "max_kernels": 10,
    "max_preforked": 1,
    # The keys to resource_limits can be any available resources
    # for the resource module. See http://docs.python.org/library/resource.html
    # for more information (section 35.13.1)
    # RLIMIT_AS is more of a suggestion than a hard limit in Mac OS X
    # Also, Sage may allocate huge AS, making this limit pointless:
    # https://groups.google.com/d/topic/sage-devel/1MM7UPcrW18/discussion
    "preforked_rlimits": {
        "RLIMIT_CPU": 30, # CPU time in seconds
        },
    }

# Location information for kernel providers
provider_info = {
    "host": "localhost",
    "username": None,
    "python": sage + " -python",
    "location": os.path.dirname(os.path.abspath(__file__))
    }

providers = [provider_info]
