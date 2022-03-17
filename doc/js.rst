.. _js:

Javascript Frontend
===================

.. default-domain:: js


Dependencies
^^^^^^^^^^^^
JQuery: http://www.jquery.com

JQueryUI: http://www.jqueryui.com

CodeMirror: http://codemirror.net/

MathJax: http://www.mathjax.org/


Embedding Module
^^^^^^^^^^^^^^^^

Embedding into any page creates a global Javascript object named ``sagecell`` and a variable named ``sagecell_dependencies``.


Accessible Methods and Variables
________________________________


.. _sagecell.templates_embed:
.. attribute:: sagecell.templates

   Built-in embedding templates. See :ref:`templates <Templates>` in the
   Embedding documentation for more information.

.. _sagecell.quietMode:
.. attribute:: sagecell.quietMode

   Boolean. When set to true, only essential messages are printed to the console.

.. _sagecell.init_embed:
.. function:: sagecell.init(callback)

   Initializes Sage Cell embedding capabilities and loads external CSS and
   Javascript libraries.

   :param Function callback: Callback function to be executed after all external
     libraries have loaded.

.. _sagecell.makeSagecell:
.. function:: sagecell.makeSagecell(args)

   Constructs a Sage Cell instance. This function itself mainly interprets
   configuration information; the majority of the actual rendering is done by
   :ref:`sagecell.initCell() <sagecell.initCell>`.

   :param Dict args: Dictionary containing Sage Cell configuration information.
      See :ref:`customization <Customization>` for more information.
   :returns: Dictionary of Sage Cell information used by other methods.

.. _sagecell.deleteSagecell:
.. function:: sagecell.deleteSagecell(sagecellinfo)

   Deletes a Sage Cell instance.

   :param Dict sagecell info: Dictionary of Sage Cell information returned by
      :ref:`sagecell.makeSagecell() <sagecell.makeSagecell>`.

.. _sagecell.moveInputForm:
.. function:: sagecell.moveInputForm(sagecellinfo)

   Moves form elements of a Sage Cell instance outside of that instance's
   embedding context (most useful in cases where a Sage Cell is embedded
   within an external form which, on submission, should not send Sage Cell
   content).

   :param Dict sagecellinfo: Dictionary of Sage Cell information returned by
      :ref:`sagecell.makeSagecell() <sagecell.makeSagecell>`.

.. _sagecell.restoreInputForm:
.. function:: sagecell.restoreInputForm(sagecellinfo)

   Restores the Sage Cell form elements moved using
   :ref:`sagecell.moveInputForm() <sagecell.moveInputForm>` to the Sage
   Cell instance's embedding context.

   :param Dict sagecellinfo: Dictionary of Sage Cell information returned by
      :ref:`sagecell.makeSagecell() <sagecell.makeSagecell>`.

Internal Methods
________________


.. _sagecell.initCell:
.. function:: sagecell.initCell(sagecellinfo)

  Called by :ref:`sagecell.makeSagecell() <sagecell.makeSagecell>`.
  Renders a Sage Cell instance.

  :param Dict sagecellinfo: Dictionary of Sage Cell configuration
    information created by
    :ref:`sagecell.makeSagecell() <sagecell.makeSagecell>`.

.. _sagecell.sendRequest:
.. function:: sagecell.sendRequest(method, url, data, callback, [files])

   Send an HTTP request to a URL using an ``XMLHttpRequest``, JSONP, or
   a form submission. This function will give the same result regardless of
   cross-origin issues.

   :param string method: HTTP method (usually "GET" or "POST")

   :param string url: URL to which to send the request. The host portion of this
     URL must be the same as the one from which the JavaScript is loaded.

   :param object data: parameters to send with the request
   
   :param function callback: a function that takes a single argument. If the
     request succeeds, the function will be called with the string containing
     the server response.

   :param Array files: if the browser supports the ``FormData`` class, an array
     of ``File`` objects to be uploaded; otherwise, an array of ``input``
     elements of ``type="file"``. This argument will be ignored if ``method`` is
     ``GET``.

.. _sagecell.renderEditor:
.. function:: sagecell.renderEditor(editor, inputLocation)

   Called by :ref:`sagecell.initCell() <sagecell.initCell>` Renders the
   code editor for a Sage Cell instance.

   :param String editor: Name of editor to be rendered
   :param inputLocation: jQuery selector corresponding to the location for Sage
      Cell input (where the editor should be created).
   :returns: ``[editor, editorData]`` where ``editor`` is the name of the
      rendered editor and ``editorData`` is additional data required to later
      modify the rendered editor.


Utility Functions
^^^^^^^^^^^^^^^^^

These functions serve a variety of repeated purposes throughout the Sage Cell Server and are located in the object ``sagecell.functions``.

