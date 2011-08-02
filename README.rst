.. highlight:: bash

This is a demo of a 3-component Python compute service,
using MongoDB.

Installation
============

We depend on the following packages:

* `Flask <http://flask.pocoo.org/>`_
* `MongoDB <http://www.mongodb.org/>`_
* `PyMongo <http://api.mongodb.org/python/current/>`_
  (at least version 0.10.1, which is newer than the version
  packaged in Ubuntu!)
* `ØMQ <http://www.zeromq.org/>`_
* `pyzmq <http://www.zeromq.org/bindings:python>`_
* `MathJax <http://www.mathjax.org/>`_

Optionally, you can also use `nginx <http://www.nginx.org/>`_
and `uWSGI <http://projects.unbit.it/uwsgi/>`_ to have a multithreaded
web server that can drastically increase your capabilities over the
built-in Python web server.  There are lots of other WSGI servers you
could use as well.

These instructions assume that Sage is installed and that it can
be run using the command ``sage``.

Dependencies
------------

In the following instructions, ``$SERVER`` refers to the directory
containing all of the software (for example, it might be
``/var/singlecellserver``).

Build dependencies
^^^^^^^^^^^^^^^^^^

The builds below have their own dependences, which you will have to
install before successfully configuring them. On Ubuntu, this command
should take care of most or all of them::

    sudo apt-get install uuid-dev libpcre3-dev zlib1g-dev openssh-server

ØMQ
^^^

Download ØMQ and build it in ``$SERVER/zeromq-2.1.7/install/``::

    cd $SERVER
    wget http://download.zeromq.org/zeromq-2.1.7.tar.gz
    tar -xzvf zeromq-2.1.7.tar.gz
    cd zeromq-2.1.7
    ./configure --prefix=`pwd`/install && make install

nginx
^^^^^

Download nginx and build it in ``$SERVER/nginx-1.0.4/install/``::

    cd $SERVER
    wget http://www.nginx.org/download/nginx-1.0.4.tar.gz
    tar -xzvf nginx-1.0.4.tar.gz
    cd nginx-1.0.4
    ./configure --prefix=`pwd`/install && make install

uWSGI
^^^^^

These instructions are based on `these instructions
<http://webapp.org.ua/dev/compiling-uwsgi-from-sources/>`_.  We don't
want to require libxml2 (it's just for the config files, I believe),
so we'll make our own build configuration that doesn't support XML build
files.  Also note that any version of uwsgi before 0.9.8 will not build
with gcc-4.6.

#. Get uWSGI::

    cd $SERVER
    wget http://projects.unbit.it/downloads/uwsgi-0.9.8.1.tar.gz
    tar -xzvf uwsgi-0.9.8.1.tar.gz

#. Change the configuration file to set ``xml = false``::

    cd uwsgi-0.9.8.1/buildconf
    cp default.ini myproject.ini
    # edit myproject.ini to make the xml line read: xml = false
    cd ..

#. Build uWSGI::

    sage -python uwsgiconfig.py --build myproject

Python packages
^^^^^^^^^^^^^^^

Install the required Python packages. Note that we upgrade setuptools
since the version that comes with Sage is too old for the most recent
version of PyMongo.

The ``sudo`` in the first line is not required if Sage is not installed
in a protected directory. In the penultimate line, replace ``$SERVER``
with the same directory name that it represented above (environmental
variables will not be preserved inside the Sage shell). ::

    sudo sage -sh # install into Sage's python
    easy_install pip # install a better installer than easy_install
    pip install --upgrade setuptools # need upgrade for pymongo
    pip install flask
    pip install pymongo
    pip install pyzmq --install-option="--zmq=$SERVER/zeromq-2.1.7/install"
    exit


Single Cell Server
^^^^^^^^^^^^^^^^^^

The repository for this software is on GitHub, under the name
`simple-python-db-compute
<https://www.github.com/jasongrout/simple-python-db-compute>`_.
Either download the `tarball
<https://www.github.com/jasongrout/simple-python-db-compute/tarball/master>`_,
extract the contents into ``$SERVER``, and rename the directory to
``single-cell-server``; or use git to clone
the code::

    cd $SERVER
    git clone git://www.github.com/jasongrout/simple-python-db-compute.git single-cell-server

MongoDB
^^^^^^^

Download the appropriate version of MongoDB from
`here <http://www.mongodb.org/downloads>`_ and extract the
contents to the ``$SERVER`` directory.


Sage
^^^^

Several patches enable Sage to take advantage of the enhanced protocol
for communicating graphical displays.  In order to patch Sage, apply
the patches to your Sage installation found in the ``sage-patches``
directory.  Apply them in numeric order.  I suggest using Mercurial
Queues so that it is easy to back out the patches if needed.  After
applying the patches, rebuild Sage with ``sage -b``.

Jmol
^^^^
In sage mode, Sage can output 3d graphs in Jmol format.  The Jmol java
applet must be installed in order to see these.  It is sufficient to
make a symbolic link from the ``/static`` directory over to the
appropriate Jmol directory in the Sage notebook::

    cd $SERVER/static
    ln -s $SAGE_ROOT/sage/devel/sagenb/sagenb/data/jmol .

MathJax
^^^^^^^

MathJax is used for typesetting complex expressions. Due to its size, it
cannot be included in the repository, so it must be
`downloaded <http://www.mathjax.org/download/>`_ and installed
separately to $SERVER/static/mathjax/.


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
    $SERVER/mongodb-linux-x86_64-1.8.2/bin/mongod -f mongodb.conf

#. Now you need to set up usernames and passwords for database access,
   if the database is running on a shared server.

   .. note::

     MongoDB `authentication documentation
     <http://www.mongodb.org/display/DOCS/Security+and+Authentication>`_
     recommends that you run without authentication, but secure the
     environment so that the environment is trusted.

   Set up an admin user, authenticate, then set up a user for the
   ``singlecelldb`` database.  Since we include the
   ``<SINGLECELL_USER>`` and ``<SINGLECELL_PASSWORD>`` in a URL later,
   it's helpful if neither of them contain any of ``%:/@`` (any
   length of password with letters and numbers would be okay).  ::

      $SERVER/mongodb-linux-x86_64-1.8.2/bin/mongo --port <MONGODB_PORT> # start up mongo client
      > use admin
      > db.addUser("<ADMIN_USER>", "<ADMIN_PASSWORD>")
      > db.auth("<ADMIN_USER>", "<ADMIN_PASSWORD>")
      > use singlecelldb
      > db.addUser("<SINGLECELL_USER>", "<SINGLECELL_PASSWORD>")
      > quit()

