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

Testing
-------

Here are some tests that should be written:

 * an interact (maybe where the user waits a small random amount of time, then "moves the slider", another small random amount of time and "changes an input", etc.

 * upload a file, do some operation on the file, and then get the result (and the resulting file)

 * a longer computation than just summing two numbers. Maybe a for loop that calculates a factorial of a big number or something.

 * generate a file in code (maybe a matplotlib plot) and download the resulting image

 * Exercise the "Sage Mode" --- that should also be an option for all of the above

 * Sage-specific preparser tests.

 * tests exercising memory and cputime limits::

    import time
    a = []
    for i in range(20):
        a.append([0] * 50000000)
        time.sleep(1)
        print(get_memory_usage())

   or for time limits::

       factor(2^4994-3^344)
