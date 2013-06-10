.. highlight:: bash

This is a Sage computation web service.

Installation
============

1. Make sure you have git; if you're on Ubuntu, you’ll also need the UUID dev package for ØMQ (`uuid-dev` on Ubuntu, `libuuid-devel` on Redhat).
2. Compile Sage 5.10.rc1 (download it from http://www.sagemath.org/download-latest.html).
3. Delete the IPython installation in Sage: go to ``SAGE_ROOT/local/lib/python/site-packages/`` and delete the IPython directory and the ipython egg.
4. Install ipython past commit ipython/ipython@0d4706f74b5b454c0a54026547a286caa786e6a4.  For example, you can do this::

    sage -sh -c "easy_install https://github.com/ipython/ipython/archive/0d4706f.zip"

5. Install the latest sagecell spkg at http://sage.math.washington.edu/home/jason/sagecell-spkg/ (replace ``<filename>`` below with the name of the current spkg)::

    sage -i http://sage.math.washington.edu/home/jason/sagecell-spkg/<filename>.spkg


To start up, go into the ``$SAGE_ROOT/devel/sagecell`` directory and do:

1. Copy the ``config_default.py`` file to ``config.py`` and edit the ``sage`` variable and username/host variables. In particular, the host and username variables should point to an SSH account that you can log into *without* typing in a password. For example, by default, it assumes you can do ``ssh localhost`` without typing in a password. You’ll want to change this to a more restrictive account; otherwise anyone will be able to execute any code under your username. You can set up a passwordless account using SSH: type “ssh passwordless login” into Google to find lots of guides for doing this, like http://www.debian-administration.org/articles/152.
2. ``../../sage -sh -c "make -B"`` (We run it inside of ``sage -sh`` so that make can find the root Sage directory for various IPython files it needs. If Sage is in your ``$PATH``, you can run it normally.)
3. ``../../sage web_server.py``

The biggest potential troublesome spot in the installation is that the
spkg has to apply two patches to Sage.  If you have uncommitted
changes, or if you have conflicts, the installation will stop.

The default configuration is not secure, so you'll need to do more
work to harden the system to open it up to outside users.  But at
least that should get you up and running for a personal/development
server.

See the :doc:`Advanced Installation <advanced_installation>`
guide for more details about configuring and running a server.

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
* Internet Explorer (9+)

If you notice issues with any of these browsers, please let us know.

