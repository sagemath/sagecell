This is a very simple demo of a 3-component Python compute service,
using mongodb.  


Installation
============

We depend on the following packages:

#. Flask
#. MongoDB
#. Pymongo (at least version 0.10.1, which is newer than the version
   packaged in Ubuntu!)
#. ZeroMQ


Optionally, you can also use the following nginx and uwsgi to have a
multithreaded webserver that can drastically increase your
capabilities over the built-in python web server.  There are lots of
other WSGI servers you could use as well.

Installation
------------

In the following instructions, ``$SERVER`` refers to the directory
containing all of the software (for example, it might be
``/var/singlecellserver``).

ZeroMQ
^^^^^^

I had problems trying to build this using Sage's shell, but it seems
to work fine if I build it outside of the sage shell, but just install
it into the Sage tree::
  
    cd $SERVER
    wget http://download.zeromq.org/zeromq-2.1.7.tar.gz
    tar -xzvf zeromq-2.1.7.tar.gz
    cd zeromq-2.1.7
    ./configure --prefix=$SAGE_ROOT
    make install
     
nginx
^^^^^
  
Get and make nginx in the ``install`` directory::
  
    cd $SERVER
    wget http://nginx.org/download/nginx-1.0.4.tar.gz
    tar -xzvf nginx-1.0.4.tar.gz 
    cd nginx-1.0.4
    ./configure --prefix=`pwd`/install && make install
    

uwsgi
^^^^^

These instructions are based on `these instructions
<http://webapp.org.ua/dev/compiling-uwsgi-from-sources/>`_.  We don't
want to require libxml2 (it's just for the config files, I believe),
so we'll make our own build configuration that doesn't support xml build
files.

#. Get uwsgi::

    cd $SERVER
    wget  http://projects.unbit.it/downloads/uwsgi-0.9.7.2.tar.gz
    tar -xzvf uwsgi-0.9.7.2.tar.gz 

#. Change the configuration file to set ``xml = false``::

    cd uwsgi-0.9.7.2/buildconf
    cp default.ini myproject.ini
    # edit myproject.ini to make the xml line read: xml = false
    cd ..
     
#. Build uwsgi::

    sage -python uwsgiconfig.py --build myproject
      


Python packages
^^^^^^^^^^^^^^^

Install the following python packages.  Note that we upgrade setuptools since the
version that comes with Sage is too old for the most recent version of
pymongo.  ::

    sage -sh # install into Sage's python
    easy_install pip # install a better installer than easy_install
    pip install --upgrade setuptools # need upgrade for pymongo
    pip install flask
    pip install pymongo
    pip install pyzmq --install-option="--zmq=$SAGE_LOCAL"
      

Single Cell Server
^^^^^^^^^^^^^^^^^^

`Download
<https://github.com/jasongrout/simple-python-db-compute/tarball/master>`_
from github or use git to clone the code.  The repository is at
`https://github.com/jasongrout/simple-python-db-compute
<https://github.com/jasongrout/simple-python-db-compute>`_. ::

   git clone git://github.com/jasongrout/simple-python-db-compute.git single-cell-server

MongoDB
^^^^^^^

Download and install `MongoDB <http://www.mongodb.org/>`_.


Configuration and Running
-------------------------

MongoDB
^^^^^^^

#. Make new directories ``$SERVER/mongodb`` and
   ``$SERVER/mongodb/mongo``::

    mkdir -p $SERVER/mongodb/mongo

#. Make a ``$SERVER/mongodb/mongodb.conf`` file.  Replace
   ``<MONGODB_PORT>`` below with the port you want for your
   database. ::

    dbpath = $SERVER/mongodb/mongo/
    bind_ip = localhost
    port = <MONGODB_PORT>
    auth = true
    logpath = $SERVER/mongodb/mongodb.log
    logappend = true
    nohttpinterface = true
    
    # Comment the below out (don't just switch to false)
    # in order to cut down on logging
    verbose = true
    cpu = true

#. Start up MongoDB::

    cd $SERVER/mongodb/
    mongod -f mongodb.conf

#. Now we need to set up usernames and passwords for database access,
   if the database is running on a shared server.

   .. note:: 

     Mongodb `authentication documentation
     <http://www.mongodb.org/display/DOCS/Security+and+Authentication>`_
     recommends that you run without authentication, but secure the
     environment so that the environment is trusted.

   We set up an admin user, authenticate, then set up a user for the
   ``singlecelldb`` database.  Since we include the
   ``<SINGLECELL_USER>`` and ``<SINGLECELL_PASSWORD`` in a URL later,
   it's helpful if neither of them contain any of ``%:/@`` (e.g., any
   length of password with letters and numbers would be okay).  ::

      mongo --port <PORT> # start up mongo client
      > use admin
      > db.addUser("<ADMIN_USER>", "<ADMIN_PASSWORD>")
      > db.auth("<ADMIN_USER>", "<ADMIN_PASSWORD>")
      > use singlecelldb
      > db.addUser("<SINGLECELL_USER>", "<SINGLECELL_PASSWORD>")

    
