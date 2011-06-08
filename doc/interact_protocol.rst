Interacts
=========

Supported Interacts
-------------------

**Supported / Partially Supported Interact Controls:**

[X] Input Box

* String, Numerical, and Boolean values

[A] Selector

* Only drop-down menu is available (no button bar)
* No iterator support
* No multiple select (only single-item select)

[A] Slider

* Adds numerical input box which updates slider / interact (click on the displayed slider value)

* No iterator support

**Not Supported Interact Controls:**

[ ] Checkbox

[ ] Matrix / Grid / Button Bar

[ ] Color Picker

**Not Supported Interact Features:**

[ ] Layouts

[ ] Colors

Using Interacts
---------------

Verbose Syntax
^^^^^^^^^^^^^^

The verbose form of all interacts uses the following structure::

    # Interact decorator
    @interacts.interact
    
    # Function definition, including name, variables, and the variables' control types / options
    def <function name>(<variable> = interact.<control type>(<control options>)):
        [function body]

Full declarations of each control (with default parameter values shown) 
would be:

* Input Box::

    interact.input_box(default = "", raw = False, label = "")

  - default (String / Number / Bool): Default value of the input box.
  - raw (Bool): Boolean flag indicating whether the value of the input box should be treated as "quoted" (String) or "unquoted" (raw). By default, raw is False to enable text input including spaces, but if the control is to be used in any sort of numerical calculation or control flow, this flag should be True.
  - label (String): Label of the control.


* Selector::

    interact.selector(default = 0, values = [0], raw = False, label = "")

  - default (Int): Initially selected index of [values].
  - values (List): List of values (String, Number, and/or Boolean) from which the user can select.
  - raw (Bool): Boolean flag indicating whether the selected value should be treated as should be treated as "quoted" (String) or "unquoted" (raw). By default, raw is False to enable text including spaces, but if the control is to be used in any sort of numerical calculation or control flow, this flag should be True.
  - label (String): Label of the control.


* Slider::

    interact.slider(default = 0, range = (0, 100), step = 1, raw = True, label = "")

  - default (Number): Initial value of the slider.
  - range (List): Two-value numeric tuple with the form (min, max).
  - step (Number): Step size for the slider.
  - raw (Bool): Boolean flag indicating whether the selected value should be treated as should be treated as "quoted" (String) or "unquoted" (raw). Since the slider currently only supports numerical values, there is little reason for raw to be True.
  - label (String): Label of the control.

Note that for each control, not all parameters must be given; the device 
will automatically assign default parameters as needed.

Also, the function declaration supports multiple interact control parameters. For 
instance, the following would construct two sliders with default configurations 
and print the sum of their values::

    @interact.interact
    def f(n = interact.slider(), p = interact.slider()):
        print n + p

Interact Decorators
^^^^^^^^^^^^^^^^^^^

The interact decorator can be called in three different ways (using a 
basic slider control as an example):

* Normal decorator::

    @interact.interact
    def f(n = interact.slider()):
        print n

* Verbose decorator::

    def g(n = interact.slider()):
        print n
    interact.interact(g)

* Importing the interact class::

    from interact import *
    @interact
    def f(n = slider()):
        print n

If multiple interacts are used in the same input, the first two styles
of decorators can be used interchangeably. However, using the third style
necessarily requires that all interacts following the import statement 
conform to the same decorator syntax.

Autoguessing Syntax
^^^^^^^^^^^^^^^^^^^

If an interact control is not explicitely given, the device will 
automatically attempt to guess which control should be rendered. The 
syntax for this follows the current syntax in the Sage notebook. See the 
`Sage Documentation <http://www.sagemath.org/doc/reference/sagenb/notebook/interact.html#sagenb.notebook.interact.automatic_control>`_ 
for more details. For instance, to create an input box with a label 'Label'
and an initial value of 15 that prints twice its (numerical) input, one 
could submit::

    @interact.interact
    def f(n = ("Label", 15)):
        print 2 * n

This is equivalent to::

    @interact.interact
    def f(n = interact.input_box(label = "Label", default = 15, raw = True)):
        print 2 * n


Interact Protocol
-----------------

Here we give a rough definition of what happens to get an interact working.

USER types into SINGLE CELL::

    @interact.interact
    def f(n = interact.slider(range = (1,20), step = 1)):
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
              'range': [0, 20],
              'step': 1,
              'default': 0,
              'raw': True,
              'label':""}}
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

Interact TODO List
------------------

[X] Change the execution requests to use IPython messages.  We still
probably want to store these in a special table, rather than just
putting them in the messages table.  Tables in the MongoDB would then
nicely correspond to 0MQ channels, and preserve the idea that the
database is merely a large buffer for the 0MQ channels.

[X] When the first execution request for a computation is sent,
flask/DB assign a session id (this is what we call the computation id
right now).

[X] When later execution requests are sent for the same session id,
they also have an message id.  In interacts, this is the function
that needs to be executed.  In this way, old requests for execution
are overwritten and old output is also overwritten.  This saves time
and disk space if there are a large number of execution requests
coming in for the same function.

[A] When a device queries for work, it receives back both new session
requests as well as new execution requests for existing sessions on
the device.  There is another table in the database which matches
process ids up to device ids, so we'll be able to tell what new
execution requests are to be sent to the device.

[X] A worker process in the device doesn't just execute code.
Instead, it opens up a queue to the device and accepts execution
requests.  The first execution request should be immediately placed
into the queue.  The worker polls this queue.  If the (configurable)
timeout on the poll is triggered, the worker terminates.  This allows
a server administrator to specify that worker processes should be
terminated if they are idle for 10 seconds, say.

[ ] Generic HTML control that would allow user-defined controls ::

    msg_type: "interact_control"
    content: {"control_type": "html",
              "html": <string for the html of the control. The
    onChange handler should trickle up beyond this html.>
              "sanitize": <string for a javascript function which
    takes in the div containing only the "html" string, and returns a
    string representing the value of the control}

[A] Select Box control

[A] JqueryUI slider control

[X] Get current Sage interact theme

[ ] Use sent layout parameters and css / tables to output interacts.

[ ] Other interact controls (checkbox, matrix/grid, buttons, etc.)


Interact Backend
----------------

This script is responsible for interpreting interact definitions and 
sending interact messages to the client.

.. automodule:: interact
    :members:

Interact Frontend
-----------------

See the :doc:`js` Documentation.
