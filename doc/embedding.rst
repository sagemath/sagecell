.. _embedding:

Embedding Sage Cell Instances
=============================

.. default-domain:: js

Description
^^^^^^^^^^^
Provides functionality to embed multiple customized instances of the Sage Cell
in arbitrary webpages. Customizable options include location of input and output
and functionality shown to the user.

Dependencies
^^^^^^^^^^^^
jQuery: http://www.jquery.com

Basic Usage
^^^^^^^^^^^

jQuery is assumed to be loaded in ``<head>``. 
In ``<head>``, the following lines should be inserted::

   <script type="text/javascript" src="http://<server>/embedded_sagecell.js"></script>
   <script type="text/javascript">sagecell.init();</script>

where ``<server>`` is the root url of a live Sage Cell server. This downloads
additional required javascript and css libraries and creates a global javascript
object called ``sagecell``. See the documentation for
:ref:`sagecell.init() <sagecell.init_embed>` for more configuration options
upon initialization, including callback functionality.

Later, the following javascript should be run::

   sagecell.makeSagecell({inputLocation: "[jQuery selector]"});

This creates a basic Sage Cell instance at the location matching
``inputLocation``. This location must be a unique selector for an HTML element
in which content can be dynamically placed. See the documentation for
:ref:`sagecell.makeSagecell() <sagecell.makeSagecell>`
for more configuration options. This function returns a dictionary containing
information necessary to later move portions of or remove the entirety of the
Sage Cell instance if desired.

``sagecell.makeSagecell()`` can be called multiple times to embed multiple
Sage Cell instances, as long as the input (and output, if specified) locations
of each instance are unique to the page.

To remove a Sage Cell instance, the following javascript can be used::

   sagecell.deleteSagecell(sagecellInfo);

where ``sagecellInfo`` is the dictionary of information returned upon that
Sage Cell instance's creation by ``sagecell.makeSagecell()``.

Sage Cell instances can be safely embedded within HTML forms (even though each
instance contains form elements) since those form elements are copied to a
hidden form outside of the embedded context. However, in such a case, it may
not be optimal for external form submission to include Sage Cell elements. To
prevent this issue, the following javascript can be used before and after form
submission to move and restore the Sage Cell::

   sagecell.moveInputForm(sagecellInfo); // before submission
   sagecell.restoreInputForm(sagecellInfo); // after submission

where ``sagecellInfo`` is the dictionary of information returned upon that
Sage Cell instance's creation by ``sagecell.makeSagecell()``.

.. _Customization:

Customization
^^^^^^^^^^^^^

All customization occurs through ``sagecell.makeSagecell()``, which takes a
dictionary as its argument. The key/value pairs of this dictionary serve as the
configuration of the created Sage Cell instance. The following options can be
set when embedding:

Input Location
--------------

This sets the location of the input elements of a Sage Cell, which includes
the editor, editor toggle, "Sage Mode" selector, file upload selector, and the
evaluate button::

   { ..
   inputLocation: "jQuery selector, must map to a unique HTML tag"
   .. }

The inputLocation argument is required and cannot be omitted.

Output Location
---------------

This sets the location of the output elements of a Sage Cell, which includes
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

Note that Sage Cell editor toggling functionality only switches between the
group of editors that are editable or static. For instance, ``textarea-readonly``
can only become ``codemirror-readonly``, rather than ``textarea`` or
``codemirror``.

This sets the initial content of the code editor::

   { ..
   code: "code"
   .. }


Code editor content can also be set by embedding the code within the input
location of the Sage Cell::

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

This sets whether the Sage Cell can evaluate Sage-specific code::

   { ..
   sageMode: boolean
   .. }

Managing subsequent sessions
----------------------------

This sets whether subsequent session output (future Sage Cell evaluations)
should replace or be displayed alongside current session output::

   { ..
   replaceOutput: boolean
   .. }

Hiding Sage Cell elements
---------------------------

