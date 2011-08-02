Embedding Single Cell Instances
===============================

Description
^^^^^^^^^^^
Functionality to embed multiple customized instances of the Single Cell
in arbitrary webpages. Customizable options include display of messages,
location of input and output, and file uploads.

Dependencies
^^^^^^^^^^^^
jQuery: http://www.jquery.com

Basic Usage
^^^^^^^^^^^

* Load jQuery

jQuery is assumed to be loaded in <head> with $ available.

* Load embed javascript

In <head>, the following lines should be inserted::

    <script type="text/javascript" src="http://<server>/embedded_singlecell.js"></script>
    <script type="text/javascript">singlecell.init();</script>

where <server> is the root url of a live single cell server. This gets
the code to embed the single cell and downloads additional required
javascript and css files. It also creates a global javascript object called
singlecell.

* Initialize Single Cell instance

In <body>, the user should insert code similar to the following
(basic example)::

    <script type="text/javascript">
        singlecell.makeSinglecell();
    </script>

In this case, the page should have a <div> with an id "singlecell" in
which the single cell is rendered (default option). makeSinglecell() can
be called multiple times to embed multiple single cell instances, so
long as customization options are used to set the input and output locations
of each instance to different locations on the page. The following
section details customizable options:

Customization
^^^^^^^^^^^^^

The following options are customizable:

* Input (code / files / evaluate button) location
* Output (output / messages) location
* Showing file uploads
* Showing messages
* Showing computation ID

Options are passed to singlecell.makeSinglecell() as a dictionary with the following
form::

    {"inputDiv": jQuery selector for input location,
    "outputDiv": jQuery selector for output location,
    "code": text string to initialize the code block,
    "files": javascript boolean for showing file uploads,
    "messages": javascript boolean for showing messages,
    "computationID": javascript boolean for showing computation ID}

Parameters are optional; the default behavior of each parameter is as
follows::

    {"inputDiv": "#singlecell",
    "outputDiv": inputDiv,
    "files": true,
    "messages": true,
    "computationID": true}

If the code parameter is not set, the inputDiv is first examined for
code.  If no code is found there, the javascript attempts to restore
in the text cell whatever the user had in that particular cell
before.  If that fails, the code is initialized to an empty string.

For example, here is a very simple embedded cell with most things
turned off and a default piece of code (replace <SERVER> with the
appropriate address)::

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
                inputDiv: '#mysingle',
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