nginx
^^^^^

#. Make the ``$SERVER/nginx-1.0.4/install/conf/nginx.conf`` file have only one server
   entry (delete all the others).  Adjust ``<SERVER_PORT>`` to be whatever port you plan to
   expose to the public.  ::

    server {
        listen <SERVER_PORT>;
        server_name localhost;
        charset utf-8;
        client_max_body_size 4M; # Maximum file upload size, M stands for mB.
        location / {
            uwsgi_pass  unix:/tmp/uwsgi.sock;
            include  uwsgi_params;
        }
    }


#. Start nginx::

    $SERVER/nginx-1.0.4/install/sbin/nginx 


uwsgi
^^^^^

Start uwsgi. The ``-p 50`` means launch 50 workers to handle incoming
requests.  Adjust this to suite your needs. ::

  cd $SERVER/single-cell-server
  ../uwsgi-0.9.7.2/uwsgi -s /tmp/uwsgi.sock -w web_server:app -p 50




Single Cell Server
^^^^^^^^^^^^^^^^^^

The only thing left now is to configure and start the single-cell
compute server.  The compute server will automatically launch a number
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

#. Create a configuration file
   ``$SERVER/single-cell-server/singlecell_config.py`` by copying and
   modifying
   ``$SERVER/single-cell-server/singelcell_config.py.default``.  The
   ``mongo_uri`` should be something like
   ``<SINGLECELL_USER>:<SINGLECELL_PASSWORD>@localhost:<MONGODB_PORT>``.

  .. warning:: Make the ``singlecell_config.py`` file *only* readable by
      the trusted account, not by the untrusted account, since it
      contains the password to the database.

#. Start up the trusted server.  Replace ``untrusted@localhost`` with the SSH address for
   the untrusted account. Adjust the number of workers (``-w``) to meet your
   needs. Add ``-q`` to only print out very few messages.  ::

    cd $SERVER/single-cell-server/
    sage -python trusted_db.py -w 50 --untrusted-account untrusted@localhost

To shut down the server, just press Ctrl-C.  This should automatically
clean up the worker processes.



To Use Tsung on OSX
===================

Install tsung via macports: 

    sudo port install tsung 

(make sure to get the 1.3.3 version; you might have to apply the patch
`https://trac.macports.org/ticket/28826 <https://trac.macports.org/ticket/28826>`_)

Install mochiweb::

     sudo port install mochiweb

Modify the tsung_stats.pl script as follows::

    https://trac.macports.org/ticket/26255

Change the tsung.xml script to reference the dtd in ::

    --- tsung.xml	2011-03-16 00:28:01.000000000 -0500
    +++ tsung-macports.xml	2011-03-18 07:04:04.000000000 -0500
    @@ -1,5 +1,5 @@
     <?xml version="1.0" encoding="UTF-8"?>
    -<!DOCTYPE tsung SYSTEM "/usr/share/tsung/tsung-1.0.dtd" [] >
    +<!DOCTYPE tsung SYSTEM "/opt/local/share/tsung/tsung-1.0.dtd" [] >
 
     <!--
     This is a configuration file for Tsung (http://tsung.erlang-projects.org),


Then run tsung::

  tsung -f tsung-macports.xml -l tsung.log start

You can check the status by going to another terminal and doing "tsung
status"

After finishing, go into the directory tsung created for your results
(which it prints out when it finishes) and do::

    /opt/local/lib/tsung/bin/tsung_stats.pl


or to generate some reports using matplotlib, do::

    tsplot -v -d . my_run tsung.log
