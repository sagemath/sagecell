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
  - Sends a start interact message on the user message channel::
     
     msg_type='interact_start'
     content: 
     function_code: (either the string function def or bytecode)
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
     - stores the function_code text
     - sets up an on_change handler for any control
        - Send an evaluate message back to the server with function code and new defaults.  Output is put into the interact div's output block, replacing old output.
  - stores the function_code in a javascript object representing the interact control
  - sets up the slider according to the control message
  - prints out the output inside of an output div inside the interact control
 
