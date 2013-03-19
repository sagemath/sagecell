The next phase
==============

* Set up multiple servers talking to the same database (possibly distributed) over the web
* Either implement database mirroring or use a server that does, deploy multiple permalink servers.  Possibilities for a database server include:
  * web side in Tornado, Go, or Node.js
  * database side in PostgreSQL (with propogation), Redis, Couchbase, Cassandra (Cassandra seems to fit the distributed, no-single-point-of-failure need)
  * Another possibility is to do the permalink server as a simple Google App Engine project.  William has lots of credit for this sort of thing.
* Change output model so that output of a request can be confined, and the browser knows where the output goes (instead of just trusting the python side to send an output id)
* explore javascript widgets
* explore using bootstrap to lay out widgets (see William's design)
* implement an html layout
* rate limiting for incoming computations and permalink requests
* permalinks only requested when wanted (hide div, requested and shown when you click on permalink)
* logging of all requests (separate from permalinks)
* explore SELinux or some other solution for untrusted users
* have a pool of user accounts to execute code in.  Have the untrusted account drop privileges and switch users to an unused user account
* pressing evaluate multiple times really fast hangs things.  When I press evaluate a second time, before a reply message comes back, something seems to be getting messed up.
* Set up dependency management on python side: control updates are sent immediately on variable assignment.  This also allows us to easily track which controls got updated so they update only once, if wanted

