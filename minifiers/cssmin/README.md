# `cssmin`

This is a Python port of the [YUI CSS Compressor][yuicompressor]. Install it:

  [yuicompressor]: http://developer.yahoo.com/yui/compressor/

    $ easy_install cssmin # OR
    $ pip install cssmin

Use it from the command-line:

    $ cssmin --help
    $ cat file1.css file2.css file3.css | cssmin > output.min.css
    $ cssmin --wrap 1000 < input.css > output.css

Or use it from Python:

    >>> import cssmin
    >>> output = cssmin.cssmin(open('input.css').read())
    >>> print output
