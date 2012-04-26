======================================
 Notes for Possible Future Directions
======================================

Using IPython workers
---------------------

Issues when migrating to using IPython 0.12+ hub and engines

* We'd have to figure out a way to spawn an engine easily by forking a process, with custom initialization and cleanup (like putting files in a directory and cleaning up the files afterwards).

* We'd need to have a way to "wrap" any messages sent out, to translate them GAE channel messages, for example.  The IPython notebook seems to do this already with their websocket/zmq bridge.



