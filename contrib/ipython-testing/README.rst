.. highlight:: bash

This is a Sage computation web service.

Installation
============

The easiest way to install the Sage Cell server is to install the
experimental spkg for Sage.

#. Install Sage 5.0 (tested on 5.0 beta 12)
#. Install the new Sage Notebook (instructions at `Trac 11080 <http://trac.sagemath.org/sage_trac/ticket/11080>`_)
#. Install the `spkg <http://sage.math.washington.edu/home/jason/sagecell-0.9.0.spkg>`_::

    sage -i http://sage.math.washington.edu/home/jason/sagecell-0.9.0.spkg

Then open up two terminals.  In the first, launch the webserver::

    cd $SAGE_ROOT/devel/sagecell
    sage ./start_web.py

In the second terminal, launch the worker processes::

    cd $SAGE_ROOT/devel/sagecell
    sage ./start_device.py

Open your browser to http://localhost:8080/ and have fun!

You can update your codebase to the latest cutting-edge version by
doing::

    cd $SAGE_ROOT/devel/sagecell
    git pull

The biggest potential troublesome spot in the installation is that it
has to apply two patches to Sage using queues.  If you have
uncommitted changes, or if you have conflicts, the installation will
proceed, but you may have problems.

The default configuration is not secure, so you'll need to do more
work to harden the system to open it up to outside users.  But at
least that should get you up and running for a personal/development
server.  See the :doc:`Advanced Installation <advanced_installation>`
guide for more details about setting up a server outside of a Sage
directory and making your server more secure and scalable.


License
=======

See the :download:`LICENSE.txt <../LICENSE.txt>` file for terms and conditions for usage and a
DISCLAIMER OF ALL WARRANTIES.

Browser Compatibility
=====================

The Sage Cell Server is designed to be compatible with recent versions of:

* Google Chrome
* Firefox
* Safari
* Opera
* Internet Explorer (8+)

If you notice issues with any of these browsers, please let us know.

