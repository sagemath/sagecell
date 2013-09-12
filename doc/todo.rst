The next phase
==============

Security
--------
* Implement untrusted account restrictions for workers.  We can start
  by making workers derive from the unconfined_t role in CentOS.
  * explore SELinux or some other solution for untrusted users (like LXC):
    * http://magazine.redhat.com/2008/04/17/fedora-9-and-summit-preview-confining-the-user-with-selinux/
    * http://fedoraproject.org/wiki/SELinux
    * http://docs.fedoraproject.org/en-US/Fedora/18/html/Security_Guide/index.html
    * http://docs.fedoraproject.org/en-US/Fedora/13/html/Security-Enhanced_Linux/sect-Security-Enhanced_Linux-Targeted_Policy-Confined_and_Unconfined_Users.html
    * http://selinux-mac.blogspot.com/2009/06/selinux-lockdown-part-four-customized.html
    * http://www.gentoo.org/proj/en/hardened/selinux/selinux-handbook.xml
    * http://debian-handbook.info/browse/wheezy/sect.selinux.html
  * see also Linux containers: http://www.docker.io/, http://pyvideo.org/video/1852/the-future-of-linux-containers.  see also http://www.ibm.com/developerworks/linux/library/l-lxc-security/
  * Here's another crazy idea for managing diskspace: per-process filesystem namespaces (like http://glandium.org/blog/?p=217) along with copy-on-write unionfs mounts.  When a sage process is done, just throw away the unionfs mount, and poof, everything is gone.  See also http://www.ibm.com/developerworks/linux/library/l-mount-namespaces/index.html or http://blog.endpoint.com/2012/01/linux-unshare-m-for-per-process-private.html and the bottom of http://linux.die.net/man/2/mount
  * Make ssh more secure: http://wiki.centos.org/HowTos/Network/SecuringSSH
  * Polyinstantiated directories: https://access.redhat.com/site/documentation/en-US/Red_Hat_Enterprise_Linux/6/html/Security-Enhanced_Linux/polyinstantiated-directories.html
  * rate limiting for incoming computations and permalink requests, both total and by IP.  This may involve upgrading HAProxy to 1.5dev: http://blog.serverfault.com/2010/08/26/1016491873/ or http://blog.exceliance.fr/2012/02/27/use-a-load-balancer-as-a-first-row-of-defense-against-ddos/ or https://code.google.com/p/haproxy-docs/wiki/rate_limit_sessions
