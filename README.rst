.. highlight:: bash

This is a demo of a 3-component Sage computation service,
using MongoDB.

Installation
============

We depend on the following packages:

* `Flask <http://flask.pocoo.org/>`_
* `MongoDB <http://www.mongodb.org/>`_
* `PyMongo <http://api.mongodb.org/python/current/>`_
  (at least version 1.10.1, which is newer than the version
  packaged in some Ubuntu releases)
* `ØMQ <http://www.zeromq.org/>`_
* `pyzmq <http://www.zeromq.org/bindings:python>`_
* `MathJax <http://www.mathjax.org/>`_


These instructions assume Sage 5.0.beta4 is installed.

Dependencies
------------

In the following instructions, ``$SERVER`` refers to the directory
containing all of the software (for example, it might be
``/var/sagecellsystem``).

Build dependencies
^^^^^^^^^^^^^^^^^^

The builds below have their own dependences, which you will have to
install before successfully configuring them. On Ubuntu, this command
should take care of most or all of them::

    sudo apt-get install uuid-dev zlib1g-dev openssh-server

Sage
^^^^

Install Sage 5.0.beta4.  ``$SAGE_ROOT`` refers to the installation
directory.

Install the flask Sage notebook by following the directions at http://trac.sagemath.org/sage_trac/ticket/11080.

ØMQ
^^^

Download ØMQ and build it in ``$SERVER/zeromq/installed/``::

    cd $SERVER
    wget http://download.zeromq.org/zeromq-2.1.11.tar.gz
    tar -xzvf zeromq-2.1.11.tar.gz
    ln -s zeromq-2.1.11 zeromq
    cd zeromq
    ./configure --prefix=`pwd`/installed && make install

Python packages
^^^^^^^^^^^^^^^

Install the required Python packages. ::

    sudo sage -sh # install into Sage's python
    easy_install pip # install a better installer than easy_install
    pip install flask
    pip install pymongo
    pip install pyzmq --install-option="--zmq=$SERVER/zeromq/installed"
    exit


Sage Cell Server
^^^^^^^^^^^^^^^^

The repository for this software is in the `sagemath/sagecell
<https://github.com/sagemath/sagecell>`_ repository on Github.

Either download the `tarball
<https://github.com/sagemath/sagecell/tarball/master>`_ and
extract the contents of the contained folder into ``$SERVER/sagecell``,
or use git to clone the code::

    cd $SERVER
    git clone git://github.com/sagemath/sagecell.git sagecell

MongoDB
^^^^^^^

Download the appropriate version of MongoDB from `here
<http://www.mongodb.org/downloads>`_ and extract the contents to the
``$SERVER`` directory.  Then make a symbolic link named
``mongodb-bin`` to the installation directory::

    ln -s $SERVER/mongodb-linux-x86_64-2.0.2 $SERVER/mongodb-bin

Sage
^^^^

Several patches enable Sage to take advantage of the enhanced protocol
for communicating graphical displays.  In order to patch Sage, apply
the patches to your Sage installation found in the
``$SERVER/sagecell/sage-patches`` directory.  Apply them in numeric
order.  We suggest using Mercurial Queues so that it is easy to back
out the patches if needed.  After applying the patches, rebuild Sage
with ``sage -b``. ::

  sage -sh
  cd $SAGE_ROOT/devel/sage/
  hg qimport $SERVER/sagecell/sage-patches/01-sage-embedded.patch
  hg qpush
  hg qimport $SERVER/sagecell/sage-patches/02-sage-show.patch
  hg qpush
  exit
  sage -b


Jmol
^^^^
In sage mode, Sage can output 3d graphs in Jmol format.  The Jmol java
applet must be installed in order to see these.  It is sufficient to
make a symbolic link from the ``/static`` directory over to the
appropriate Jmol directory in the Sage notebook::

    cd $SERVER/sagecell/static
    ln -s $SAGE_ROOT/local/share/jmol .

MathJax
^^^^^^^

MathJax is used for typesetting complex expressions. Due to its size, it
cannot be included in the repository, so it must be
`downloaded <http://www.mathjax.org/download/>`_ and installed
separately to ``$SERVER/sagecell/static/mathjax/``.

Configuration and Running
-------------------------

MongoDB
^^^^^^^

#. Make new directories ``$SERVER/mongodb`` and
   ``$SERVER/mongodb/mongo``::

    mkdir -p $SERVER/mongodb/mongo

#. Make a ``$SERVER/mongodb/mongodb.conf`` file. Copy the text
   below into this file, replacing ``<MONGODB_PORT>`` with the port
   you want for your database and ``<$SERVER>`` with the path of
   the server directory. ::

    dbpath = <$SERVER>/mongodb/mongo/
    bind_ip = localhost
    port = <MONGODB_PORT>
    auth = true
    logpath = <$SERVER>/mongodb/mongodb.log
    logappend = true
    nohttpinterface = true

    # Comment the below out (don't just switch to false)
    # in order to cut down on logging
    verbose = true
    cpu = true

#. Start up the MongoDB daemon (replace the location of mongodb as
   appropriate)::

    cd $SERVER/mongodb/
    $SERVER/mongodb-bin/bin/mongod -f mongodb.conf