This hides specified parts of the Sage Cell using CSS ``display: none``::

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
* Session title (``sessionTitle``)
* Session end message (``done``)
* Session files label (``sessionFilesTitle``)
* Session files (``sessionFiles``)

.. todo:: make the Session identifiers on an output cell be hidden.
   Also, it might be nice to make a more user-friendly way of saying
   that a session is done, maybe by changing the background color or
   letting the page author pass in a CSS "style" or maybe a class?

.. _Templates:

Templates
---------

Templates provide an alternative way to set certain Sage Cell properties and
are designed to simplify the process of embedding multiple instances on the
same page. A template is a javascript dictionary with key/value pairs
corresponding to desired key/value pairs given to
``sagecell.makeSagecell()``.

Within ``sagecell.makeSagecell()``, a template can be applied with the
following::
  
   { ..
   template: {template}
   .. }

The following options can be specified within a template dictionary (see the
documentation for :ref:`customization <Customization>` for full syntax
information, as these options mirror what can be given to
``sagecell.makeSagecell()``).

* Hiding Sage Cell elements::

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

There are two built-in templates in ``sagecell.templates`` which are
designed for common embedding scenarios:

* ``sagecell.templates.minimal``: Prevents editing and display of embedded
  code, but displays output of that code when the Evaluate button is clicked.
  Only one output cell is shown at a time (subsequent output replaces previous
  output)::

    {
      "editor": "textarea-readonly",
      "hide": ["computationID","editor","editorToggle","files","messages","sageMode", "sessionTitle", "done", "sessionFilesTitle"],
      "replaceOutput": true
     }

* ``sagecell.templates.restricted``: Displays code that cannot be edited
  and displays output of that code when the Evaluate button is clicked. Only
  one output cell is shown at a time (subsequent output replaces previous
  output)::

     {
       "editor": "codemirror-readonly",
       "hide": ["computationID","editorToggle","files","messages","sageMode","sessionTitle","done","sessionFilesTitle"],
       "replaceOutput": true
     }

Explicit options given to ``sagecell.makeSagecell()`` override options
described in a template dictionary, with the exception of ``hide``, in which
case both the explicit and template options are combined.


Module Initialization
^^^^^^^^^^^^^^^^^^^^^

The embed javascript is initialized with ``sagecell.init()``, which can take a
callback function as its argument that is executed after all required external
libraries are loaded.

This allows for chaining the process of embedding initialization and creating
Sage Cell instances::

  $(function() { // load only when the page is loaded
    var makecells = function() {
      sagecell.makeSagecell({
        inputLocation: "#firstInput",
	outputLocation: "#firstOutput",
	template: sagecell.templates.restricted});
      sagecell.makeSagecell({
        inputLocation: "#secondInput",
	outputLocation: "#secondOutput",
	template: sagecell.templates.minimal,
	evalButtonText: "Show Result"});
    }

    sagecell.init(makecells); // load Sage Cell libraries and then
                                // initialize two Sage Cell instances

  });


Example
^^^^^^^

This is a very simple embedded cell with most things turned off and a
default piece of code (you can replace ``aleph.sagemath.org`` with a
different Sage Cell server, if you like)::

    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
    <html>
      <head>
        <meta http-equiv="Content-type" content="text/html;charset=UTF-8">
        <meta name="viewport" content="width=device-width">
        <title>Sage Cell Server</title>
        <script type="text/javascript" src="http://aleph.sagemath.org/static/jquery.min.js"></script>
        <script type="text/javascript" src="http://aleph.sagemath.org/embedded_sagecell.js"></script>

        <script>
    $(function() {
        var makecells = function() {
            sagecell.makeSagecell({
                inputLocation: '#mycell',
                template: sagecell.templates.minimal,
                evalButtonText: 'Make Live'});
        }
        sagecell.init(makecells);
    })</script>

     </head>
      <body>
        <div id="mycell"><script type="text/code">
    @interact
    def _(a=(1,10)):
          print factorial(a)
    </script></div>
      </body>
    </html>

