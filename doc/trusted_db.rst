Trusted database
================

Because a user will be able to run arbitrary Python code from their browser,
the processes in which this execution takes place must be run out of a
user account that has very few privileges. It must also not be allowed
to directly access the database. Indirect database access is allowed
through the :class:`db_zmq.DB` class.

Additionally, each message from a user session must prove that they
originated from that session. To solve this problem, we use this
security scheme:

1. The trusted process generates two random keys and stores them in
   two files, ``/tmp/sage_shared_key1`` and ``/tmp/sage_shared_key2``
   on the disk. The first key is associated with the database; the
   second key is for the filestore.
2. The trusted process uses SSH to start the untrusted worker
3. The untrusted device reads and stores the keys from the two files,
   and then deletes the files.
4. When the untrusted device gets an execution request and starts a
   new session:

   a. The untrusted device resets the key associated with the database
      to that key's SHA1 sum. It then creates a new :mod:`hmac` object
      with the new key value as the initial secret and the SHA1 function
      in the ``digestmod`` argument.
   b. It sends an IPython ``extension`` message through its
      :class:`db_zmq.DB` instance with a ``msg_type`` of
      ``"create_secret"`` and a content of ``{session: SESSION_ID}``.
   c. The trusted device receives this message and performs the same
      procedure with its own copy of the key, creating its own :mod:`hmac`
      object associated with the session. The trusted and untrusted sides
      now both have two different :mod:`hmac` objects from the same secret.
      If both sides perform the same updates on their own :mod:`hmac`,
      they will remain equivalent.
   d. Steps a--c are repeated with the filestore object and keys

When the untrusted side needs to send a message to the untrusted side,
the ØMQ database adaptor sends the message as the second part of a
multipart message, the first part being the binary digest of its
:mod:`hmac` object updated with the string of the message to be sent.
The trusted process performs the same update on its own :mod:`hmac`
object and compares the digest from that result with the digest it
has received. If the digests match, the message is considered to have
passed authentication. This ensures that not only are messages being
sent from the right sessions, they are also sent and received in the
same order.

While sending a batch of output messages, the trusted device sends
a list of tuples of the form ``(hexdigest, message_str)``, where the hash
is updated for each message, instead of sending a single hash for the
entire list of messages. This allows it to send output from different
sessions in the same ØMQ message, for purposes of efficiency.

.. automodule:: trusted_db
   :members:
