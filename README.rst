This is a very simple demo of a 3-component Python compute service,
using mongodb.  


INSTALLATION
============

Dependencies

#. Flask
#. MongoDB
#. Pymongo (at least version 0.10.1, which is newer than the version
   packaged in Ubuntu!)


Install
-------
* ZeroMQ::
  
      wget http://download.zeromq.org/zeromq-2.1.7.tar.gz
      tar -xzvf zeromq-2.1.7.tar.gz
      cd zeromq-2.1.7
      ./configure --prefix=/scratch/jason/sage-4.7/local/
      make
      make install
     
* nginx::
  
      wget http://nginx.org/download/nginx-1.0.4.tar.gz
      tar -xzvf nginx-1.0.4.tar.gz 
      cd nginx-1.0.4
      ./configure --prefix=`pwd`/install && make install
    
   Make the ``install/conf/nginx.conf`` file have only one ``server``
   entry::

      server {
          listen 5467;
          server_name localhost;
          charset utf-8;
          #root   /Users/wstein/sd29/nb/ss/;  
          location / {
              uwsgi_pass  unix:/tmp/uwsgi.sock;
              include     uwsgi_params;
          }
      }

    launch nginx::
        ./install/sbin/nginx 

* uwsgi (based on `these instructions <http://webapp.org.ua/dev/compiling-uwsgi-from-sources/>`_)::

      wget  http://projects.unbit.it/downloads/uwsgi-0.9.7.2.tar.gz
      tar -xzvf uwsgi-0.9.7.2.tar.gz 
      cd uwsgi-0.9.7.2/buildconf
      cp default.ini myproject.ini # change xml line to xml = false
      cd ..
      sage -python uwsgiconfig.py --build myproject
      


* Python packages::

      pip install --upgrade setuptools # need upgrade for pymongo
      pip install flask
      pip install pymongo
      pip install pyzmq --install-option="--zmq=/scratch/jason/sage-4.7/local/"
      
Old instructions
================
Pay no attention to the instructions below.  They are old and woefully
out of date.      







DEPENDENCIES:

   * Flask -- install with "easy_install flask"   (see http://flask.pocoo.org/)
   * MongoDB -- optional, if you want to use the mongodb database (see http://www.mongodb.org/)
   * Pymongo -- if you use MongoDB, install this with "easy_install pymongo" (see http://api.mongodb.org/python/)

To start it all up, do the following:

1. Start the database server, if needed (mongo will store data in a new directory
   mongo).  This is not needed if using sqlite

         ./start_mongo

2. Start the web server (specify sqlite if using a sqlite database):
         python web_server.py [sqlite]

3. Start the compute device (first argument is the number of worker
   processes).  Specify sqlite if using a sqlite database:
         python device.py 1 [sqlite]

4. Point your browser at:
         http://127.0.0.1:5000

To use an IPython device instead, use:
         python web_server.py ipython
         python device.py ipython

CAVEAT: If you're on a multi-user machine, any other user on that same
machine could eval arbitrary expressions as the sage device process
(3) above.


Instructions for running with Nginx and uWSGI:


1. Install uWSGI: download from
http://projects.unbit.it/uwsgi/wiki/WikiStart#Getit

then we follow directions from http://projects.unbit.it/uwsgi/wiki/Example

tar -xzvf uwsgi-0.9.6.8.tar.gz
cd uwsgi-0.9.6.8
sage -python uwsgiconfig.py --build # or just python, to use the
system python
cd path/to/simple/server
/path/to/uwsgi/uwsgi -s /tmp/uwsgi.sock -w web_server:app

At this point, you can test things by doing:

cd path/to/simple/server
/path/to/uwsgi/uwsgi --http 127.0.0.1:8080  -w web_server:app

Stop the server when you are ready to go on and install nginx.

2. Install Nginx: download from http://nginx.org/

tar -xzvf nginx-0.8.54.tar.gz
cd nginx-0.8.54
./configure --prefix=$HOME/nginx-local
make
make install

3. Make the nginx.conf file in the $HOME/nginx-local/conf directory have
this server entry:

server {
  listen 8080;
  server_name localhost;
  charset utf-8;
  #root   /Users/grout/projects/sagenb/git-simple-db-compute/;

  location / {
  	uwsgi_pass  unix:/tmp/uwsgi.sock;
        include     uwsgi_params;
    }
}

4. Start nginx:

$HOME/nginx-local/sbin/nginx

5. Go to localhost:8080.

Unfortunately, since it seems that command line parameters are not
passed into the wsgi app with the above uwsgi invocation, so there
isn't a way to specify a sqlite backend, yet.


To Use Tsung on OSX
===================

Install tsung via macports: sudo port install tsung (make sure to get
the 1.3.3 version; you might have to apply the patch https://trac.macports.org/ticket/28826)

Install mochiweb: sudo port install mochiweb

Modify the tsung_stats.pl script as follows: https://trac.macports.org/ticket/26255

Change the tsung.xml script to reference the dtd in 

--- tsung.xml	2011-03-16 00:28:01.000000000 -0500
+++ tsung-macports.xml	2011-03-18 07:04:04.000000000 -0500
@@ -1,5 +1,5 @@
 <?xml version="1.0" encoding="UTF-8"?>
-<!DOCTYPE tsung SYSTEM "/usr/share/tsung/tsung-1.0.dtd" [] >
+<!DOCTYPE tsung SYSTEM "/opt/local/share/tsung/tsung-1.0.dtd" [] >
 
 <!--
    This is a configuration file for Tsung (http://tsung.erlang-projects.org),


Then run tsung:

tsung -f tsung-macports.xml -l tsung.log start

You can check the status by going to another terminal and doing "tsung
status"

After finishing, go into the directory tsung created for your results
(which it prints out when it finishes) and do:

/opt/local/lib/tsung/bin/tsung_stats.pl


or to generate some reports using matplotlib, do

tsplot -v -d . my_run tsung.log
