.. _embedding:

Embedding Sage Cells
====================

You can embed multiple customized Sage cells in
arbitrary webpages. Customizable options include location of input and
output and functionality shown to the user.

Example
-------

This is a very simple HTML page showing how to embed two cells with
most things turned off and a default piece of code (you can replace
``sagecell.sagemath.org`` with a different SageMathCell server, if you
like):

.. code-block:: html

   <!DOCTYPE HTML>
   <html>
     <head>
       <meta charset="utf-8">
       <meta name="viewport" content="width=device-width">
       <title>SageMathCell</title>
       <script src="https://sagecell.sagemath.org/static/embedded_sagecell.js"></script>
       <script>
       // Make the div with id 'mycell' a Sage cell
       sagecell.makeSagecell({inputLocation:  '#mycell',
                              template:       sagecell.templates.minimal,
                              evalButtonText: 'Activate'});
       // Make *any* div with class 'compute' a Sage cell
       sagecell.makeSagecell({inputLocation: 'div.compute',
                              evalButtonText: 'Evaluate'});
       </script>
     </head>
     <body>
     <h1>Embedded Sage Cells</h1>

     <h2>Factorial</h2>
     Click the &ldquo;Activate&rdquo; button below to calculate factorials.
       <div id="mycell"><script type="text/x-sage">
   @interact
   def _(a=(1, 10)):
       print factorial(a)
    </script>
   </div>

   <h2>Your own computations</h2>
   Type your own Sage computation below and click &ldquo;Evaluate&rdquo;.
       <div class="compute"><script type="text/x-sage">plot(sin(x), (x, 0, 2*pi))</script></div>
       <div class="compute"><script type="text/x-sage">
   @interact
   def f(n=(0,10)):
       print 2^n
   </script></div>
     </body>
   </html>


Basic Usage
-----------

The following line should be inserted into ``<head>``:

.. code-block:: html

   <script src="https://<server>/static/embedded_sagecell.js"></script>

where ``<server>`` is the root url of a SageMathCell server. This downloads
additional required JavaScript and CSS libraries and creates a global JavaScript
object called ``sagecell``. Use :ref:`sagecell.init() <sagecell.init_embed>`
for more configuration options upon initialization, including callback functionality.

Later, the following JavaScript should be run:

.. code-block:: javascript

   sagecell.makeSagecell({inputLocation: "[jQuery selector]"});

This creates basic Sage cells at the locations matching
``inputLocation``. See the
documentation for :ref:`sagecell.makeSagecell()
<sagecell.makeSagecell>` for more configuration options. This function
returns an object containing information necessary to later move
portions of or remove the entirety of the Sage cell if
desired.

``sagecell.makeSagecell()`` can be called multiple times to embed multiple
Sage cells, as long as the input (and output, if specified) locations
of each call are unique to the page.

To remove a Sage cell, the following JavaScript can be used:

.. code-block:: javascript

   sagecell.deleteSagecell(sagecellInfo);

where ``sagecellInfo`` is the object returned upon that Sage cell creation by
``sagecell.makeSagecell()``.

Sage cells can be safely embedded within HTML forms (even though each
cell contains form elements) since those form elements are copied to a
hidden form outside of the embedded context. However, in such a case, it may
not be optimal for external form submission to include cell elements. To
prevent this issue, the following JavaScript can be used before and after form
submission to move and restore the Sage cell:

.. code-block:: javascript

   sagecell.moveInputForm(sagecellInfo); // before submission
   sagecell.restoreInputForm(sagecellInfo); // after submission

where ``sagecellInfo`` is the object returned upon that Sage cell creation by
``sagecell.makeSagecell()``.

.. _Customization:

Customization
-------------

All customization occurs through ``sagecell.makeSagecell()``, which takes a
dictionary as its argument. The key/value pairs of this dictionary serve as the
configuration of the created Sage cell. The following options can be
set when embedding:

Input Location
^^^^^^^^^^^^^^

This sets the location of the input elements of a Sage cell, which includes
the editor, mode selector, and the evaluate button:

.. code-block:: javascript

   { ..
   inputLocation: "#..."
   .. }

The ``inputLocation`` argument (required) should be a
`jQuery selector <http://api.jquery.com/category/selectors/>`_ (which
may actually return more than one DOM element --- each one will be made
into a Sage cell). If a DOM node is a textarea, the textarea will be used
as the basis for the code input box (this can be helpful if you are
trying to make an existing form textarea a live Sage cell).

Output Location
^^^^^^^^^^^^^^^

This sets the location of the output elements of a Sage cell, which includes
the session output and server messages:

.. code-block:: javascript

   { ..
   outputLocation: "#..."
   .. }

The ``outputLocation`` argument should be a
`jQuery selector <http://api.jquery.com/category/selectors/>`_
for a single DOM node. If ``outputLocation`` is not specified,
it defaults to the same selector as ``inputLocation``.

Code Editor
^^^^^^^^^^^

This sets the type of code editor:

.. code-block:: javascript

   { ..
   editor: "editor type"
   .. }

Available options are:

* ``codemirror`` - default, CodeMirror editor, which provides syntax
  highlighting and other more advanced functionality

* ``codemirror-readonly`` - like ``codemirror``, but not editable

* ``textarea`` - plain textbox

* ``textarea-readonly`` - like ``textarea``, but not editable

Default code
^^^^^^^^^^^^

This sets the initial content of the code editor:

.. code-block:: javascript

   { ..
   code: "code"
   .. }

The value of the ``code`` argument should be a string of Python/Sage
code.

Code editor content can also be set using the ``codeLocation`` argument:

.. code-block:: javascript

   { ..
   codeLocation: "#..."
   .. }

