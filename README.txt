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