* Have a pool of user accounts to execute code in.  Have the forking kernel manager drop privileges when forking and switch users to an unused user account, then clean up any files by the user when the computation is done. (see https://github.com/sagemath/sagecell/issues/233)
* Get tinc working for a private network between database and servers.


Permalink database
------------------
* Benchmark the current permalink server.  Possibly implement a distributed permalink database server.  Right now we use a
tornado/sqlite server.
* Make sure the permalink server restarts if it goes down

Reliability and Scalability
---------------------------

* Test taking down a server.  Do clients automatically redirect to other servers from HAProxy noticing it is down?
* Benchmark a test setup identical to production setup for throughput of computations
* Automatically expire and restart idle workers.  See https://github.com/sagemath/sagecell/issues/391

Interacts
---------
* look into putting output in iframe to avoid all of the styling
  issues we've dealt with
* interactive 2d plots using Matplotlib's new tools
* Implement submit button for matrix control
* Diagnose the error in this interact: http://localhost:8888/?z=eJyNlVtr2zAUx98L_Q4iL5ZS1bPdlkHBY9Ax-hTG6FsIQbHlVKssGUlZkn76HUlxLk4bpgfZupyLf-cvWbSdNg6pVdttEbNIdej6quYNWgg177Tczo3WzuJJyzaoRHkGjRqm3mBQ3Pu3unwxK04er68QNCYlrDwx47gVTP0yul5VDo_dqpMcT6e3Oc1nszH2Lm5yQkg0m5RgmFbM1EIxKdwW7xZEg0Lob5NdgLAbZspJHL9zwyCi6lLedmAXMh1794TWbtvxEpYq3UL4zc5n7BttkKKwskBCIQ4EwJPjGBIhR7EgAYXKMsQ8mvZtYTh7O9npcQw2BYaV5k1jPbIxZON36TY8hHI4owW14p2Xeyi3-cEHl5ZfdOm_4LDucUxV-P5HrMBZeJ3BPo_IW-Y1PnJAUhONDXcroyLOwOg75AaDykU9zLHy1KdeAfTBd1ELRdZP7GayWdBHaaWoucE5vYMFCi7YSrqyuCc93c5ABJQ8MVmtJHNCLVHQGkXCobUAITn2xhHrOqM3aUJ9_C8QiCaWV1rVNjnx86Idk17IC26QbgIlpVvBpH1MaDHea46i0ZofBYjlkNtRiBB9_nYe7QdnoPR7Dgdgp6hOOhh22pcTvYsO-ypzJjH4IRQGomXLMCCx1Dk60eKe9W58AF70HHve0O9hZuRYqaeaDbZlNpROYDX6Ydh6z9vDigx6ZgHaaGApXWpf9Ro3Yhk-4YFcFul5dRthLEwFzAVNLhbbkwz7fMXJsOR9A6LFhToVw5vqJ3wXJ_-HRBvAzusTJuk5lOLTwhcnlS_2pYc7R2pTJuA8QbTHeT9IC4PvG--ffI59KJteOjVXFu7QeSe1wwDHltOM3kftFP6A_vWEcJbewRTN0vxER0cqCrZnIhqQsxz-H1rBzaGDAXIaWQ617PMIAvNYR-d-PlBO354p2vB6yUEj2_BE8Z5_FdbppWFtUX9-zmhIHfu6-DdC92_ES2HJS_8vSr9SBN2MoqPBjCptWr77r32cW8ucEZsIGMJKvcTPhFYt68rkD3dJJOw7eihcLCT5B72dHfI=&lang=sage (Click on 100 bins.  I get: "/Users/grout/projects/sagenb/sagecell/receiver.py:43: RuntimeWarning: divide by zero encountered in log self.dealer.send(source, zmq.SNDMORE)" below the picture)

Frontend
--------
* Extend codemirror's multiplexing mode addon to handle the string
  decorators (including end delimiter syntax, which probably involves
  extending the mode to have strings from the opening regex
  substituted into the closing string)
* Change output model so that output of a request can be confined, and
  the browser knows where the output goes (instead of just trusting
  the python side to send an output id).  This would help with displaying errors, for example. (see https://github.com/sagemath/sagecell/issues/387)


Summer 2013
===========
* [X] new interacts, maybe based on William's system
* [X] string decorators
* [X] (they are in my github branch, anyway) get sagecell patches into Sage
* Configure and deploy CentOS images using SELinux, a cloud database,
  and nginx for static assets.  Kernels should be tied to different
  users.  Rate limits and request logging should be in place.  All
  things should be proper daemons with appropriate watchdog processes.
  * Virtual image
    [X] sagecell server
    [X] sage worker account and ssh setup
    [X] tar up sage install so installing it doesn't involve recompiling
    [X] Make temporary directory writable by both the worker and the server (maybe just group-writeable)
    [X] sage cell config
    [X] Figure out permissions so that sageworker can execute sage
    [X] Set up http port forward
    [X] snapshots so I don't have to reinstall every single time.  Figure out how to make an image that is based on a single base image
    [X] Figure out appropriate firewall rules (lokkit --disabled to disable firewall)
    [X] permanent and temporary disks for database and tmp (leave tmp
        alone, just mount permanent disk)
    [X] diagnose and fix network problem when cloning:
        http://adam.younglogic.com/2010/06/eth0-not-present-after-libvirt-clone/,
        http://crashmag.net/correcting-the-eth0-mac-address-in-rhel-or-centos,
        https://bugzilla.redhat.com/show_bug.cgi?id=756130,
        We now delete the hardcoded mac address, and then delete the automatic generation of the eth0 rules.
    [X] quotas
    [X] immutable .ssh, .sage, etc. for sage worker
    [X] clean tmp directory (added cron script using tmpwatch)
    [X] use systemd or some other service to keep the cell server up
        - Final solution: use systemd and a cron script that checks
          every 2 minutes to make sure the website is still up.  This
          is way less complicated than monit, at the cost of a
          possible 2-minute downtime for a server.  If the server
          crashes, it is immediately restarted.  We could make the
          polling interval smaller.
    [X] Nginx -- installed and haproxy points to it
    [X] (right now, the sqlite solution works great as a separate
          permalink server.  Re-evaluate after benchmarking.  Figure out better(?) database solution.
        - benchmark the current tornado/sqlite permalink server solution.
        - estimate the load we expect
        - examine postgresql, couchbase, and cassandra for backend
        - examine node, go, tornado for front end
        - build centos-derived shadow vm for db server, probably
          separate from sagecell exec servers
    [X] Add google analytics code to the sage cell root page 
    [X] Better logging: log for web *and* service: where computations are coming from,
          compute code
        - log to permalink server (requests made from server, so
          should be fast; this means that logs are stored offsite from the untrusted images)
          we could also just use a remote logging service; centos comes with nice logging: http://www.server-world.info/en/note?os=CentOS_6&p=rsyslog, http://blog.secaserver.com/2013/01/centos-6-install-remote-logging-server-rsyslog/ (log with python logging module: http://stackoverflow.com/questions/3968669/how-to-configure-logging-to-syslog-in-python), http://help.papertrailapp.com/kb/configuration/configuring-centralized-logging-from-python-apps
        - make logging address configurable from the config file?
        - log:
           - where computations are coming from (embedding page URL or
             requesting IP address if /service)
           - type of computation (/service or normal evaluate; should
             we also track interact changes?)
           - date/time
           - kernel id (this will track separate computations)
           - code executed
    [X] Set up centos servers on combinat
    [X] Set up test servers