The ``codeLocation`` argument should be a
`jQuery selector <http://api.jquery.com/category/selectors/>`_
for a single DOM node. This node should be a ``SCRIPT`` element
of type ``text/x-sage`` containing the default Python/Sage code:

.. code-block:: html

       <script type="text/x-sage" id="mycode">
   print("Here's some code!")
   print("Hello World")
       </script>

Note that all whitespace is preserved inside of the ``<script>``
tags.  Since the Python/Sage language is whitespace-sensitive, make
sure to not indent any lines unless you really want the indentation in
the code.

.. todo::  

  strip off the first blank line and any beginning
  whitespace, so that people can easily paste in blocks of code and
  have it work nicely.

If the code parameter is not set, the code location is examined for code.
If no code is found there, the JavaScript attempts to restore in the editor
whatever the user had in that particular cell before (using the web browser's
session storage capabilities). If that fails, the editor is initialized to an
empty string.

Linked Cells
^^^^^^^^^^^^

When multiple input locations are given, this sets whether the code from these
cells is to be executed from the same kernel, so that code executed in one
will affect the execution of code from another cell:

.. code-block:: javascript

   { ..
   linked: boolean
   .. }

This option is ``false`` by default.

Evaluate button text
^^^^^^^^^^^^^^^^^^^^

This sets the text of the evaluate button:

.. code-block:: javascript

   { ..
   evalButtonText: "text"
   .. }

Languages
^^^^^^^^^

This sets the list of languages that can be evaluated in the Sage cell:

.. code-block:: javascript

   { ..
   languages: ["sage", ...]
   .. }

Possible values in this array are ``"sage"``, ``"gap"``, ``"gp"``, ``"html"``,
``"maxima"``, ``"octave"``, ``"python"``, ``"r"``, and ``"singular"``.
If more than one language is specified in this option, a selection box will
appear to allow the user to select a language.

The default value is ``["sage"]`` (only Sage code allowed). To allow all of the
available languages, use the value ``sagecell.allLanguages`` in place of the
array.

Managing subsequent sessions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This sets whether subsequent session output (future Sage cell evaluations)
should replace or be displayed alongside current session output:

.. code-block:: javascript

   { ..
   replaceOutput: boolean
   .. }

Automatic evaluation
^^^^^^^^^^^^^^^^^^^^

This sets whether the code from the ``code`` option will be immediately evaluated,
without the need for pressing a button:

.. code-block:: javascript

   { ..
   autoeval: boolean
   .. }

.. caution::

    Please use this option sparingly, especially with ``@interact``, to
    decrease the load on servers. Unless majority of users who open your page
    are likely to use this cell, let them press a button to trigger evaluation.

Callback
^^^^^^^^

This is a function with no arguments that will be called after SageMathCell
has finished loading:

.. code-block:: javascript

   { ..
   callback: function
   .. }

Hiding Sage Cell elements
^^^^^^^^^^^^^^^^^^^^^^^^^

This hides specified parts of the Sage cell using CSS ``display: none``:

.. code-block:: javascript

   { ..
   hide: ["element_1", ... , "element_n"]
   .. }

The following input elements can be hidden:

* Editor (``editor``)
* Language selection box (``language``)
* Evaluate button (``evalButton``)

The following output elements can be hidden:

* Share button to permalinks (``permalink``)
* Session output (``output``)
* Session end message (``done``)
* Session files (``sessionFiles``)

Additionally, the following debugging elements are hidden by default:

* Message logging (``messages``)
* Session title (``sessionTitle``)

These elements can be displayed in :ref:`debug_mode`.

.. _Templates:

Templates
^^^^^^^^^

Templates provide an alternative way to set certain Sage cell properties and
are designed to simplify the process of embedding multiple cells on the
same page. A template is a JavaScript dictionary with key/value pairs
corresponding to desired key/value pairs given to
``sagecell.makeSagecell()``.

Within ``sagecell.makeSagecell()``, a template can be applied with the
following:

.. code-block:: javascript

   { ..
   template: template_name
   .. }

The following options can be specified within a template dictionary (see the
documentation for :ref:`customization <Customization>` for full syntax
information, as these options mirror what can be given to
``sagecell.makeSagecell()``).

* Hiding Sage cell elements:

.. code-block:: javascript

   { ..
   hide: ["element_1", .. , "element_n"]
   .. }

* Editor type:

.. code-block:: javascript

   { ..
   editor: "editor type"
   .. }

* Evaluate button text:

.. code-block:: javascript

   { ..
   evalButtonText: "text"
   .. }

* Language selection:

.. code-block:: javascript

   { ..
   languages: ["sage", ...]
   .. }

* Replacing or appending subsequent sessions:

.. code-block:: javascript

   { ..
   replaceOutput: boolean
   .. }

* Automatic evaluation:

.. code-block:: javascript

   { ..
   autoeval: boolean
   .. }

There are two built-in templates in ``sagecell.templates`` which are
designed for common embedding scenarios:

* ``sagecell.templates.minimal``: Prevents editing and display of
  embedded code, but displays output of that code when the Evaluate
  button is clicked.


* ``sagecell.templates.restricted``: Displays a read-only version of
  the code.

Explicit options given to ``sagecell.makeSagecell()`` override options
described in a template dictionary, with the exception of ``hide``, in which
case both the explicit and template options are combined.

.. _debug_mode:

Debug Mode
^^^^^^^^^^

A special "debug" mode is avaliable by passing the following to
``sagecell.makeSagecell()``:

.. code-block:: javascript

     { ..
       mode: "debug"
     .. }

This shows all page elements (overriding ``hide`` specification), which provides
session titles and sent / recieved message logging that are otherwise hidden by
default. Since this mode is not intended for production purposes, a browser
warning will be raised when initializing a Sage cell in debug mode.
