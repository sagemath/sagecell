This is a very simple demo of a 3-component Python compute service,
using mongodb.  

DEPENDENCIES:

   * Python packages: pymongo, flask 
   * MongoDB   

To start it all up, do the following:

1. Start the server: 
         python hello.py

2. Start the database server:
         cd mongo; ./go

3. Start the compute device:
         python device.py

4. Point your browser at:
         http://127.0.0.1:5000

CAVEAT: If you're on a multi-user machine, any other user on that same
machine could eval arbitrary expressions as the sage device process
(3) above.




