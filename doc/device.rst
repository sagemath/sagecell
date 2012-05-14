=========
 Devices
=========

The device executes user code and puts the resulting messages into the database.

.. _trusted:

Trusted device
==============

Because a user will be able to run arbitrary Python code from their browser,
the processes in which this execution takes place must be run out of a
user account that has very few privileges. It must also not be allowed
to directly access the database. Instead, the worker process communicates
over ØMQ with a process running from a trusted account.

The untrusted process can ask the trusted process to perform a database
operation, and if that operation is allowed, the trusted process will
perform it and send back the result. The trusted process is also
responsible for making sure that any messages that get sent from a
particular session really did come from the session that it claims.

Trusted--Untrusted communication
--------------------------------

Initialization
^^^^^^^^^^^^^^

When the trusted device is started, it starts an untrusted device in
a more secure location and passes it a pair of randomly generated
strings that will serve as security keys later on.

1. The trusted process generates two random keys and stores them in
   two files, ``/tmp/sage_shared_key1`` and ``/tmp/sage_shared_key2``
   on the disk. The first key is associated with the database; the
   second key is for the filestore.
2. The trusted process uses SSH to start the untrusted worker.
3. The untrusted device reads and stores the keys from the two files,
   and then deletes the files.

Now, both the untrusted and the trusted processes have in memory copies
of the same pair of randomly generated strings. These are used to generate
shared secrets for each new session.

Unauthenticated messages
^^^^^^^^^^^^^^^^^^^^^^^^

Messages sent from the untrusted device before a session starts are
unauthenticated. Unauthenticated messages are sent using the following
procedure:

1. The untrusted device calls a method of a :class:`db_zmq.DB` or
   :class:`filestore.FileStoreZMQ` object. This is the same method it
   would call if it were a normal (trusted) database object, and it
   gets the same response.

2. The database or filestore object sends a message over ØMQ to the
   trusted device. The message is an IPython-style message like this::

       {"header": {"msg_id":ID_NUM},
        "msg_type": METHOD_NAME,
        "content": {KWARG_NAME1: KWARG_VAL1,
                    KWARG_NAME2: KWARG_VAL2}}

   where ``METHOD_NAME`` is the name of the desired database method
   and the keyword arguments to that method are passed in the ``content``
   field.
3. The trusted device, running a ØMQ event loop, receives this message,
   after confirming that validation is not needed for this method, runs
   the method on its own database. The return value of this function
   (possibly ``None``) is sent back over ØMQ in pickle form.
4. The untrusted process, which has in the meantime been waiting for
   the response, receives it and returns it as the result of the
   method originally called in step 1.

.. note::

   The existance of unauthenticated messages may mean that a user could
   send a message spoofing the main untrusted worker function. There should
   probably be HMAC authentication for the main
   :func:`~device_process.worker` function to prevent this from happening.

Starting a session
^^^^^^^^^^^^^^^^^^

When the untrusted device gets an execution request and starts a new session:

1. The worker process sends calls the DB object's unauthenticated method
   :meth:`~db_zmq.DB.create_secret`, triggering the steps described above.
   The argument to this function is the ID of the new session.
2. When the trusted process receives a ``create_secret`` message,
   instead of passing it on to the database:

   a. The trusted process calculates the SHA1 of its copy of the database
      key, and changes the key to that SHA1.
   b. The trusted process creates an :mod:`hmac` object with the DB key
      as the secret and the SHA1 function for the digestmod. This object
      will be stored throughout the session.
   c. The trusted process sends the value ``True`` to the database
      in order to confirm that this procedure has been successfully
      carried out.

3. The untrusted worker receives this ``True`` value and performs steps
   2a and 2b using its own copy of the database key. This causes the
   copies of the DB key in both processes to have the same value
   (since they were the same, then both were replaced with their SHA1).
   They therefore have also created equivalent :mod:`hmac` objects.
   Each session has its own such set of these objects.
4. Steps 1--3 are repeated for the filestore key, generating a separate
   :mod:`hmac` object. The database's :mod:`hmac` gets stored (the
   execution  process doesn't need it), and the filestore :mod:`hmac`
   is passed to the execution process.

Authenticated messages
^^^^^^^^^^^^^^^^^^^^^^

When a method of :class:`db_zmq.DB` or :class:`~filestore.FileStoreZMQ`
is called with an ``hmac`` argument set to an :mod:`hmac` object,
an *authenticated* message is sent, using the following procedure:

1. The same IPython-style message is created as in an unauthenticated
   message.
2. The message is converted into a JSON-formatted string.
3. The :mod:`hmac` object's :obj:`update` method is called, using
   the JSON string for the ``msg`` argument. Because this object is
   passed by reference, this change will be preserved after the
   function returns.
4. A ØMQ multi-part message is sent. The first part contains the
   JSON string; the second part contains the (binary) digest of the
   :mod:`hmac` object.
5. The trusted device receives this message. It checks to see whether
   the message needs authentication, and when it sees that it does:

   a. It updates its copy of the :mod:`hmac` object associated with
      that session and database, created above, with the JSON string
   b. If the digest of the trusted device's copy matches the digest
      sent in the message, authentication has succeeded; the
      database method is executed and the return value sent back.
      If the digests do not match, authentication has failed;
      the trusted device's :mod:`hmac` object is reset to its
      previous state and the value ``None`` is sent back.

Note that this leaves the :mod:`hmac` objects for that database the
same again in both the trusted and untrusted side. This parity is
essential for the authentication procedure.

Authenticated file messages
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :class:`~filestore.FileStoreZMQ` method
:meth:`~filestore.FileStoreZMQ.create_file` involves sending the complete
contents of a file over ØMQ to the trusted process. It sends the messages
in the same style as above, but its outgoing multipart message contains
the contents of the file as a string.

.. note::

   The JSON message is authenticated, but the file contents are not.
   Maybe they should be.

The :meth:`~filestore.FileStoreZMQ.copy_file` method of the same class
sends a normal authenticated JSON message, and receives from the trusted
side a pure string (as opposed to a pickled Python object) containing
the file contents, which it writes to the disk.

Output messages
^^^^^^^^^^^^^^^

When the user's code creates an output message (e.g. with a ``print``
statement), that message gets passed to a global queue and is picked
up by the main worker process. This queue contains the output from
every running process all mixed together. Every time the worker
processes the queue, it retrieves all of the messages available to
it at that time and calls :meth:`db_zmq.DB.add_messages`. The
arguments of this function the list of retrieved messages (as dicts)
and the dict of sessions mapped to :mod:`hmac` objects for the
database.

:meth:`~db_zmq.DB.add_messages` iterates through the message list.
At each one, it updates that message's session's :mod:`hmac` with the
JSON string of the message, and then appends a tuple of the form
``(MESSAGE_STR, HEX_DIGEST)`` to a new list. (Note the use of hex digest
instead of binary digest.) This sent to the trusted device in an
*unauthenticated* message of type ``add_messages``. The authentication
for these messages occurs for each message individually, not the entire list.

Upon receiving this list, the trusted device goes through the list in
order and authenticates each message individually. All messages that
pass authentication will be added to the database for the web server
to find.

Trusted device code documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: trusted_db
   :members:


Untrusted Subprocess-based Device
---------------------------------

This device implements the IPython 0.11 messaging scheme for communicating results back to the client.

.. automodule:: device_process
    :members:

User code-device interaction
----------------------------

.. automodule:: user_convenience
