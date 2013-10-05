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

* Implement IPython comm spec.  Here is a working example:
http://localhost:8888/?z=eJx1UsFq3DAQvRv8D1NTiARGSQ69bLJ7aEogUGghKTmEImRbXquRJSONk5pl_72S5XS3W2IQlmbevHnzJD95xr3YSs5-iRfha6cGJEVR5JlqyQfslGfP0hmpWW37nvfCBLBjKNxWon86Q-nx7CeFXZ69CAfYCVzHqqt0fgjpR9UELKyhHU2NyhogkWuugfDNTWIkQOLv6iTMrOG935KPbHD290TmRCdMo6UrZxil_9QIrStRP_vAt1N2GCtYwc6OOIwYdgcagQsNT8lylk_3-8AWV54d5McitDgN8q310UAkyPt_HOalacgOqtXlBezLE3H0b5N3TXZyqzxKx5PbJJldwt33CTtr2IhKeyb0q5g8N_KVHOTOjuzzLNwkzbPW2X62FlQ_WIdwH_hvpNY3IRYlLO4fh0lqyo3o5Tp1pgmY5mpUjUSslUHyidKQamQLizWzH6tkx-ACBDYb8PGpcY-NdI7zEgLmGHFyLCx2wWOPY9syxoqU67DXpLiuNp-_ff0C9w8_bm-vz6tNnHHRtryVRch7ii8vZsl59geYrfhK&lang=sage

http://localhost:8888/?z=eJzNWF-P4zQQf6_U72DCreLslWxX4l627QpxcOLeEBzwsKwib-O25lInsp1tq9V-d2ZsJ3HSdheEEFRqk47nn2d-M55kpcotWZbbLRHbqlSG_MzW_D0vivdIY5rgdTzyi3Ut8vFoPFqh1McfD2ZTyrQ2otCpUUyYghvdKPqB6U9I0xPyURq-5mpCfpFiWeZ8Qr4tywLp2jC5hP8fipKZgd5c6Kpgh0bfJRoej5YF05r8JvI1N7S1kdyMRwQ-himgZ5JtOVk05mi0s-xR4phEHqx5Ws5XJBN5BldWF4ZqXqwapfhR3NRKkthp-upCx-TChiPFn69pkm743rG7XxvTRbtFinEMbeH6WWs5MwyEkZzifX_lLhZ5fN-sY0YGXqItipyTMCALyx4QktDfbypVVlyZQ-cjajgXiKfnRtgl5Ccm19xnxV1eSYlCgSYjWyFhzYKATlVDZPuWeD1tyY-sqHm78K6la8Orjr-hZp_5QQP5LgYb8YTEoBUvVgveoFh875mFzDZM5gVXIIIYpR9YofuBstkDcQHh4RlwZ3WFtzZSE4L7nJCyyOGW78LIiZVLmNvArfsD7gQsNsBMaE5-RabvlSoVjZzARU74fsl5rm1kLvIIEEg7jZNWYZL0jIIbZO4Xhfzr1h54Ue5sas7aEjK01bdaGscUBHVg2y774B2HGOSEyTIf1svLzzsAkg4DqmsALA2Q59xK0la2lQqE0CgWX1rKbKvXblfOQfwfsH4JYF8LAIgiwGsbXLbcoDnCVkhFKyF7aTZc7TCgvrAdWDVZMhkbCCjRFV-KleD5wKGBfufUKZT5yFtY_6P6BQU3EDJmjPIhBkpCVqXCG9haYOh5mJwA8b2EtLHVXOa0bV_O0TC3ilfK5_aEc9HcJpXQi_R6lRD8vWl_bs9isasAf4e1fQSsLtV-35j04Sb6neCTqvlRcwaxu3hZwtEmTXx_FyO5aST4MeowwPvJ2A54fPV4NtR5gsG5OcjdxJ0NcHcfYHglJCuKoScn9mgbXRCFg4bw5WVt0p0SkOv4d-UOPZuzk4yrotabE5Vsk70x2-I44ZUS0vWJYxBE0TwXj8SeL4voQke38ysg3MKCd6M9-wLMu6Hh-EQN6YNkdy1oPMLtZBpmoCz9gz0yvVSiMhRM4uIjU-FBB1Fb1XJpRCkJRdg7LJEnf_BthE79GICXWTcYNL3nTQpVuz9Qy9oBc2Jlk2QWKoI0PrDlZzzMnoJOW1b1A7kJSfiBdFS1AfopC27RG-nkfJU_z3Crrd0z56c7NkMHu7JIfVVYUshiB6-WGf6GizgkQHop7tr5EIQad2FKc6h4w9cLfhtzzJBbfEMjuEkj8rax3YQTyoviUsHl2mzIYrEg0yQMoAegrIvCizz3JaGochoJCVGMkvN6XN4Uxw5uxx0UTvoqvS1YeGXboZ7e3uHMQbVhBBqmNzSeWy-hctw1TlLbNWLUiXm0rHHjlA2fy2ObpllYYtjCKHKJxXRGBMwVLUh8HID69m0vDMiO_WzR8d6JBjo2BuiD82vQxwaxsnzQ9O1s67p_0nPPxSJlVYXnT2cBwDDXFZNXt5AvlufvsafQCCAN_w3fG6cR5xknlBzrsNbPrp6zwPZ9CzCdvajjQaGGv2vGhqJnyAXH65mF8SsljdyUEU367cHK-AkkD3rQ83lU9kR6sOSPpodJCbPkws6i39lmGxQjLn3lwAHbMa26OYGxvwelqyuYxIqDnz8If-TqQKbpNTxjQmTHI1jvF3EfQF13OOo4w9I5KvPjCnl6nv2LRdEWAbBUTGnuHmz6tZIMKqRL_SkprJxWotsg4ik9VQpnOE9A-jTnOVT2jrV2WvTPq72zrsfaw8YCAfVKy-wO1B4ywzM6SOdLB5dnCcivQAlh_UXYll-C5EuY-x-03f8eKecav0u-356SvLBwyrZMwgCn0ubpLXOvIKg_7CaDN1es2LGDzqA1hc-StlBg7rNTIQ7I4RsOIKrm_ZSbG_1Lqi0zGwCx2PKWJOttdcA3abIaj_CNhqzSQkjY95LTqZpc2697v4HZejdVMLNQ4NJC0n1CLol7yYEgkPhU0Ezzqi112pxbaDnVBecVnabT6TuV_AkvV77E&lang=sage

