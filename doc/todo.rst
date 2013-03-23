The next phase
==============

Scaling
-------
* rate limiting for incoming computations and permalink requests, both total and by IP

  * HAProxy (upgrade to 1.5dev): http://blog.serverfault.com/2010/08/26/1016491873/ or http://blog.exceliance.fr/2012/02/27/use-a-load-balancer-as-a-first-row-of-defense-against-ddos/ or https://code.google.com/p/haproxy-docs/wiki/rate_limit_sessions
  * iptables: http://www.debian-administration.org/articles/187 or http://penguinsecurity.net/wiki/index.php?title=The_iptables_Rate-Limiting_Module (for example)
* load testing (ab, httperf, jmeter, our own multimechanize solution)
* Set up nginx to serve static assets


Security
--------
* Implement untrusted account restrictions:

  * explore SELinux or some other solution for untrusted users:
    http://docs.fedoraproject.org/en-US/Fedora/13/html/Security-Enhanced_Linux/sect-Security-Enhanced_Linux-Targeted_Policy-Confined_and_Unconfined_Users.html,
    http://selinux-mac.blogspot.com/2009/06/selinux-lockdown-part-four-customized.html,
    http://www.gentoo.org/proj/en/hardened/selinux/selinux-handbook.xml, http://debian-handbook.info/browse/wheezy/sect.selinux.html
  * have a pool of user accounts to execute code in.  Have the forking kernel manager drop privileges when forking and switch users to an unused user account, then clean up any files by the user when the computation is done.
* Manage daemons without screen (using https://pypi.python.org/pypi/python-daemon/, maybe?  Or maybe http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/ ?  See also http://www.python.org/dev/peps/pep-3143/ ).

Codebase
--------
* implement cookie-based TOS agreement, activated on evaluating your first computation (necessary for hosting at UW)
* Change output model so that output of a request can be confined, and the browser knows where the output goes (instead of just trusting the python side to send an output id)
* pressing evaluate multiple times really fast hangs things.  When I press evaluate a second time, before a reply message comes back, something seems to be getting messed up.


Permalink database
------------------
* Either implement database mirroring or use a server that does, deploy multiple permalink servers.  Possibilities for a database server include:

  * web side in Tornado, Go, or Node.js (for many simultaneous connections, but I suppose we could go back to flask/wsgi or something of that nature too)
  * database side in PostgreSQL (with propogation), Redis, Couchbase, Cassandra (Cassandra seems to fit the distributed, no-single-point-of-failure need)
  * Another possibility is to do the permalink server as a simple Google App Engine project.  William has lots of credit for this sort of thing.
* permalinks only requested when wanted (hide div, requested and shown when you click on permalink)
* logging of all requests (separate from permalinks): 

  * python logging facility (load-test this)
  * straight to append-only file
  * to database?

Lower priority
==============

Interacts
---------
* Set up dependency management on python side: control updates are sent immediately on variable assignment.  This also allows us to easily track which controls got updated so they update only once, if wanted
* explore javascript widgets
* explore using bootstrap to lay out widgets (see William's design)
* implement an html layout


Done
====
* Set up multiple servers talking to the same database (possibly distributed) over the web