#. OPTIONAL: Now you need to set up usernames and passwords for database access,
   if the database is running on a shared server.

   .. note::

     MongoDB `authentication documentation
     <http://www.mongodb.org/display/DOCS/Security+and+Authentication>`_
     recommends that you run without authentication, but secure the
     environment so that the environment is trusted.

   Set up an admin user, authenticate, then set up a user for the
   ``sagecelldb`` database.  Since we include the
   ``<SAGECELL_USER>`` and ``<SAGECELL_PASSWORD>`` in a URL later,
   it's helpful if neither of them contain any of ``%:/@`` (any
   length of password with letters and numbers would be okay).  Change
   ``<ADMIN_USER>``, ``<ADMIN_PASSWORD>``, ``<SAGECELL_USER>``, and
   ``<SAGECELL_PASSWORD>``, and ``<MONGODB_PORT>`` to appropriate values::

      $SERVER/mongodb-bin/bin/mongo --port <MONGODB_PORT> # start up mongo client
      > use admin
      > db.addUser("<ADMIN_USER>", "<ADMIN_PASSWORD>")
      > db.auth("<ADMIN_USER>", "<ADMIN_PASSWORD>")
      > use sagecelldb
      > db.addUser("<SAGECELL_USER>", "<SAGECELL_PASSWORD>")
      > quit()

Sage Cell Server
^^^^^^^^^^^^^^^^

First, minify CSS and JavaScript files (this is required)::

    cd $SERVER/sagecell/static
    make

The only thing left now is to configure and start the Sage cell server.
The server will automatically launch a number of workers via
passwordless SSH into an untrusted account (i.e., an account with heavy
restrictions; this account will be executing arbitrary user code).

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
   (``ssh <UNTRUSTED_USER>@localhost``) and out (``exit``).
   If you have a passphrase for your key, you may need to type it
   once, but there should be a way to store the key and log in
   fully automatically.

#. Create a configuration file
   ``$SERVER/sagecell/sagecell_config.py`` by copying and
   modifying
   ``$SERVER/sagecell/sagecell_config.py.default`` and make the
   following changes:

   * The ``mongo_uri`` variable should be set to
     ``mongodb://<SAGECELL_USER>:<SAGECELL_PASSWORD>@localhost:<MONGODB_PORT>``.
   
   * If you do not use Sage or ``sage -sh`` to start the scripts, the
     ``sage`` variable should be set to point to the sage executable.
     If you will not be running the server using Sage, define the
     ``python`` and other variables in the config file appropriately
     to not use the ``sage`` variable.

   .. warning:: Make the ``sagecell_config.py`` file *only* readable by
      the trusted account, not by the untrusted account, since it
      contains the password to the database::

          chmod 600 sagecell_config.py

#. Start the webserver::

       sage -sh
       cd $SERVER/sagecell
       ./start_web.py

#. Start the trusted server::

       sage -sh
       cd $SERVER/sagecell
       ./start_device.py

   When you want to shut down the server, just press Ctrl-C. This should
   automatically clean up the worker processes.

#. Go to ``http://localhost:8080`` to use the Sage Cell server.

Optional Installation
=====================

You can use ``nginx`` and ``uwsgi`` to get a more capable webserver.

nginx
-----

First, install the ``libpcre3-dev`` library (if on Ubuntu).  This
makes it so that when nginx is a reverse proxy, it can rewrite the
headers so that the absolute URLs work out correctly. ::

    sudo apt-get install libpcre3-dev

Download nginx and build it in ``$SERVER/nginx/install/``::

    cd $SERVER
    wget http://www.nginx.org/download/nginx-1.0.12.tar.gz
    tar -xzvf nginx-1.0.12.tar.gz
    ln -s nginx-1.0.12 nginx
    cd nginx
    ./configure --prefix=`pwd`/install --without-http_rewrite_module && make install



Make the ``$SERVER/nginx/install/conf/nginx.conf`` file have
only one server entry, as shown here (delete all the others).
``<SERVER_PORT>`` should be whatever port you plan to expose to
the public (should be different from ``<MONGODB_PORT>``). ::

    server {
        listen <SERVER_PORT>;
        server_name localhost;
        charset utf-8;
        client_max_body_size 4M; # Maximum file upload size of 4MB
        location / {
            uwsgi_pass unix:/tmp/uwsgi.sock;
            include uwsgi_params;
        }
    }

Start nginx::

    $SERVER/nginx/install/sbin/nginx


uWSGI
-----

These instructions are based on `these instructions
<http://webapp.org.ua/dev/compiling-uwsgi-from-sources/>`_.  We don't
want to require libxml2 (it appears to be only for the config files),
so we'll make our own build configuration that doesn't support XML build
files.

#. Get uWSGI::

    cd $SERVER
    wget http://projects.unbit.it/downloads/uwsgi-latest.tar.gz
    tar -xzvf uwsgi-latest.tar.gz
    ln -s uwsgi-1* uwsgi

#. Change the configuration file to set ``xml = false``::

    cd uwsgi/buildconf
    cp default.ini sagecell.ini
    # edit myproject.ini to make the xml line read: xml = false
    cd ..

#. Build uWSGI::

    sage -python uwsgiconfig.py --build sagecell

#. Create a symbolic link to uWSGI in ``$SERVER/sagecell``::

      ln -s $SERVER/uwsgi/uwsgi $SERVER/sagecell/uwsgi

#. Set the ``webserver`` variable in the ``sagecell_config.py`` file
   to be ``'uwsgi'``.

.. note:: If there are errors when you start the uwsgi server, you may
   need to change permissions of ``/tmp/uwsgi.sock``::

       chmod 777 /tmp/uwsgi.sock



License
=======

See the ``LICENSE.txt`` file for terms and conditions for usage and a
DISCLAIMER OF ALL WARRANTIES.