http://localhost:8888/?z=eJzNGWtv47jxe4D8B9aJISnrle27LlDEcdDe9hZ3wLZXdNP2Qy4wGIu2uStTKknF9gX5750hKYl6ONn0WrRZrC0PhzPDeXO0ktmWLLPtlvBtnklNPtE1e8_S9D3CqCL4fXriFouCJ6cnpycr3PXjXw56k4m40DxVsZaU65RpVRL6gaobhKkR-VFotmZyRP4m-DJL2Ih8l2UpwpWmYgm_P6QZ1SPykSvdop5wlaf0UFK9QPanJ8uUKkX-wZM102HFKbo8PSHwp6kE-ELQLSPzkmk42Bn0QWSReOKtOVjCVmTBkwV80yLVoWLpqiSKf5LpQgoSWEpvhyogQ6OUGD9-G0bxhu0tuv00mp1XBw1Rmz4vXD_KLaGawmYEx_jcXLkNeBLcletol5aUyCtEzJGvkLlB9wCRL-_vc5nlTOpDLSNSOKaIx6dyszXIX6lYM2cV-_WCSSRuKC2y5QLWjCuEE1kC6b4CTicV-IGmBasW3lVwpVle45fQxRd2UAC-DYBHMCIBUMUvQwUfcFtw55C5WGyoSFImYQt6aviBpqqpKGM92M5BPWwB2Isix0ejqRHBc45IlibwyHa-5vjKGswe4Nr-AHE8FKNgyhUjf0ek76XMZDiwG4YJYfslY4kymhkmA_DAsKY4qghGUYMpiEGu3CIXX8_tnqXZzpjmKC8ufF5Nrpm2SJ5SW7zNslNeV8Wwj-vFwqn14uLLDhxJ-QpVBThs6HmeFSuKq73VLm8TMsXgizOx2Kq1PZUVEH97qGfg7GvIS-ANgGvS3GK5QXaErhCKXHz0TG-Y3KFCXWBbZ1VkSUWgQaFE5WzJV5wlLYFa9K1QfV7mNG_c-lfFLxC4BJVRraVTMUAissokPsDRPEZPbeN4Ht8wSKVbxUQSVunLCurbVrJcOtv2CDe4MkYl4TCeriKCn5fVx_VRX6wjwD1hbHccqza1OzcavX2IZia4kQXrJGfYdhssMyhwQgd3twGCy0SCf1oeWv7eq9sWjoseh4Y0exCsmC3bjWxtgKc7z4dXXNA0bUvSc0aT6DwtHBSoL8kKHe8kB1sHP0tb9IzNehFXaaE2PZFsjL3R27Rr8FxyYfNE1wkGg6uEPxBTX-aDoRpcX40BcA0LToyq9nk-b5uGbkX14S1j1yno9ASPs1DQCS3iz_SBqqXkuQ6BJS4-UOkXOtDaqhBLzTNBQnR760vk0RW-DVexawPwa1Y3BmXuOY8haveH0KDWjjkye6No5hMCM97T5RcsZo9eps3y4p5c-iD8A3PkhQZ4Hwe76JjU-1yUP83wqBXfI_XTlk1fwDosYhcVBuSjmMarQoaf_iI2CWDeEE9tZfBUjafQmT7krMRrKL_SOVrILp6HA3iIB-RNybtUJ4RXiEspE2u9IfP5nEwiX4HOAUWRpm7LU3MnBFUSDrgALQ6i43Ss3STDDG7aHdwcNUk6XrDwwrF9Oo2zQ81Bsr4GSqTzMLgyUkLk2O8gik3WCJAm2tGgBqVQRn3WjpWZZn6IYQoLEYvPJzPCoa-onMTpAaBv3jTUgOiYz-Y17i0vXcfoAGWwcrXyWEtXBg-SvultbfaPGuJZXcQ0z7H-1BzAGa5UTsX4GuxFk-Q95pRwAC4NvzXba0sR-xm7KerSMNyPrh7jQPdNDtCdPUvjXiKF17IxqmgwsspxdGa-_jIRDmyXMRg104PZ4zqQxMtBT8e9srGl4ZbsQTd8UkAvOTe96B9NsvWCEZfeWueA4-iK3BWBtr_hSuMxdGLpwfUfhD0weSCTeAo3TdDs6QmsN4O46UB1duhknHbodMK8GyGPT7P_YlBUQQAoOZWK2YtNM1aiVoTUpu_bhZFT7agPiP4U94XCEcwel-7HPOaVjbJWdYvuvtqodQ3Uhm_M0aFeSJl1QW14pl-jPXM-V7gcigd-wZXQrX_jp-XnXPI5n_s_SLv_e085lvit8d3xpGCpcafFlgpo4GRc3t4WdgQRumI3as2vaLqjB7WA1OTfJU2gQN9nukJskP0JBwBlOZ-yfaMbUm2p3oAT8y2rQKLY5gecp4n89AQnGiKPUy7g3EsWTuRoav6bMQYa691EQssSApLiItxH5ILYGQf6gMBLQdnMyyrSw7JsIeNYpYzl4SSeTN7Jqhk_gz_y4eNPN-T7Pd3mKatnaZAidO_kBqRk2PvhbK5s6_unOcEKaOTwP-h0_2qT7V66KCZ8qUPDzc6ozGPUIYUM3H0HbniHDkGzrayZKQr9C8_D_QjSZLvlN1J1RhfIZJkyKvsFLvVxe_cMtV93FbHcX3WFKieT5rLEE3NTKi9NaBY3-3SXp8C_Oj173TnHpPbJAoLxeJmIz5CZ06xIVimVDM03pp_pfpzyezVGTuNJ_Lt4Ov78zwLKcowQTA7xZ2X6S9O66EPKCCbneYCxPl4qFVyTuJbzkcC33lxi6R_OyIbx9UZfkm8nk3w_e7oaGwqm-TFmvsnCwYbRxOVKzHm1O_9797P6ptKuCPWF5XV3OJumarleV6JAApWlLE6zdVjPp4ArRgN0-GeBd8UZdYW2wVS2cV-fLKuQfiZf1mdqpMtVqu0kVtf5EmB-xuxJhO_k6Js6D1YJ0G41p92PKmgHvMyUBdt_r35PUb6P-IM41KnxE-jupy1b05vuq4YM4f6EvzGI_LKbm6wGATCHVCxNgzqf2ke8PAN0Co8mhc-nAAbbQduT7RYiE2zuz53REj6jWrGwRa7VPCzz25mbNBYKoqw67o7D9dSVISnBds7RgeafgZf9dWj8wtmQOaDXcHkTIi8zWazGPeDFSbhJQJ6R8VZwYaH6uUztsfWnw92ZcG23zki4Td_If2T-2nO26tVBm47ur-zf1C8u-k7uiWCLeY8azghc9MgPN3_6SHSGV1ySZNsXy8kZYUIVkjk_VSlPcGKtSCLpTvQqoTmKr8se9t24C8SefFUdfaH626ug6VXww98PfbNxMwJ5sbwYNoWIoPmF0Gm_xjBF8BnBgVRr1dSnoyXdrFYNR-xeLcSH_0iVP-LTLxf5wo5ETRG0FfQtTflaXJIl5HsmZ3BTEPqt4r-wSwKuNxzOgutzdLSfrRvo6Nz2AVf38nqo8PPcLp1fEmwcytG6Ob8vUTTyXaWxAicBFhmo0cuXDujw7bu8byeyAXWv7KYl9EgMTU0IGYxKc_8CrYzxbA==&lang=sage

Frontend
--------
* Extend codemirror's multiplexing mode addon to handle the string
  decorators (including end delimiter syntax, which probably involves
  extending the mode to have strings from the opening regex
  substituted into the closing string)
* Change output model so that output of a request can be confined, and
  the browser knows where the output goes (instead of just trusting
  the python side to send an output id).  This would help with displaying errors, for example. (see https://github.com/sagemath/sagecell/issues/387)


Fall 2013
=========

* [X] Revamp the timeout mechanism:
  - no purpose to linked message attribute---just request a default
    timeout when the kernel is created
  - To set the default timeout from code, we should just have a
    special function that will deliver a message to the intermediate
    zmq/websocket bridge to set the timeout, instead of surreptitously
    adding timeout data to every message.

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


