.. _advanced_installation:

Advanced Installation
=====================

In the following instructions, :envvar:`$SAGECELL` refers to the directory
containing the cell server, usually ``SAGE_ROOT/devel/sagecell``.

Configuration and Running
-------------------------

First, minify CSS and JavaScript files, as well as update the various
web components we depend on (this is required)::

    cd $SAGECELL
    make

Now we configure and start the Sage cell server.  The server will
automatically launch a number of workers via passwordless SSH into an
untrusted account (i.e., an account with heavy restrictions; this
account will be executing arbitrary user code).

.. warning::

    The untrusted account will execute arbitrary user code, which may
    include malicious code.  Make *sure* that you are securing the
    account properly.  Working with a professional IT person is a very
    good idea here.  Since the untrusted accounts can be on any
    computer, one way to isolate these accounts is to host them in a
    virtual machine that can be reset if the machine is compromised.

    These instructions assume that the locked-down account is on the
    same computer as the server.

#. Install OpenSSH if it is not already installed.

#. Create a new restricted user account and enable passwordless SSH
   from your account to the restricted account::

     sudo adduser <UNTRUSTED_USER>
     ssh-keygen # not needed if you already have a public key
     sudo mkdir <UNTRUSTED_USER_HOME_DIR>/.ssh
     sudo cp ~/.ssh/id_rsa.pub <UNTRUSTED_USER_HOME_DIR>/.ssh/authorized_keys

   Test the passwordless SSH by logging in
   (:samp:`ssh {<UNTRUSTED_USER>}@localhost`) and out (``exit``).
   If you have a passphrase for your key, you may need to type it
   once, but there should be a way to store the key and log in
   fully automatically.

#. Create a configuration file
   :file:`{$SAGECELL}/config.py` by copying and modifying
   :file:`{$SAGECELL}/config_default.py` and make the
   following changes:

   * In ``_default_config``, change the ``username`` value to
     :samp:`'{<UNTRUSTED_USER>}@localhost'`.

   * ``db_config["uri"]`` should be set to
     :samp:`'sqlite:///{<$SAGECELL>}/sqlite.db'` or some other URI as
     described at :ref:`Database Engines <sqlalchemy:engines_toplevel>`.

     .. warning:: Make the sqlite file is *only* readable by the
        trusted account, not by the untrusted account::

          chmod 600 sqlite.db

#. Start the webserver::

       sage web_server.py -p <PORT_NUMBER>

   When you want to shut down the server, just press :kbd:`Ctrl-C`. This should
   automatically clean up the worker processes.

#. Go to http://localhost:<PORT_NUMBER> to use the Sage Cell server.



Making an spkg
--------------

In order to make an spkg, after the cell server is installed, just go
into the main cell server repository directory and do::

    sage sage-spkg/spkg-dist

The spkg will be made in the :file:`dist/` directory

