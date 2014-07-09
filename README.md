This is a Sage computation web service.

# Warning

Installation instructions below (as well as other variants) may be outdated. The most reliable source of build instructions at the moment is in contib/vm scripts.
    
# Simple Installation

We assume that you have access to the Internet and can install any needed dependencies (e.g. git). If you need to know more precisely what tools are needed, please consult the scripts for building virtual machine images in contrib/vm

If you are going to run a world accessible Sage Cell server, we also assume that you understand security implications and can implement reasonable precautions.

1. Make sure you have a recent enough version of git: 1.8.5 is good enough, while 1.7.9 isn't.
2. Install required npm packages:
```bash
sudo apt-get install npm
# On Debian based systems we need to make an alias
sudo ln -s /usr/bin/nodejs /usr/bin/node
sudo npm install -g inherits requirejs coffee-script
```
3. Download repositories from GitHub:
```bash
# Create a directory for building images and go there.
mkdir sc_build
cd sc_build
# Get clone_repositories, make it executable, and run it.
wget https://github.com/sagemath/sagecell/raw/master/contrib/vm/clone_repositories
chmod u+x clone_repositories
./clone_repositories
```
Note: these are the largest downloads that happen during installation, but not the only ones - you have to have Internet access during the following steps as well.
4. Build Sage (`export MAKE="make -j8"` or something similar can speed things up):
```bash
mv github/sage .
cd sage
make start
```
Note that we are building a special branch of Sage for the Cell server, do NOT use your regular Sage installation!
5. Prepare Sage for Sage Cell:
```bash
./sage -sh -c "easy_install pip"
./sage -i http://boxen.math.washington.edu/home/jason/zeromq-4.0.3.spkg
./sage -i pyzmq
# we need a more recent pyzmq than Sage provides
./sage -sh -c "pip install -U pyzmq"
# We need IPython stuff not present in spkg.
pushd local/lib/python/site-packages
rm -rf IPython*
rm -rf ipython*
popd
mv ../github/ipython .
pushd ipython
../sage setup.py develop
popd
# we need a cutting-edge matplotlib as well for the new interactive features
mv ../github/matplotlib .
pushd matplotlib
../sage setup.py install
popd
./sage -sh -c "easy_install ecdsa"
./sage -sh -c "easy_install paramiko"
./sage -sh -c "easy_install sockjs-tornado"
./sage -sh -c "easy_install lockfile"
```
6. Build Sage Cell:
```bash
mv ../github/sagecell .
cd sagecell/static
ln -s ../../local/share/jmol .
cd ..
../sage -sh -c "make -B"
```


# Configuration

1. Go into the ``sage/sagecell`` directory (you are there in the end of the above instructions).
2. Copy ``config_default.py`` to ``config.py``.
3. Edit ``config.py`` according to your needs. Of particular interest are ``host`` and ``username`` entries of the ``_default_config`` dictionary: you should be able to SSH to ``username@host`` *without typing in a password*. For example, by default, it assumes you can do ``ssh localhost`` without typing in a password. Unless you are running a private and **firewalled** server for youself, you’ll want to change this to a more restrictive account; otherwise **anyone will be able to execute any code under your username**. You can set up a passwordless account using SSH: type “ssh passwordless login” into Google to find lots of guides for doing this, like http://www.debian-administration.org/articles/152.
4. Start the server via
```bash
../sage web_server.py
```
and stop it by pressing ``Ctrl+C`` in the same terminal.

Once again: **the default configuration is not secure**, so you'll need to do more work to harden the system to open it up to outside users. But at least the above instructions should get you up and running for a personal/development server. See the [Advanced Installation](doc/advanced_installation.rst) guide for more details about configuring and running a server.

# License

See the [LICENSE.txt](LICENSE.txt) file for terms and conditions for usage and a
DISCLAIMER OF ALL WARRANTIES.

# Browser Compatibility

The Sage Cell Server is designed to be compatible with recent versions of:

* Chrome
* Firefox
* Internet Explorer
* Opera
* Safari

If you notice issues with any of these browsers, please let us know.