.. _uuid4:
.. function:: sagecell.functions.uuid4()
    
    Creates a UUID4-compliant identifier as specified in `RFC 4122 <http://tools.ietf.org/html/rfc4122.html>`_. `CC-by-SA-licensed <http://creativecommons.org/licenses/by-sa/2.5/>`_ from `StackOverflow <http://stackoverflow.com/questions/105034/how-to-create-a-guid-uuid-in-javascript>`_ contributers.

.. _makeClass:
.. function:: sagecell.functions.makeClass()

    Generic class constructor to instantiate objects. `MIT-licensed <http://www.opensource.org/licenses/mit-license.php>`_ by `John Resig <http://ejohn.org/blog/simple-class-instantiation/>`_. 

.. _colorize:
.. function:: sagecell.functions.colorize()

    Colorizes error tracebacks formatted with `IPython <http://ipython.scipy.org>`_'s ultraTB library.

.. _createElement:
.. function:: sagecell.functions.createElement(type, [attrs, [children]])

    Creates a DOM element with the given parameters.

    :param string type: the element type
    :param object attrs: the attribute names and values for the element
    :param Array children: a list of child nodes to give this element


Session Class
^^^^^^^^^^^^^

.. _Session:
.. class:: sagecell.Session(outputLocation, selector, sageMode, hideDynamic)

    Manages Sage Cell functionality for a given cell, including client-server communication and displaying and rendering output.

    :param Object outputLocation: jQuery object for output location
    :param String selector: JQuery selector for overall session output
    :param Bool sageMode: whether Sage Mode is toggled
    :param Object hideDynamic: output elements that should be dynamically hidden

Session Functions
_________________

.. _Session.appendMsg:
.. function:: Session.appendMsg(msg, string)

    :param JSON msg: JSONify-able message to be appended.
    :param String string: Text (Send, Receive, etc.) to preface the message.
    
    Appends response message to the messages div.

.. _Session.clearQuery:
.. function:: Session.clearQuery()

    Ends web server querying for the session.

.. _Session.get_output:
.. function:: Session.get_output()

    Polls the web server for computation results and other messages. Calls :ref:`get_output_success() <Session.get_output_success>` when messages are returned for the session.

.. _Session.get_output_success:
.. function:: Session.get_output_success(data, textStatus, jqXHR)

    Callback function that is executed if the GET request in :ref:`get_output() <Session.get_output>` succeeds. Interprets, formats, and outputs returned message contents as user-readable HTML.

.. _Session.output:
.. function:: Session.output(html)

    Outputs content to the JQUery selector defined in :ref:`session_output <Session.session_output>`.
    
    :param String html: Html markup to be inserted.
    :returns: Jquery selector of last child element of the output location, which can be used to chain output.
    
.. _Session.restoreOutput:
.. function:: Session.restoreOutput()

    Resets output location for computations to its default value, sets :ref:`replace_output <Session.replace_output>` to append (rather than replace) previous output, and resets :ref:`lock_output <Session.lock_output>` to guarantee that the output location can be set. This function overrides any previous uses of :ref:`setOutput() <Session.setOutput>`.

.. _Session.send_computation_success:
.. function:: Session.send_computation_success(data, textStatus, jqXHR)
    
    Callback function that is executed if the post request in :ref:`sendMsg() <Session.sendMsg>` suceeds. Checks that the returned session ID matches the sent session ID.
    
.. _Session.sendMsg:
.. function:: Session.sendMsg(code[, id])

    Posts an "execute_request" message to the web server. Supports sending messages with custom message IDs. Calls :ref:`send_computation_sucess() <Session.send_computation_success>` if post request succeeds.
    
    :param String code: Code to be executed.
    :param id: Custom message ID.

.. _Session.setQuery:
.. function:: Session.setQuery()

    Sets web server querying for new messages for the session.

.. _Session.setOutput:
.. function:: Session.setOutput(selector[, replace, lock])
    
    Sets output location for computations.
    
    :param String location: JQuery selector for computation output within the overall session output location.
    :param Bool replace: Flag designating whether computation output should replace (true) or be appended to (false) existing output.
    :param Bool lock: Flag designating whether :ref:`setOutput() <Session.setOutput>` can change the output location.

.. _Session.updateQuery:
.. function:: Session.updateQuery(interval)

    Sets web server querying for new messages for the session at a given interval.
    
    :param Int interval: New querying interval (in milliseconds).

Session Variables
_________________

.. _Session.eventHandlers:
.. attribute:: Session.eventHandlers

    Tracks event handlers associated with the session.

.. _Session.interacts:
.. attribute:: Session.interacts

    Tracks interacts associated with the session.

.. _Session.lock_output:
.. attribute:: Session.lock_output

    Boolean flag which determines whether :ref:`setOutput() <Session.setOutput>` can set the output. Note that :ref:`restoreOutput() <Session.restoreOutput>` always overrides this flag.

