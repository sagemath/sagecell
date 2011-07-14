Interacts
=========

Supported Interacts
-------------------

Supported / Partially Supported Interact Controls and Features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

[X] Checkbox

[X] Input Box

[X] Input Grid

[A] Selector (Dropdown List, Button, Radio Button)

* No multiple select (only single-item select)

[X] Button (New Interact Control)

* Unlike the button selector, allows for a button to be pressed multiple times.
* Unlike the button selector, user choice is not remembered, but is instead applied only once.

[X] Button Bar (New Interact Control)

* Multiple grouped instances of the Button control

[X] Slider

* Both continuous sliders and discrete sliders which iterate through values or objects in a list
* Continuous sliders have a numerical input box which updates the slider / interact (to use, click on displayed slider value)

[X] Multi-Slider (New Interact Control)

* Renders a set of either continuous or discrete sliders, each of which can take their own parameters. The value of the control is returned as a one-dimensional list with entries of the values of each slider.

[X] Color Picker

* Currently only uses colorpicker (one of the Sage options).

[X] Autoguessing Syntax

[X] User defined-update parameters

* Update button that can update an entire interact or only particular variables
* Arbitrary variables can update other arbitrary variables

[X] Layouts

* Users can specify order of controls and position relative to interact output

Using Interacts
---------------

An interact is defined using a function with the ``@interact`` decorator.
Any time the output of the interact is requested, the function will run with
arguments whose values are determined by the state of the interact controls.

The controls of an interact can be defined in two ways:

* In the arguments of the :func:`~interact_singlecell.interact` function::

    @interact([("name1", control1), ("name2", control2)])
    def f(**kwargs):
        ...

* In the arguments of the inner function::

    @interact
    def f(name1=control1, name2=control2):
        ...

The ``name``\ s above are the names of the argument through which the inner
function (here ``f``) will be passed the value of the control. The
``control``\ s are objects representing interact controls: either instances
of subclasses of :class:`~interact_singlecell.InteractControl` (see
:ref:`controls`) or objects using the
:ref:`Autoguessing Syntax <autoguessing-syntax>`.

The following code (if run in Sage Mode) will generate two sliders with
default configurations and print the sum of their values::

    @interact
    def f(a = slider(), b = slider()):
        print a + b

If Sage Mode is not enabled or if Sage libraries cannot be imported, the
previous code must be prefaced with
``from interact_singlecell import *`` to run. Sage already reserves
part of the user namespace (such as the decorator @interact), so the
singlecell replaces the Sage decorator with its own version. In contrast,
since the singlecell can also run and interpret stock python code, the
goal is to avoid cluttering the user namespace, so the prefacing import
statement must be explicit.

Updating Interacts
^^^^^^^^^^^^^^^^^^

By default, interact controls update themselves automatically when they 
are changed. However, one can specify custom updating structures in two
different ways:

* UpdateButton controls. This creates an interact control which, when clicked, updates specified variables.

* Decorator specification. If a parameter ``update`` is given in @interact, arbitrary variables can update other arbitrary variables. This should take the form::
    
    update = {"updated var": ["var_1 to update" ... "var_n to update"]}

For both options, one can give the shortcut ``["*"]`` in place of variable names to bind all variables.

.. _controls:

Interact Layouts
^^^^^^^^^^^^^^^^

An entire interact can be visualized as a table taking the following form::

     ____________________________________________
    |             |               |              |
    |  top_left   |  top_center   |   top_right  |
    |_____________|_______________|______________|
    |             |               |              |
    |     left    |  __output__   |     right    |
    |_____________|_______________|______________|
    |             |               |              |
    | bottom_left | bottom_center | bottom_right |
    |_____________|_______________|______________|


In the interact decorator, a parameter ``layout`` can be given taking the form::

    layout = {"location_1": ["var_1" ... "var_n"] ... "location_n": ["var_1" ... "var_n"]}
    
where ``location_n`` is an element of the interact table, with the exception of ``__output__`` (which is reserved for interact output). The given controls will be placed in the corresponding location in the table in the order in which they are given.

If layout is manually specified, all variables must be manually specified. To manually place all variables (alphabetically) in a given portion of the table, the following shortcut can be used::

    layout = {"location": ["*"]}

If layout is not given, controls will be placed alphabetically in the ``top_center`` area, above interact output.

For backwards compatibility with the interact layout parameter in the Sage Notebook, ``top`` and ``bottom`` map to ``top_center`` and ``bottom_center``.

Controls
^^^^^^^^

.. autoclass:: interact_singlecell.InteractControl

.. autoclass:: interact_singlecell.Checkbox
   :show-inheritance:
   :no-members:

.. autoclass:: interact_singlecell.checkbox

.. autoclass:: interact_singlecell.InputBox
   :show-inheritance:
   :no-members:

.. autoclass:: interact_singlecell.input_box

.. autoclass:: interact_singlecell.InputGrid
   :show-inheritance:
   :no-members:

.. autoclass:: interact_singlecell.input_grid

.. autoclass:: interact_singlecell.Selector
   :show-inheritance:
   :no-members:

.. autoclass:: interact_singlecell.selector

.. autoclass:: interact_singlecell.DiscreteSlider
   :show-inheritance:
   :no-members:

.. autoclass:: interact_singlecell.discrete_slider

