import os.path

from config_default import sage

# Global database running on Google Compute Engine with a static IP
db = "web"
db_config = {"uri": "http://130.211.113.153"}

requires_tos = False

max_kernel_timeout = 60*90 # 90 minutes, for interacts
pid_file='/home/{server}/sagecell.pid'

computers = []
_default_config = {"host": "localhost",
                  "username": "{worker}",
                  "python": sage + " -python",
                  "location": os.path.dirname(os.path.abspath(__file__)),
# The keys to resource_limits can be any available resources
# for the resource module. See http://docs.python.org/library/resource.html
# for more information (section 35.13.1)

# Note: RLIMIT_NPROC doesn't really work
# Note: RLIMIT_AS is more of a suggestion than a hard limit in Mac OS X
# Note: All other resource limits seem to be working, but besides RLIMIT_CPU and
# RLIMIT_AS they don't actually kill off offending processes
                  "resource_limits": {"RLIMIT_CPU": 120, # CPU time in seconds
                                     },
                  "max_kernels": 30,
                  "preforked_kernels": 5,
# These set paramaters for a heartbeat channel checking whether a given kernel is alive.
# Setting first_beat lower than 1.0 may cause javascript errors.
                  "beat_interval": 0.5,
                  "first_beat": 1.0}

for i in range(4):
    computers.append(_default_config)
