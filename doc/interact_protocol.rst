Interact Protocol
=================

Here we give a rough definition of what happens to get an interact working.

USER types into SINGLE CELL::

    @interact
    def f(n=slider(1,20,step=1)):
        print n

and presses "Submit"


Code goes into database and gets sent to device.

The interact decorator is defined in the user namespace on the device.

It:

  - Parses the arguments for the function
  - generates a unique name for the function and stores it in a global dict of interact functions for this cell
  - Sends a start interact message on the user message channel::
     
     msg_type='interact_start'
     content: 
     function_name: the unique name generated
     controls: a dict, with keys=variables, values=dict representing control::

        {'n': {'type': 'slider'
              'start': 0
              'end': 20
              'step': 1}}
     layout: the layout parameters for controls.  By default this is a list in order of arguments
         ['n']

  - executes the function with the default values
  - Sends an end interact message::

     msg_type='interact_end'

The BROWSER gets a series of messages like the following:::

    {"default":null,"control_type":"input_box","label":null}}},"msg_type":"interact_start"},"header":{"msg_id":0.17421273858338893}}
    {"parent_header":{"msg_id":"4ddd48c92da351296000001f"},"msg_type":"extension","sequence":3,"content":{"content":{},"msg_type":"interact_end"},"header":{"msg_id":0.877582738300609}}

The BROWSER:
  - creates a div for the interact control
  - initializes a javascript object which represents the interact control:
     - stores the function_id
     - sets up an on_change handler for any control
        - Send an evaluate message back to the server with function_id and new defaults.  Output is put into the interact div's output block, replacing old output.  This needs to be sent back with the same computation id (to get the same worker process).  This new computation will replace the original computation (possibly in a separate interact table).  It also includes something of a state number.
  - sets up the slider according to the control message
  - prints out the output inside of an output div inside the interact control
 

An interesting way to think about this architecture is:

  - BROWSER generates and interprets messages
  - FLASK is a router/filter for messages
  - DB is a huge buffer
  - DEVICE is a router for execution requests
  - DEVICE WORKER is overseer for the actual session
  - SESSION gets and executes messages

So the FLASK-DB-DEVICE-DEVICE WORKER chain is really just a huge long
message channel between the BROWSER and the SESSION

TODO
====

[ ] Change the execution requests to use IPython messages.  We still
probably want to store these in a special table, rather than just
putting them in the messages table.  Tables in the MongoDB would then
nicely correspond to 0MQ channels, and preserve the idea that the
database is merely a large buffer for the 0MQ channels.

[ ] When the first execution request for a computation is sent,
flask/DB assign a session id (this is what we call the computation id
right now).

[ ] When later execution requests are sent for the same session id,
they also have an message id.  In interacts, this is the function
that needs to be executed.  In this way, old requests for execution
are overwritten and old output is also overwritten.  This saves time
and disk space if there are a large number of execution requests
coming in for the same function.

[ ] When a device queries for work, it receives back both new session
requests as well as new execution requests for existing sessions on
the device.  There is another table in the database which matches
process ids up to device ids, so we'll be able to tell what new
execution requests are to be sent to the device.

[ ] A worker process in the device doesn't just execute code.
Instead, it opens up a queue to the device and accepts execution
requests.  The first execution request should be immediately placed
into the queue.  The worker polls this queue.  If the (configurable)
timeout on the poll is triggered, the worker terminates.  This allows
a server administrator to specify that worker processes should be
terminated if they are idle for 10 seconds, say.

 - If we get an interact message back, don't stop the computation and return an end of computation marker.  Instead, keep the worker open for X number of seconds and continue polling for new computation requests.

 - Support in the database multiple interact evaluation requests

 - On the devices, support multiple evaluation requests for worker processes

