This is a very simple demo of a 3-component Python compute service,
using mongodb.  

DEPENDENCIES:

   * Flask -- install with "easy_install flask"   (see http://flask.pocoo.org/)
   * MongoDB -- optional, if you want to use the mongodb database (see http://www.mongodb.org/)
   * Pymongo -- if you use MongoDB, install this with "easy_install pymongo" (see http://api.mongodb.org/python/)

To start it all up, do the following:

1. Start the database server (which will store data in a new directory
   mongo):
         ./start_mongo

2. Start the web server: 
         python web_server.py

3. Start the compute device:
         python device.py

4. Point your browser at:
         http://127.0.0.1:5000

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
