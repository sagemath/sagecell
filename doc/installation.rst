Here is a list of installation instructions from Davi dos Santos (see https://groups.google.com/d/msg/sage-support/nxy_BFvEtPw/sCGkSNjfctAJ)

    sudo apt-get install uuid-dev # ubuntu users

    sudo apt-get install build-essential m4 gfortran perl dpkg-dev make tar

    sudo apt-get install libcurl4-openssl-dev

    sudo apt-get install python-software-properties

    sudo add-apt-repository ppa:chris-lea/node.js

    sudo apt-get update

    sudo apt-get install nodejs

    sudo apt-get install npm

    git clone https://github.com/jasongrout/sage.git

    cd sage

    git checkout origin/sagecell

    mkdir upstream

    cd upstream

    wget -O ipython-1.0.0.tar.gz https://github.com/ipython/ipython/releases/download/rel-1.0.0/ipython-1.0.0.tar.gz

    cd ..

    vi build/pkgs/ipython/checksums.ini

    tarball=ipython-1.0.0.tar.gz # the version of earlier step and remove extra spaces

    make

    ./sage -sh -c "easy_install pip"

    ./sage -i zeromq

    ./sage -i pyzmq

    ./sage -sh -c "pip install -U pyzmq"

    sudo apt-get install libcurl4-openssl-dev

    ./sage -f git

    # IPython

    pushd local/lib/python/site-packages

    rm -rf IPython*

    rm -rf ipython*

    popd

    git clone https://github.com/ipython/ipython.git

    pushd ipython

    git remote add jason https://github.com/jasongrout/ipython.git

    git fetch jason

    git checkout jason/sagecell

    ../sage setup.py develop

    popd

    ./sage -sh -c "easy_install pyparsing"

    git clone https://github.com/jasongrout/matplotlib

    pushd matplotlib

    git checkout origin/sagecell

    ../sage setup.py install

    popd

    pushd /local/lib/python2.7/site-packages

    ln -s sagenb-0.10.7.2-py2.7.egg  sagenb-0.10.4-py2.7.egg # corrigido

    popd

    npm install -g inherits requirejs coffee-script     ##installs  r.js ==required.js

    ./sage -sh -c "easy_install pyparsing"

    git clone https://github.com/jasongrout/matplotlib

    pushd matplotlib

    git checkout origin/sagecell

    ../sage setup.py install

    popd

    ./sage -i http://sage.math.washington.edu/home/jason/sagecell-spkg/sagecell-2013-08-13.spkg

    cd sagecell/

    git pull origin master

    ../sage -sh -c "make -B"

    cp config_default.py config.py

    configure user and host in config_default.py
    ../sage web_server.py -p  8889