.. _Session.session_output:
.. attribute:: Session.session_output

    JQuery selector which controls location of computation output.

.. _Session.poll_interval:
.. attribute:: Session.poll_interval

    Interval (milliseconds) used in polling the web server for additional messages.

.. _Session.replace_output:
.. attribute:: Session.replace_output

    Boolean flag which determines whether output (stdout, stderr, etc.) should be appended to or replace previous output.

.. _Session.sequence:
.. attribute:: Session.sequence

    Sequence number of latest message received for the session; used to track messages across sessions and check they are being received in the correct order.

.. _Session.session_id:
.. attribute:: Session.session_id

    Unique session ID generated by :ref:`uuid4() <uuid4>`.


InteractCell Class
^^^^^^^^^^^^^^^^^^

.. _InteractCell:
.. class:: sagecell.InteractCell(selector, data)

    Manages the configuration, display, and state of an interact control.
    See :doc:`interact_protocol` for more details.
    
    :param String selector: JQuery selector for the location of the interact control.
    
    :param Dict data: Configuration data, including layout and controls.

InteractCell Functions
______________________

.. _InteractCell.bindChange:
.. function:: InteractCell.bindChange(interact)

    Binds Javascript change handlers for each interact control. When a change is noticed, :ref:`getChanges() <InteractCell.getChanges>` is called to determine updated function parameters and a message is sent using :ref:`Session.sendMsg() <Session.sendMsg>` with a :ref:`custom message ID <InteractCell.msg_id>` to update the interact computation result. 
    
    :param InteractCell interact: InteractCell object.

.. _InteractCell.getChanges:
.. function:: InteractCell.getChanges()

    Gets the values of an interact's controls.
    
    :returns: Dictionary of parameters and values for a given interact.

.. _InteractCell.locateButtonIndex:
.. function:: InteractCell.locateButtonIndex(n, nCols)

    Gets the index position (row, col) of the nth entry of a two-dimensional array. Used for the selector interacts.
    
    :param Int n: Entry in the array (e.g. 1st, 2nd, 3rd, etc. entry), where n is calculated by incrementing a counter at each entry while progressing along columns, then rows.
    :param Int nCols: Number of columns in the two-dimensional array.
    :return: Dictionary, where dict[location] = n, dict[row] = row, dict[col] = col.

.. _InteractCell.renderCanvas:
.. function:: InteractCell.renderCanvas()

    Renders interact controls as HTML.


InteractCell Variables
______________________

.. _InteractCell.controls:
.. attribute:: InteractCell.controls
    
    Dictionary containing data on various controls (input box, slider, etc.) in the interact.

.. _InteractCell.element:
.. attribute:: InteractCell.element

    JQuery selector for the location where the interact's controls should be rendered.

.. _InteractCell.function_code:
.. attribute:: InteractCell.function_code

    Unique function code for the interact 

.. _InteractCell.interact_id:
.. attribute:: InteractCell.interact_id

    Unique ID for the interact generated by :ref:`uuid4() <uuid4>`.

.. _InteractCell.layout:
.. attribute:: InteractCell.layout

    Dictionary containing data on the layout of the controls in :ref:`controls <InteractCell.controls>`.

.. _InteractCell.session:
.. attribute:: InteractCell.session

    :ref:`Session <Session>` object which the interact is instantiated within.

.. _InteractCell.msg_id:
.. attribute: InteractCell.msg_id

    Unique ID used to differentiate and identify interact computation results. Also used as a selector for output of interact functions.


InteractData Object
^^^^^^^^^^^^^^^^^^^

Contains classes and functions providing control over rendering, updating, monitoring, and extracting data from each type of interact control. Located at ``sagecell.InteractData``. See :doc:`interact_protocol` for details on specific interact controls.

Each type of control (Button, Checkbox, etc.) is a separate value within the InteractData object instantiated as a class. For instance, ``sagecell.InteractData.Button`` is the class referring to a Button control. Each class must contain the following methods:

.. _InteractData.init:
.. function:: InteractData.control.init(args)

   :param Dict args: Dictionary containing arguments necessary for control initialization.

   Initializes control object.

.. _InteractData.changeHandlers:
.. function:: InteractData.control.changeHandlers()

   Returns a list of jQuery change handlers associated with the given control.

.. _InteractData.changes:
.. function:: InteractData.control.changes()

   Retrieves value of a changed control;

.. _InteractData.html:
.. function:: InteractData.control.html()

   Returns core HTML code for the control.

.. _InteractData.finishRender:
.. function:: InteractData.control.finishRender()

   Adds onto core HTML code for more advanced or specific functionality. This often includes binding specific change handlers for the control.
