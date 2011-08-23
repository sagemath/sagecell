.. _embedding:

Embedding Single Cell Instances
===============================

.. default-domain:: js

Description
^^^^^^^^^^^
Provides functionality to embed multiple customized instances of the Single Cell
in arbitrary webpages. Customizable options include location of input and output
and functionality shown to the user.

Dependencies
^^^^^^^^^^^^
jQuery: http://www.jquery.com

Basic Usage
^^^^^^^^^^^

jQuery is assumed to be loaded in ``<head>`` with ``$`` available.

In ``<head>``, the following lines should be inserted::

   <script type="text/javascript" src="http://<server>/embedded_singlecell.js"></script>
   <script type="text/javascript">singlecell.init();</script>

where ``<server>`` is the root url of a live Single Cell server. This downloads
additional required javascript and css libraries and creates a global javascript
object called ``singlecell``. See the documentation for
:ref:`singlecell.init() <singlecell.init_embed>` for more configuration options
upon initialization, including callback functionality.

Later, the following javascript should be run::

   singlecell.makeSinglecell({inputLocation: "[jQuery selector]"});

This creates a basic Single Cell instance at the location matching
``inputLocation``. This location must be a unique selector for an HTML element
in which content can be dynamically placed. See the documentation for
:ref:`singlecell.makeSinglecell() <singlecell.makeSinglecell>`
for more configuration options. This function returns a dictionary containing
information necessary to later move portions of or remove the entirety of the
Single Cell instance if desired.

``singlecell.makeSinglecell()`` can be called multiple times to embed multiple
Single Cell instances, as long as the input (and output, if specified) locations
of each instance are unique to the page.

To remove a Single Cell instance, the following javascript can be used::

   singlecell.deleteSinglecell(singlecellInfo);

where ``singlecellInfo`` is the dictionary of information returned upon that
Single Cell instance's creation by ``singlecell.makeSingleCell()``.

Single Cell instances can be safely embedded within HTML forms (even though each
instance contains form elements) since those form elements are copied to a
hidden form outside of the embedded context. However, in such a case, it may
not be optimal for external form submission to include Single Cell elements. To
prevent this issue, the following javascript can be used before and after form
submission to move and restore the Single Cell::

   singlecell.moveInputForm(singlecellInfo); // before submission
   singlecell.restoreInputForm(singlecellInfo); // after submission

where ``singlecellInfo`` is the dictionary of information returned upon that
Single Cell instance's creation by ``singlecell.makeSingleCell()``.

.. _Customization:

Customization
^^^^^^^^^^^^^

All customization occurs through ``singlecell.makeSinglecell()``, which takes a
dictionary as its argument. The key/value pairs of this dictionary serve as the
configuration of the created Single Cell instance. The following options can be
set when embedding:

Input Location
--------------

This sets the location of the input elements of a Single Cell, which includes
the editor, editor toggle, "Sage Mode" selector, file upload selector, and the
evaluate button::

   { ..
   inputLocation: "jQuery selector, must map to a unique HTML tag"
   .. }

The inputLocation argument is required and cannot be omitted.

Output Location
---------------

This sets the location of the output elements of a Single Cell, which includes
the session output, the computation ID, and server messages::

   { ..
   outputLocation: "jQuery selector, must map to a unique HTML tag"
   .. }

If ``outputLocation`` is not specified, it defaults to the same selector as
``inputLocation``.

Code Editor
-----------

This sets the type of code editor::

   { ..
   editor: "editor type"
   .. }

Available options are:

* ``codemirror`` - default, CodeMirror editor, which provides syntax
  highlighting and other more advanced functionality

* ``codemirror-readonly`` - like ``codemirror``, but not editable

* ``textarea`` - plain textbox

* ``textarea-readonly`` - like ``textarea``, but not editable

Note that Single Cell editor toggling functionality only switches between the
group of editors that are editable or static. For instance, ``textarea-readonly``
can only become ``codemirror-readonly``, rather than ``textarea`` or
``codemirror``.

This sets the initial content of the code editor::

   { ..
   code: "code"
   .. }


Code editor content can also be set by embedding the code within the input
location of the Single Cell::

   <div id="myInputDiv">
      <script type="text/code">print "Here's some code!"
   print "Hello World"
      </script>
   </div>

Note that all whitespace is preserved inside of the ``<script>``
tags.  Since the Python/Sage language is whitespace-sensitive, make
sure to not indent any lines unless you really want the indentation in
the code.