.. autoclass:: interact_singlecell.ContinuousSlider
    :show-inheritance:
    :no-members:

.. autoclass:: interact_singlecell.continuous_slider

.. autoclass:: interact_singlecell.MultiSlider
    :show-inheritance:
    :no-members:

.. autoclass:: interact_singlecell.multi_slider

.. autoclass:: interact_singlecell.ColorSelector
    :show-inheritance:
    :no-members:

.. autoclass:: interact_singlecell.color_selector

.. autoclass:: interact_singlecell.Button
    :show-inheritance:
    :no-members:

.. autoclass:: interact_singlecell.button

.. autoclass:: interact_singlecell.ButtonBar
    :show-inheritance:
    :no-members:

.. autoclass:: interact_singlecell.button_bar

.. autoclass:: interact_singlecell.HtmlBox
    :show-inheritance:
    :no-members:

.. autoclass:: interact_singlecell.UpdateButton
    :show-inheritance:
    :no-members:

Note that for each control, not all parameters must be given; the device 
will automatically assign default parameters as needed.

.. _autoguessing-syntax:

Autoguessing Syntax
^^^^^^^^^^^^^^^^^^^

If an interact control is not explicitly given, the device will 
automatically attempt to guess which control should be rendered. The 
syntax for this follows the current syntax in the Sage notebook. See the 
Sage documentation (:func:`sagenb.notebook.interact.automatic_control`) 
for more details. For instance, to create an input box with a label 'Label'
and an initial value of 15 that prints twice its (numerical) input, one 
could submit::

    @interact
    def f(n = ("Label", 15)):
        print 2 * n

This is equivalent to::

    @interact
    def f(n = input_box(label = "Label", default = 15, raw = True)):
        print 2 * n

The interact autoguessing present in Sage is fully supported.

Interact Protocol
-----------------

Here we give a rough definition of what happens to get an interact working.

USER types into SINGLE-CELL::

    @interact
    def f(n = continuous_slider(interval = (1,20), stepsize = 1)):
        print n

and presses "Submit".

Code goes into the database and gets sent to the device.

The interact decorator is defined in the user namespace on the device. It:

1. Parses the arguments for the function, if necessary
2. Generates a unique identifier for the function and stores it
   in a global dict of interact functions for this session along with
   the state of the function's arguments.
3. Sends a message of type ``interact_prepare`` on the
   user message channel:

   .. code-block:: javascript

       {"msg_type": "interact_prepare",
       "content": {"interact_id": "12345" /* the unique ID generated */,
                   "controls": {"n": {"type": "slider"
                                      "range": [0, 20]
                                      "step": 1,
                                      "default": 0,
                                      "raw": true,
                                      "label": ""}}
                   "layout": ["n"] /* the layout parameters for controls */ }}

4. Pushes the generated interact ID onto a session-wide stack. The output
   messages of any executed code will now have their ``output_block`` field
   set to the interact ID to tell the BROWSER where to place the output.
5. Executes the function with the default values.
6. Pops the interact ID off of the stack to resume normal output.

The BROWSER:

1. Creates a div for the interact control
2. Initializes a JavaScript object which represents the interact control:
3. Sets up the controls according to the ``interact_prepare`` message
4. Upon receiving the initial output from step 5 above, inserts that output
   into a div below the controls
5. Repeatedly polls the server for updates

After the USER makes a change on one of the controls, the BROWSER
detects it and sends a new ``execute_request`` message with some code
that will call the function whose arguments that control manipulates,
with the updated argument(s).

    _update_interact('12345')(n=3,)

When the EXEC process receives this message, it pushes the ID (``"12345"``)
to the output stack, updates the stored state of the interact with the
new argument(s) and executes the function with the new state. Any output
from this execution will be put into a message whose ``output_block``
field contains the ID. The BROWSER receives the output message, and
replaces the current contents of the div representing the interact
output with the new output it receives.

An interesting way to think about this architecture is:

  - BROWSER generates and interprets messages
  - FLASK is a router/filter for messages
  - DB is a huge buffer
  - DEVICE is a router for execution requests
  - DEVICE WORKER is overseer for the actual session
  - SESSION gets and executes messages

So the FLASK--DB--DEVICE--DEVICE WORKER chain is really just a long
message channel between the BROWSER and the SESSION.

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

[ ] Generic HTML control that would allow user-defined controls

.. code-block:: javascript

    {msg_type: "interact_control"
     content: {control_type: "html",
               html: /* string for the HTML of the control. The
                        onChange handler should trickle up beyond
                        this html. */
               sanitize: /* string for a JavaScript function which
    	                    takes in the div containing only the
                            "html" string, and returns a string
                            representing the value of the control */}}

[A] Select Box control

[X] JqueryUI slider control

[X] Get current Sage interact theme

[A] Use sent layout parameters and css / tables to output interacts.

[X] Other interact controls (checkbox, matrix/grid, buttons, etc.)


Interact Backend
----------------

This script is responsible for interpreting interact definitions and 
sending interact messages to the client.

.. autofunction:: interact_singlecell.automatic_control

.. autofunction:: interact_singlecell.interact

.. autofunction:: interact_singlecell.decorator_defaults

Interact Frontend
-----------------

See the :ref:`js` Documentation.

Interact Module
---------------

.. automodule:: interact_singlecell