nginx
^^^^^

#. Make the ``$SERVER/nginx-1.0.4/install/conf/nginx.conf`` file have
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


#. Start nginx::

    $SERVER/nginx-1.0.4/install/sbin/nginx

Single Cell Server
^^^^^^^^^^^^^^^^^^

First, minify CSS and JavaScript files (this is required)::

    cd $SERVER/static
    make

The only thing left now is to configure and start the single-cell
compute server.  The server will automatically launch a number
of workers via passwordless SSH into an untrusted account (i.e., an
account with heavy restrictions; this account will be executing
arbitrary user code).

.. warning::

    The untrusted account will execute arbitrary user code, which may
    include malicious code.  Make *sure* that you are securing the
    account properly.  Working with a professional IT person is a very
    good idea here.  Since the untrusted accounts can be on any
    computer, one way to isolate these accounts is to host them in a
    virtual machine that can be reset if the machine is compromised.

    These instructions assume that the locked-down account is on the
    same computer as the server.

1. Install OpenSSH if it is not already installed.

2. Create a new restricted user account and enable passwordless SSH
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

3. Create a configuration file
   ``$SERVER/single-cell-server/singlecell_config.py`` by copying and
   modifying
   ``$SERVER/single-cell-server/singlecell_config.py.default``.  The
   ``mongo_uri`` should be set to
   ``mongodb://<SINGLECELL_USER>:<SINGLECELL_PASSWORD>@localhost:<MONGODB_PORT>``.
   If you will be running the server using Sage, replace the line
   ``python='python'`` with ``python='sage -python'``.

  .. warning:: Make the ``singlecell_config.py`` file *only* readable by
      the trusted account, not by the untrusted account, since it
      contains the password to the database::

          chmod 600 singlecell_config.py

4. Start uWSGI. The ``-p 50`` means that uWSGI will  launch 50 workers
   to handle incoming requests.  Adjust this to suit your needs. ::

       sage -sh
       cd $SERVER/single-cell-server
       ../uwsgi-0.9.8.1/uwsgi -s /tmp/uwsgi.sock -w web_server:app -p 50 -M

5. Start up the trusted server. Replace ``<UNTRUSTED_USER>@localhost``
   below with the SSH address for the untrusted account. Adjust the
   number of workers (``-w``) to meet your needs. Add the argument
   ``-q`` to minimize the number of log messages. ::

       cd $SERVER/single-cell-server/
       sage -python trusted_db.py -w 50 --untrusted-account untrusted@localhost

   When you want to shut down the server, just press Ctrl-C. This should
   automatically clean up the worker processes.

6. Go to ``http://localhost:<SERVER_PORT>`` to use the single-cell server.


License
=======

See the file "LICENSE.txt" for terms & conditions for usage and a
DISCLAIMER OF ALL WARRANTIES.