.. todo::  

  strip off the first blank line and any beginning
  whitespace, so that people can easily paste in blocks of code and
  have it work nicely.

If the code parameter is not set, the input location is examined for code.
If no code is found there, the javascript attempts to restore in the editor
whatever the user had in that particular cell before (using the web browser's
session storage capabilities). If that fails, the editor is initialized to an
empty string.

Evaluate button text
--------------------

This sets the text of the evaluate button::

   { ..
   evalButtonText: "text"
   .. }

Sage Mode
---------

This sets whether the Single Cell can evaluate Sage-specific code::

   { ..
   sageMode: boolean
   .. }

Managing subsequent sessions
----------------------------

This sets whether subsequent session output (future Single Cell evaluations)
should replace or be displayed alongside current session output::

   { ..
   replaceOutput: boolean
   .. }

Hiding Single Cell elements
---------------------------

This hides specified parts of the Single Cell using CSS ``display: none``::

   { ..
   hide: ["element_1", ... , "element_n"]
   .. }


The following input elements can be hidden:

* Editor (``editor``)
* Editor type toggle (``editorToggle``)
* Evaluate button (``evalButton``)
* Sage Mode toggle (``sageMode``)

The following output elements can be hidden:

* Computation ID logging (``computationID``)
* Message logging (``messages``)
* Session output (``output``)

.. todo:: make the Session identifiers on an output cell be hidden.
   Also, it might be nice to make a more user-friendly way of saying
   that a session is done, maybe by changing the background color or
   letting the page author pass in a CSS "style" or maybe a class?

.. _Templates:

Templates
---------

Templates provide an alternative way to set certain Single Cell properties and
are designed to simplify the process of embedding multiple instances on the
same page. A template is a javascript dictionary with key/value pairs
corresponding to desired key/value pairs given to
``singlecell.makeSinglecell()``.

Within ``singlecell.makeSinglecell()``, a template can be applied with the
following::
  
   { ..
   template: {template}
   .. }

The following options can be specified within a template dictionary (see the
documentation for :ref:`customization <Customization>` for full syntax
information, as these options mirror what can be given to
``singlecell.makeSinglecell()``).

* Hiding Single Cell elements::

   { ..
   hide: ["element_1", .. , "element_n"]
   .. }

* Editor type::

   { ..
   editor: "editor type"
   .. }

* Evaluate button text::

   { ..
   evalButtonText: "text"
   .. }

* "Sage Mode"::

   { ..
   sageMode: boolean
   .. }

* Replacing or appending subsequent sessions::

   { ..
   replaceOutput: boolean
   .. }

There are two built-in templates in ``singlecell.templates`` which are
designed for common embedding scenarios:

* ``singlecell.templates.minimal``: Prevents editing and display of embedded
  code, but displays output of that code when the Evaluate button is clicked.
  Only one output cell is shown at a time (subsequent output replaces previous
  output)::

    {
      "editor": "textarea-readonly",
      "hide": ["computationID","editor","editorToggle","files","messages","sageMode"],
      "replaceOutput": true
     }

* ``singlecell.templates.restricted``: Displays code that cannot be edited
  and displays output of that code when the Evaluate button is clicked. Only
  one output cell is shown at a time (subsequent output replaces previous
  output)::

     {
       "editor": "codemirror-readonly",
       "hide": ["computationID","editorToggle","files","messages","sageMode"],
       "replaceOutput": true
     }

Explicit options given to ``singlecell.makeSinglecell()`` override options
described in a template dictionary, with the exception of ``hide``, in which
case both the explicit and template options are combined.


Module Initialization
^^^^^^^^^^^^^^^^^^^^^

The embed javascript is initialized with ``singlecell.init()``, which can take a
callback function as its argument that is executed after all required external
libraries are loaded.

This allows for chaining the process of embedding initialization and creating
Single Cell instances::

  $(function() { // load only when the page is loaded
    var makecells = function() {
      singlecell.makeSinglecell({
        inputLocation: "#firstInput",
	outputLocation: "#firstOutput",
	template: singlecell.templates.restricted});
      singlecell.makeSinglecell({
        inputLocation: "#secondInput",
	outputLocation: "#secondOutput",
	template: singlecell.templates.minimal,
	evalButtonText: "Show Result"});
    }

    singlecell.init(makecells); // load Single Cell libraries and then
                                // initialize two Single Cell instances

  });


Embedding Javascript Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Embedding creates a global javascript object named ``singlecell``.

Accessible Methods and Variables
--------------------------------

