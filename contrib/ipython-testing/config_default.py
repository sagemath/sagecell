# location of a sage executable
sage = "sage"

computers = []

for i in xrange(1):
    computers.append({"host": "localhost",
                      "username": None,
                      "python": sage + " -python",
# The keys to resource_limits can be any available resources
# for the resource module. See http://docs.python.org/library/resource.html
# for more information (section 35.13.1)
                      "resource_limits": {"RLIMIT_CPU": 10,
                                          "RLIMIT_NPROC": 500},
# The log file will be in the home directory of the untrusted account
                      "log_file": "sagecell.log"})
