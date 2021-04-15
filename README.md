This is SageMathCell - a Sage computation web service.

Our mailing list is https://groups.google.com/forum/#!forum/sage-cell

# Security Warning

If you are going to run a world accessible SageMathCell server, you must understand security implications and should be able to implement reasonable precautions.

The worker account (which is your own one by default) will be able to execute arbitrary code, which may be malicious. Make **sure** that you are securing the account properly. Working with a professional IT person is a very good idea here. Since the untrusted accounts can be on any computer, one way to isolate these accounts is to host them in a virtual machine that can be reset if the machine is compromised.


# Simple Installation

We assume that you have access to the Internet and can install any needed dependencies. If you need to know more precisely what tools are needed, please consult the scripts for building virtual machine images in [contrib/vm](contrib/vm).
In particular, system packages installed in the base container are listed [here](https://github.com/sagemath/sagecell/blob/master/contrib/vm/container_manager.py#L58).


1.  Install requirejs:

    ```bash
    sudo apt-get install npm
    # On Debian based systems we need to make an alias
    sudo ln -s /usr/bin/nodejs /usr/bin/node
    sudo npm install -g requirejs
    ```

2.  Get and build Sage (`export MAKE="make -j8"` or something similar can speed things up):

    ```bash
    git clone https://github.com/sagemath/sage.git
    pushd sage
    ./bootstrap
    ./configure --enable-download-from-upstream-url
    # read messages at the end, follow instructions given there.
    # possibly install more system packages (using apt-get, if on Debian/Ubuntu)
    make
    popd
    ```

3.  Prepare Sage for SageMathCell:

    ```bash
    sage/sage -pip install lockfile
    sage/sage -pip install paramiko
    sage/sage -pip install sockjs-tornado
    sage/sage -pip install sqlalchemy
    ```

4.  Build SageMathCell:

    ```bash
    git clone https://github.com/sagemath/sagecell.git
    pushd sagecell
    git submodule update --init --recursive
    ../sage/sage -sh -c make
    ```
    
Major JavaScript dependencies, including Require.js and CodeMirror.js, are [copied](https://github.com/sagemath/sagecell/blob/master/Makefile#L23) from the [Jupyter notebook](https://github.com/jupyter/notebook) bundled with SageMath.


# Configuration

1.  Go into the `sagecell` directory (you are there in the end of the above instructions).
2.  Copy `config_default.py` to `config.py`. (Or fill `config.py` only with entries that you wish to change from default values.)
3.  Edit `config.py` according to your needs. Of particular interest are `host` and `username` entries of the `provider_info` dictionary: you should be able to SSH to `username@host` *without typing in a password*. For example, by default, it assumes you can do `ssh localhost` without typing in a password. Unless you are running a private and **firewalled** server for youself, you’ll want to change this to a more restrictive account; otherwise **anyone will be able to execute any code under your username**. You can set up a passwordless account using SSH: type “ssh passwordless login” into Google to find lots of guides for doing this, like http://www.debian-administration.org/articles/152. You may also wish to adjust `db_config["uri"]` (make the database files readable *only* by the trusted account).
4.  You may want to adjust `log.py` to suit your needs and/or adjust system configuration. By default logging is done via syslog which handles multiple processes better than plain files.
5.  Start the server via

    ```bash
    ../sage/sage web_server.py [-p <PORT_NUMBER>]
    ```

    where the default `<PORT_NUMBER>` is `8888` and go to `http://localhost:<PORT_NUMBER>` to use the Sage Cell server.

    When you want to shut down the server, press `Ctrl-C` in the same terminal.


# License

See the [LICENSE.txt](LICENSE.txt) file for terms and conditions for usage and a
DISCLAIMER OF ALL WARRANTIES.

# Browser Compatibility

SageMathCell is designed to be compatible with recent versions of:

* Chrome
* Firefox
* Internet Explorer
* Opera
* Safari

If you notice issues with any of these browsers, please let us know.
