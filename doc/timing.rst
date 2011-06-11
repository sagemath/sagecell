Timing
=======

.. automodule:: timing


Test Scripts
------------

Timing Utilities
^^^^^^^^^^^^^^^^

.. automodule:: timing.test_scripts.timing_util

Timing Tests
^^^^^^^^^^^^

.. automodule:: timing.test_scripts.simple_computation

Notes on Timing
---------------

These tests are performed using ``sage.math`` to query
``boxen.math.washington.edu``.

  * When merely pinging the server set up with `300 uwsgi processes
    <http://sage.math.washington.edu/home/jason/multi/projects/timing/results/results_2011.06.09_11.31.44/results.html>`_,
    we are only able to get about 550 requests/sec.  This ping
    involves only requesting a URL and getting a simple json response
    back.  Since a computation involves at least two server requests (one to
    submit the computation, another to receive the answer), this puts
    an upper bound of about 275 computations per second (without
    counting for the load of actually doing the computations).
  * When we use 400 threads to submit computations to the database and
    ask once for the outputs (without actually doing the computation;
    no device is running) with `200 uwsgi processes
    <http://sage.math.washington.edu/home/jason/multi/projects/timing/results/results_2011.06.09_10.34.12/results.html>`_
    and with `300 uwsgi processes
    <http://sage.math.washington.edu/home/jason/multi/projects/timing/results/results_2011.06.09_10.41.12/results.html>`_,
    we get about 500 requests/sec and about 250 computations/sec.  The
    boxen load went up by about 5 during this test.  So it appears
    that accessing mongo for submitting requests and for getting
    answers does not really slow us down.
  * The maximum simple computation (adding two numbers) throughput
    I've been able to achieve is around `200 computations per second <http://sage.math.washington.edu/home/jason/multi/projects/timing/results/results_2011.06.08_14.33.04/results.html>`_,
    but the load on boxen was nearly 35 when this happened.  We had
    200 device workers at that time.


Other timing tools
^^^^^^^^^^^^^^^^^^

* `Grinder <http://grinder.sourceforge.net/>`_
* `JMeter <http://jakarta.apache.org/jmeter/>`_ (see also their `list
  of tools <http://jakarta.apache.org/jmeter/usermanual/boss.html#products>`_
* `Apache ab <http://httpd.apache.org/docs/2.0/programs/ab.html>`_::

    ab -c 1 -n 10000 http://boxen.math.washington.edu:5467/ping_json

* siege::
    
    ./siege -c 20 -b  -t 30s http://boxen.math.washington.edu:5467/ping_json

* `httperf <http://www.comlore.com/httperf.html>`_::

    ./httperf --server boxen.math.washington.edu --port 5467 --uri /ping_json www.sagemath.org --num-conns 10000 --timeout 1 --hog