.. _singlecell.templates_embed:
.. attribute:: singlecell.templates

   Built-in embedding templates. See :ref:`templates <Templates>` for more
   information.

.. _singlecell.init_embed:
.. function:: singlecell.init(callback)

   Initializes Single Cell embedding capabilities and loads external CSS and
   Javascript libraries.

   :param Function callback: Callback function to be executed after all external
     libraries have loaded.

.. _singlecell.makeSinglecell:
.. function:: singlecell.makeSinglecell(args)

   Constructs a Single Cell instance. This function itself mainly interprets
   configuration information; the majority of the actual rendering is done by
   :ref:`singlecell.initCell() <singlecell.initCell>`.

   :param Dict args: Dictionary containing Single Cell configuration information.
      See :ref:`customization <Customization>` for more information.
   :returns: Dictionary of Single Cell information used by other methods.

.. _singlecell.deleteSinglecell:
.. function:: singlecell.deleteSinglecell(singlecellinfo)

   Deletes a Single Cell instance.

   :param Dict singlecell info: Dictionary of Single Cell information returned by
      :ref:`singlecell.makeSinglecell() <singlecell.makeSinglecell>`.

.. _singlecell.moveInputForm:
.. function:: singlecell.moveInputForm(singlecellinfo)

   Moves form elements of a Single Cell instance outside of that instance's
   embedding context (most useful in cases where a Single Cell is embedded
   within an external form which, on submission, should not send Single Cell
   content).

   :param Dict singlecellinfo: Dictionary of Single Cell information returned by
      :ref:`singlecell.makeSinglecell() <singlecell.makeSinglecell>`.

.. _singlecell.restoreInputForm:
.. function:: singlecell.restoreInputForm(singlecellinfo)

   Restores the Single Cell form elements moved using
   :ref:`singlecell.moveInputForm() <singlecell.moveInputForm>` to the Single
   Cell instance's embedding context.

   :param Dict singlecellinfo: Dictionary of Single Cell information returned by
      :ref:`singlecell.makeSinglecell() <singlecell.makeSinglecell>`.

Internal Methods
----------------

.. _singlecell.initCell:
.. function:: singlecell.initCell(singlecellinfo)

  Called by :ref:`singlecell.makeSinglecell() <singlecell.makeSinglecell>`.
  Renders a Single Cell instance.

  :param Dict singlecellinfo: Dictionary of Single Cell configuration
    information created by
    :ref:`singlecell.makeSinglecell() <singlecell.makeSinglecell>`.

.. _singlecell.renderEditor:
.. function:: singlecell.renderEditor(editor, inputLocation)

   Called by :ref:`singlecell.initCell() <singlecell.initCell>` Renders the
   code editor for a Single Cell instance.

   :param String editor: Name of editor to be rendered
   :param inputLocation: jQuery selector corresponding to the location for Single
      Cell input (where the editor should be created).
   :returns: ``[editor, editorData]`` where ``editor`` is the name of the
      rendered editor and ``editorData`` is additional data required to later
      modify the rendered editor.

.. _singlecell.toggleEditor:
.. function:: singlecell.toggleEditor(editor, editorData, inputLocation)

   Switches the editor type (triggered upon clicking the Editor toggle link in a
   Single Cell instance).

   :param String editor: Name of current editor type.
   :param editorData: Data required to modify the current editor type, as
      returned by :ref:`singlecell.renderEditor() <singlecell.renderEditor>`.
   :param inputLocation: jQuery selector corresponding to the location for Single
      Cell input (where the editor is located).


Example
^^^^^^^

This is a very simple embedded cell with most things turned off and a default
piece of code (replace ``<SERVER>`` with the appropriate address)::

    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
    <html>
      <head>
        <meta http-equiv="Content-type" content="text/html;charset=UTF-8">
        <meta name="viewport" content="width=device-width">
        <title>Simple Compute Server</title>
        <script type="text/javascript" src="http://localhost:8080/static/jquery-1.5.min.js"></script>
        <script type="text/javascript" src="http://localhost:8080/embedded_singlecell.js"></script>

        <script>
    $(function() {
        var makecells = function() {
            singlecell.makeSinglecell({
                inputLocation: '#mysingle',
                hide: ['messages', 'computationID', 'files', 'sageMode', 'editor'],
                evalButtonText: 'Make Live'});
        }
        singlecell.init(makecells);
    })</script>

     </head>
      <body>
        <div id="mysingle"><script type="text/code">
    @interact
    def _(a=(1,10)):
          print factorial(a)
    </script></div>
      </body>
    </html>

