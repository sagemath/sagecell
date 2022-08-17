#!/usr/bin/env python3

import argparse
import datetime
import grp
import logging
import logging.config
import os
import pwd
import shlex
import shutil
import stat
import subprocess
import sys
import time

import lxc
import psutil
import yaml

number_of_compute_nodes = 3

#This will be visible on root and help pages. Suggested template:
# Resources for your computation are provided by <a href="...">...</a>.
provider_html = r"""
"""

# Container names
lxcn_base = "base"      # OS and packages
lxcn_precell = "precell"    # Everything but SageCell and system configuration
lxcn_sagecell = "sagecell"      # Sage and SageCell
lxcn_backup = "sagecell-backup"     # Saved master for restoration if necessary
lxcn_tester = "sctest"  # Accessible via special port, for testing
lxcn_prefix = "sc-"     # Prefix for main compute nodes
lxcn_version_prefix = "sage-"       # Prefix for fixed version compute nodes

# Timeout in seconds to wait for a container to shutdown, network to start etc.
timeout = 120
# Time after which SageCell should be up and running.
start_delay = 66
# How long to wait after starting new containers before destroying old ones.
deploy_delay = 2*60*60  # Two hours to allow all interacts finish "naturally".

# User names and IDs
users = {"group": "sagecell", "GID": 8888,
         "server": "sc_serv", "server_ID": 8888,
         "worker": "sc_work", "worker_ID": 9999}

# Github repositories as (user, repository, branch)
repositories = [
    ("sagemath", "sage", "master"),
    ("sagemath", "sagecell", "master"),
]

# Packages to be installed in the base container
packages = """
automake
bison
build-essential
dvipng
epstool
fig2dev
gettext
gfortran
git
gnuplot
imagemagick
ipset
iptables
libcairo2-dev
libffi-dev
libfile-slurp-perl
libisl-dev
libjson-perl
libmongodb-perl
libopenmpi3
libperl-dev
libproj-dev
libsnappy-dev
libsvg-perl
libsystemd-dev
libterm-readkey-perl
libterm-readline-gnu-perl
libxml-libxslt-perl
libxml-writer-perl
m4
nginx
ninja-build
npm
pandoc
pari-gp2c
php7.4-fpm
proj-bin
rsyslog-relp
ssh
texlive
texlive-latex-extra
tk-dev
unattended-upgrades
unzip
wget
""".split()
# Due to (other's) bugs, some packages cannot be installed during installation.
# Let's also use it to separate "standard tools" and "extra stuff".
packages_later = """
ffmpeg
graphviz
libgeos-dev
libhdf5-dev
libnetcdf-dev
libxml2-dev
libxslt1-dev
octave
octave-econometrics
octave-statistics
""".split()

# Optional Sage packages to be installed
sage_optional_packages = [
"4ti2",
"biopython",
"bliss",
"cbc",
"cryptominisat",
"database_cremona_ellcurve",
"database_jones_numfield",
"database_odlyzko_zeta",
"database_symbolic_data",
"dot2tex",  # needs graphviz
"fricas",
"gap_packages",
"gap3",
"latte_int",
"lie",  # needs bison
"lrslib",
"mcqd",
"normaliz",
"pari_elldata",
"pari_galpol",
"pari_nftables",
"pari_seadata",
"pybtex",   # needs unzip
"pynormaliz",
"qepcad",
"saclib",
"tides",
"topcom",
]

# Python packages to be installed into Sage (via pip)
python_packages = [
# Dependencies of SageMathCell
"lockfile",
"paramiko",
"psutil",
"sockjs-tornado",
"git+https://github.com/systemd/python-systemd.git",
# Optional
"future",   # fipy does not work without it installed first
"admcycles",
"APMonitor",
"astropy",
"astroquery",
"autoviz",
"bioinfokit",
"bitarray",
"bokeh",
"calplot",
"cartopy==0.19.0.post1", # Compatibility issues as of January 2022
"chart_studio",
"colorlog",
"covid-daily",
"cramjam",
"cufflinks",
"dash",
"dask[array]",
"emoji",
"geopandas",
#"geoplot", does not build even with libgdal-dev as of May 2022
"getdist",
"ggplot",
"gif",
#"giotto-tda", asks sudo access as of May 2022
"google-api-python-client",
"graphviz",
"gspread",
"fipy",
"folium",
"healpy",
"h5py",
"husl",
"itikz",
"july",
"keras",
"keyring",
"koboextractor",
"lenstools",
"lhsmdu",
"lxml",
"manimlib",
"mapclassify",
"mathchem",
"mpi4py",
"msedge-selenium-tools",
"munkres",
"nbodykit",
"nest_asyncio",
"netcdf4",
"nltk",
"numexpr",
"oauth2client",
"oct2py",
"openpyxl",
"pandas",
"pandas-profiling",
"patsy",
"plotly",
"pretty_html_table",
"pydot",
"pyforest",
"pygnuplot",
"PyPDF4",
"pyproj",
"pyswarms",
"python-snappy",
"python-ternary",
"pyvo",
"requests",
"scikit-image",
"scikit-learn",
"scikit-tda",
"scimath==4.2.0",  # 5.0.0 does not install as of August 2022
"scrapy",
"seaborn",
"selenium",
"Shapely",
"SimPy",
"snappy",
"spacy",
"SpeechRecognition",
"spiceypy",
"statsmodels",
"surface_dynamics",
"sweetviz",
"tables",
"tbcontrol",
"theano",
"tikzplotlib",
"torch",
"transformers",
"tweepy",
"twint",
"WeasyPrint",
"wordcloud",
"xarray",
"xlrd",
"moss", # This one only complains about missing dependencies
]

# R packages
R_packages = [
"deSolve",
"GGally",
"ggplot2",
"pracma",
"rms",
"survey",
"swirl",
"tidyverse",
]

# limits configuration for the host - will not be overwritten later
limits_conf = """\
* - nofile 32768
root - nofile 32768
"""


# rsyslog configuration for the host - will not be overwritten later
rsyslog_conf = r"""global(maxMessageSize="64k")

module(load="imrelp")
input(type="imrelp" port="12514")

template(name="sagecell" type="list") {
    property(name="hostname")
    constant(value=" ")
    property(name="syslogtag")
    property(name="msg" spifno1stsp="on")
    property(name="msg" droplastlf="on")
    constant(value="\n")
    }

if $syslogfacility-text == "local3" then
    {
    action(type="omfile"
           file="/var/log/sagecell.stats.log"
           template="sagecell")
    stop
    }
"""


# HA-Proxy configuration is regenerated every time the script is run.
HAProxy_header = """\
# Default from Ubuntu 20.04 LTS
global
        log /dev/log    local0
        log /dev/log    local1 notice
        chroot /var/lib/haproxy
        stats socket /run/haproxy/admin.sock mode 660 level admin expose-fd listeners
        stats timeout 30s
        user haproxy
        group haproxy
        daemon

        # Default SSL material locations
        ca-base /etc/ssl/certs
        crt-base /etc/ssl/private

        # See: https://ssl-config.mozilla.org/#server=haproxy&server-version=2.0.3&config=intermediate
        ssl-default-bind-ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384
        ssl-default-bind-ciphersuites TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256
        ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets

defaults
        log     global
        mode    http
        option  httplog
        option  dontlognull
        timeout connect 5000
        timeout client  50000
        timeout server  50000
        errorfile 400 /etc/haproxy/errors/400.http
        errorfile 403 /etc/haproxy/errors/403.http
        errorfile 408 /etc/haproxy/errors/408.http
        errorfile 500 /etc/haproxy/errors/500.http
        errorfile 502 /etc/haproxy/errors/502.http
        errorfile 503 /etc/haproxy/errors/503.http
        errorfile 504 /etc/haproxy/errors/504.http

# SageMathCell additions
        option http-server-close
        option redispatch
        timeout client-fin 50s
        timeout tunnel 2h
"""

# {suffix} {port} {hostname} {peer_port} have to be set once
# lines with {node} and {id} should be repeated for each server
HAProxy_section = r"""
frontend http{suffix}
    bind *:{port}
    reqrep ^([^\ \t]*[\ \t])(/embedded_sagecell\.js[\ \t].*)     \1/static\2
    use_backend static{suffix} if { path_beg /static }
    use_backend compute{suffix}
    monitor-uri /?healthcheck
    monitor fail if { nbsrv(compute{suffix}) lt 1 }

peers local{suffix}
    peer {hostname} localhost:{peer_port}

backend static{suffix}
    server {node} {ip}:8889 id {id} check

backend compute{suffix}
    stick-table type string len 36 size 1m expire 2h peers local{suffix}
    stick on urlp(CellSessionID)
    stick match req.hdr(Jupyter-Kernel-ID)
    stick store-response res.hdr(Jupyter-Kernel-ID)
    stick match path bytes(8,36) if { path_reg ^/kernel/.{36}/ }
    option httpchk

    server {node} {ip}:8888 id {id} check
"""

HAProxy_stats = """
listen stats
    bind *:9999
    stats enable
    stats refresh 5s
    stats uri /
    stats show-legends
"""


def call(command):
    command = command.format_map(users)
    log.debug("executing %s", command)
    return subprocess.call(shlex.split(command))


def check_call(command):
    command = command.format_map(users)
    log.debug("executing %s", command)
    subprocess.check_call(shlex.split(command))


def check_output(command):
    command = command.format_map(users)
    log.debug("executing %s", command)
    return subprocess.check_output(shlex.split(command),
                                   universal_newlines=True)


def communicate(command, message):
    command = command.format_map(users)
    log.debug("sending %s to %s", message, command)
    with subprocess.Popen(shlex.split(command),
                          stdin=subprocess.PIPE,
                          universal_newlines=True) as p:
        p.communicate(message)
        if p.returncode != 0:
            msg = "{} failed".format(command)
            log.error(msg)
            raise RuntimeError(msg)
            

def install_macaulay2():
    r"""
    Adjust system configuration and install Macaulay2.
    """
    with open("/etc/apt/sources.list.d/macaulay2.list", "w") as f:
        f.write("deb https://faculty.math.illinois.edu/Macaulay2/Repositories/Ubuntu focal main")
    check_call("apt-key adv --keyserver hkp://keyserver.ubuntu.com \
                --recv-key CD9C0E09B0C780943A1AD85553F8BD99F40DCB31")
    check_call("apt update")
    check_call("apt install -y macaulay2")


def timer_delay(delay, test=None):
    r"""
    Wait with a countdown timer.

    ``delay`` is either a timedelta or the number of seconds.
    
    ``test`` is either ``None`` (default) or callable, in which case the timer
    stops as soon as ``False`` is returned.
    """
    if isinstance(delay, datetime.timedelta):
        delay = delay.total_seconds()
    now = time.time()
    end = now + delay
    while now < end and (test is None or test()):
        remaining = datetime.timedelta(seconds=int(end - now))
        sys.stdout.write("  Please wait {} ...\r".format(remaining))
        sys.stdout.flush()
        time.sleep(1)
        now = time.time()


def update_repositories():
    r"""
    Clone/update repositories and checkout appropriate branches.
    """
    if not os.path.exists("github"):
        os.mkdir("github")
    os.chdir("github")
    git = lambda command: check_call("git " + command)
    for user, repository, branch in repositories:
        log.info("updating repository %s", repository)
        if not os.path.exists(repository):
            git("clone https://github.com/{}/{}.git".format(user, repository))
        os.chdir(repository)
        git("fetch")
        git("checkout " + branch)
        if call("git symbolic-ref -q HEAD") == 0:
            git("pull")
        os.chdir(os.pardir)
    os.chdir(os.pardir)


def create_host_users():
    r"""
    Create host users if necessary.

    If users exist (from previous runs), check that they are as expected.
    """
    log.info("creating users on the host")
    try:
        check_call("addgroup --gid {GID} {group}")
        check_call("adduser --uid {server_ID} --ingroup {group} --gecos '' "
                   "--disabled-password --no-create-home {server}")
        check_call("adduser --uid {worker_ID} --ingroup {group} --gecos '' "
                   "--disabled-password --no-create-home {worker}")
    except subprocess.CalledProcessError:
        try:
            g = grp.getgrnam(users["group"])
            s = pwd.getpwnam(users["server"])
            w = pwd.getpwnam(users["worker"])
            if g.gr_gid != users["GID"] or \
               s.pw_uid != users["server_ID"] or s.pw_gid != users["GID"] or \
               w.pw_uid != users["worker_ID"] or w.pw_gid != users["GID"]:
                raise KeyError
        except KeyError:
            raise RuntimeError("failed to create accounts on host")


def setup_container_users():
    r"""
    Create container users and setup SSH access.
    """
    log.info("setting up users in the containter")
    check_call("addgroup --gid {GID} {group}")
    check_call("adduser --uid {server_ID} --ingroup {group} --gecos '' "
               "--disabled-password {server}")
    check_call("adduser --uid {worker_ID} --ingroup {group} --gecos '' "
               "--disabled-password {worker}")

    shome = os.path.join("/home", users["server"])
    whome = os.path.join("/home", users["worker"])
    os.chdir(shome)
    os.setegid(users["GID"])
    os.seteuid(users["server_ID"])
    os.mkdir(".ssh", 0o700)
    check_call("ssh-keygen -q -N '' -f .ssh/id_rsa")

    os.chdir(whome)
    os.setuid(0)
    os.seteuid(users["worker_ID"])
    os.mkdir(".cache", 0o700)
    os.mkdir(".sage")
    os.mkdir(".ssh", 0o700)
    files_to_lock = [
        ".cache/pip",
        ".sage/local",
        ".ssh",
        ".bash_logout",
        ".bash_profile",
        ".bashrc",
        ".profile",
        ]
    check_call(" ".join(["touch"] + files_to_lock))
    os.setuid(0)
    shutil.copy2(os.path.join(shome, ".ssh/id_rsa.pub"),
                 ".ssh/authorized_keys")
    os.chown(".ssh/authorized_keys", users["worker_ID"], users["GID"])
    # Get the localhost in the known_hosts file.
    check_call("su -l {server} -c "
               "'ssh -q -oStrictHostKeyChecking=no {worker}@localhost whoami'")
    for f in files_to_lock:
        check_call("chattr -R +i " + f)


def become_server():
    r"""
    Adjust UID etc. to have files created as the server user.
    """
    os.setgid(users["GID"])
    os.setuid(users["server_ID"])
    os.environ["HOME"] = os.path.join("/home", users["server"])
    os.chdir(os.environ["HOME"])
    os.environ.setdefault("MAKE", "make -j{}".format(os.cpu_count()))


def install_sage():
    r"""
    Install Sage.
    """
    become_server()
    shutil.move("github/sage", ".")
    os.chdir("sage")
    log.info("compiling Sage")
    check_call("./bootstrap")
    check_call("./configure")
    check_call("make")
    # FIXME: permissions are wrong in Sage 8.9.
    os.chmod("local/share/jmol", stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP
        | stat.S_IROTH | stat.S_IXOTH)
    communicate("./sage", r"""
        # make appropriate octave directory
        octave.eval('1+2')
        quit
        """)
    log.info("successfully compiled Sage")


def install_packages():
    r"""
    Assuming Sage is already installed, install optional packages.
    """
    become_server()
    os.chdir("sage")
    log.info("installing optional Sage packages")
    for package in sage_optional_packages:
        check_call("./sage -i -y {}".format(package))
    log.info("installing pip packages")
    check_call("./sage -pip install --upgrade pip")
    for package in python_packages:
        check_call("./sage -pip install {}".format(package))
    log.info("installing R packages")
    for package in R_packages:
        communicate("./sage", r"""
            r.eval("install.packages('{}')")
            quit
            """.format(package))
        if "ImportError" in check_output(
                f"./sage -c \"r.library('{package}')\""):
            msg = f"R package {package} didn't install"
            log.error(msg)
            raise RuntimeError(msg)
    os.chdir("..")


def install_sagecell():
    r"""
    Install SageCell, assuming Sage and other packages are already installed.
    """
    become_server()
    log.info("compiling SageCell")
    shutil.move("github/sagecell", ".")
    shutil.rmtree("github")
    os.chdir("sagecell")
    with open("templates/provider.html", "w", encoding="utf-8") as f:
        f.write(provider_html)
    check_call("../sage/sage -sh -c 'make -B'")
    log.info("successfully compiled SageCell")


def install_config_files():
    r"""
    Install container's config files, adjusting names inside.
    """
    log.info("copying configuration files")
    os.chdir(os.path.join("/home", users["server"],
                          "sagecell/contrib/vm/compute_node"))

    def adjust_names(file):
        with open(file) as f:
            content = f.read()
        for key, value in users.items():
            content = content.replace("{%s}" % key, str(value))
        with open(file, "w") as f:
            f.write(content)

    adjust_names(shutil.copy("config.py", "../../.."))
    for root, _, files in os.walk("."):
        if root == ".":
            continue
        for file in files:
            name = os.path.join(root, file)
            adjust_names(shutil.copy(name, name[1:]))
    check_call("systemctl enable sagecell")


class SCLXC(object):
    r"""
    Wrapper for lxc.Container automatically performing prerequisite operations.
    """

    def __init__(self, name):
        self.name = name
        self.c = lxc.Container(self.name)

    def clone(self, clone_name, autostart=False, update=False):
        r"""
        Clone self, create a base container and destroy old clone if necessary.
        """
        if not self.is_defined():
            self.create()
        if update:
            self.update()
        self.shutdown()
        SCLXC(clone_name).destroy()
        log.info("cloning %s to %s", self.name, clone_name)
        if not self.c.clone(clone_name, flags=lxc.LXC_CLONE_SNAPSHOT):
            raise RuntimeError("failed to clone " + self.name)
        clone = SCLXC(clone_name)
        if autostart:
            clone.c.set_config_item("lxc.start.auto", "1")
            clone.c.set_config_item("lxc.start.delay", str(start_delay))
            clone.c.save_config()
        logdir = clone.c.get_config_item("lxc.rootfs.path") + "/var/log/"
        for logfile in ["sagecell.log", "sagecell-console.log"]:
            if os.path.exists(logdir + logfile):
                os.remove(logdir + logfile)
        return clone

    def create(self):
        r"""
        Create a base contrainer, destroy old one if necessary.
        """
        self.destroy()
        log.info("creating %s", self.name)
        # Try to automatically pick up proxy from host
        os.environ["HTTP_PROXY"] = "apt"
        if not self.c.create(
            "download", 0,
            {"dist": "ubuntu", "release": "focal", "arch": "amd64"},
            "btrfs"):
                raise RuntimeError("failed to create " + self.name)
        os.environ.unsetenv("HTTP_PROXY")

        self.update()
        log.info("installing packages")
        self.inside("apt install -y " + " ".join(packages))
        self.inside("/usr/sbin/deluser ubuntu --remove-home")
        log.info("installing later packages")
        self.inside("apt install -y " + " ".join(packages_later))
        # Need to preseed or there will be a dialog
        self.inside(communicate, "/usr/bin/debconf-set-selections",
            "tmpreaper tmpreaper/readsecurity note")
        self.inside("apt install -y tmpreaper")
        log.info("installing npm packages")
        self.inside("npm install -g requirejs")
        self.inside(install_macaulay2)

    def destroy(self):
        r"""
        Stop and destroy self if it exists.
        """
        if self.c.defined:
            log.info("destroying %s", self.name)
            if self.c.running and not self.c.stop():
                raise RuntimeError("failed to stop " + self.name)
            if not self.c.destroy():
                raise RuntimeError("failed to destroy " + self.name)
            self.c = lxc.Container(self.name)
        else:
            log.debug("not destroying %s since it is not defined", self.name)

    def inside(self, command, *args):
        r"""
        Run a function or a system command inside the container.
        """
        self.start()
        if isinstance(command, str):
            command = command.format_map(users)
            log.debug("executing '%s' in %s", command, self.name)
            if self.c.attach_wait(lxc.attach_run_command,
                                  shlex.split(command)):
                raise RuntimeError("failed to execute '{}'".format(command))
        else:
            args = [arg.format_map(users) if isinstance(arg, str) else arg
                    for arg in args]

            def wrapper():
                command(*args)
                os.sys.exit()   # Otherwise attach_wait returns -1

            log.debug("executing %s with arguments %s in %s",
                      command, args, self.name)
            if self.c.attach_wait(wrapper):
                raise RuntimeError("failed to execute {} with arguments {}"
                                   .format(command, args))

    def prepare_for_sagecell(self, keeprepos=False):
        r"""
        Set up everything necessary for SageCell installation.

        INPUT:

        - ``keeprepos`` -- if ``True``, GitHub repositories will NOT be updated
          and set to proper state (useful for development).
        """
        create_host_users()
        self.inside(setup_container_users)
        # FIXME: work with temp folders properly
        self.inside(os.mkdir, "/tmp/sagecell", 0o730)
        self.inside(os.chown, "/tmp/sagecell",
                    users["server_ID"], users["GID"])
        self.inside(os.chmod, "/tmp/sagecell", stat.S_ISGID)
        # Copy repositories into container
        if not keeprepos:
            update_repositories()
        log.info("uploading repositories to %s", self.name)
        root = self.c.get_config_item("lxc.rootfs.path")
        home = os.path.join(root, "home", users["server"])
        shutil.copytree("github", os.path.join(home, "github"), symlinks=True)
        self.inside("chown -R {server}:{group} /home/{server}/github")
        dot_cache = os.path.join(home, ".cache")
        try:
            shutil.copytree("dot_cache", dot_cache, symlinks=True)
            self.inside("chown -R {server}:{group} /home/{server}/.cache")
        except FileNotFoundError:
            pass
        self.inside(install_sage)
        self.inside(install_packages)
        # Remove old versions of packages
        upstream = os.path.join(home, "sage/upstream")
        packages = dict()
        for f in os.listdir(upstream):
            filename = os.path.join(upstream, f)
            name = f.split("-", 1)[0]
            if name not in packages:
                packages[name] = []
            packages[name].append((os.stat(filename).st_mtime, filename))
        for package in packages.values():
            package.sort()
            package.pop()
            for _, filename in package:
                os.remove(filename)
        try:
            shutil.rmtree("github/sage/upstream")
        except FileNotFoundError:
            pass
        shutil.move(upstream, "github/sage/upstream")
        try:
            shutil.rmtree("dot_cache")
        except FileNotFoundError:
            pass
        shutil.copytree(dot_cache, "dot_cache", symlinks=True)

    def install_sagecell(self):
        r"""
        Set up SageCell to run on startup.
        """
        self.inside(install_sagecell)
        self.inside(install_config_files)
        self.c.set_config_item("lxc.cgroup.memory.limit_in_bytes", "8G")
        self.c.save_config()
        self.shutdown()
        # Let first-time tasks to run and complete.
        self.start()
        timer_delay(start_delay)
        
    def ip(self):
        self.start()
        return self.c.get_ips()[0]

    def is_defined(self):
        return self.c.defined

    def save_logs(self):
        stamp_length = len("2014-12-28 15:00:02,315")
        root = self.c.get_config_item("lxc.rootfs.path")
        logdir = os.path.join(root, "var", "log")
        logname = "sagecell.log"
        fullname = os.path.join(logdir, logname)
        if not os.path.exists(fullname):
            return
        with open(fullname, "rb") as f:
            start = f.read(stamp_length).decode()
            f.seek(0, os.SEEK_END)
            f.seek(max(f.tell() - 2**16, 0))
            end = f.readlines()[-1][:stamp_length].decode()
        archname = "container_logs/%s to %s on %s" % (start, end, self.name)
        if not os.path.exists("container_logs"):
            os.mkdir("container_logs")
        log.info("saving %s", archname)
        shutil.make_archive(archname, "bztar", logdir, logname)

    def shutdown(self):
        if self.c.running and not self.c.shutdown(timeout):
            raise RuntimeError("failed to shutdown " + self.name)

    def start(self):
        r"""
        Make sure that ``self`` is running and network works.
        """
        if not self.c.running and not self.c.start():
            raise RuntimeError("failed to start " + self.name)
        if not self.c.get_ips(timeout=timeout):
            raise RuntimeError("failed to start network in " + self.name)

    def update(self):
        r"""
        Update OS packages in ``self``.
        """
        if self.is_defined():
            log.info("updating packages in %s", self.name)
            try:
                self.inside("apt update")
            except RuntimeError:
                # We get here if /var/lib/dpkg/lock is locked:
                # let's wait a bit and try again once
                timer_delay(timeout)
                self.inside("apt update")
            self.inside("apt full-upgrade -y --auto-remove")
        else:
            self.create()


def restart_haproxy(names, backup_names=[]):
    r"""
    Regenerate HA-Proxy configuration file and restart it.
    """
    log.debug("generating HAProxy configuration file")
    lines = [HAProxy_header]
    if names:
        shift = lambda n: 1 if n.endswith("A") else number_of_compute_nodes + 1
        section = HAProxy_section
        for k, v in {"port" : 80,
                     "suffix": "",
                     "peer_port": 1080,
                     "hostname": check_output("hostname").strip()}.items():
            section = section.replace("{" + k + "}", str(v))
        for l in section.splitlines():
            if "{node}" not in l:
                lines.append(l)
            else:
                for i, n in enumerate(names):
                    lines.append(l.format(
                        node=n, ip=SCLXC(n).ip(), id=i + shift(n)))
                l += " backup"
                for i, n in enumerate(backup_names):
                    lines.append(l.format(
                        node=n, ip=SCLXC(n).ip(), id=i + shift(n)))
    tester = SCLXC(lxcn_tester)
    if tester.is_defined():
        section = HAProxy_section
        for k, v in {"port" : 8888,
                     "suffix": "_test",
                     "node": lxcn_tester,
                     "ip": tester.ip(),
                     "id": 1,
                     "peer_port": 1088,
                     "hostname": check_output("hostname").strip()}.items():
            section = section.replace("{" + k + "}", str(v))
        lines.append(section)
    lines.append(HAProxy_stats)
    with open("/etc/haproxy/haproxy.cfg", "w") as f:
        f.write("\n".join(lines))
    try:
        check_call("systemctl reload haproxy")
    except subprocess.CalledProcessError:
        check_call("systemctl start haproxy")


logging.config.dictConfig(yaml.safe_load("""
    version: 1
    formatters:
      file:
        format: '%(asctime)s %(levelname)s: %(message)s'
      console:
        format: '########## %(asctime)s %(levelname)s: %(message)s ##########'
    handlers:
      file:
        class: logging.FileHandler
        formatter: file
        filename: container_manager.log
        level: DEBUG
      console:
        class: logging.StreamHandler
        formatter: console
        stream: ext://sys.stdout
        level: INFO
    root:
      level: DEBUG
      handlers: [file, console]
    """))
log = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="manage SageCell LXC containers",
                                 epilog="""
    Missing necessary containers are always created automatically.

    Default action without any options is to make sure that the master
    container is present and update its system packages.

    This script always overwrites system-wide HA-proxy configuration file and
    restarts HA-Proxy to resolve container names to new IP addresses.""")
parser.add_argument("-b", "--base", action="store_true",
                    help="rebuild 'OS and standard packages' container")
parser.add_argument("--keeprepos", action="store_true",
                    help="keep GitHub repositories at their present state")
parser.add_argument("-p", "--useprecell", action="store_true",
                    help="don't rebuild Sage and extra packages for master")
parser.add_argument("--savemaster", action="store_true",
                    help="save existing master container")
group = parser.add_mutually_exclusive_group()
group.add_argument("-m", "--master", action="store_true",
                    help="rebuild 'Sage and SageCell' container")
group.add_argument("--restoremaster", action="store_true",
                    help="restore previously saved master container")
parser.add_argument("-t", "--tester", action="store_true",
                    help="rebuild 'testing' container")
parser.add_argument("--deploy", action="store_true",
                    help="rotate deployed containers based on current master")
parser.add_argument("--nodelay", action="store_true",
                    help="don't wait for old containers to be out of use")
args = parser.parse_args()

# Do it only once and let users change it later.
if not os.path.exists("/etc/security/limits.d/sagecell.conf"):
    log.info("setting up security limits configuration file")
    with open("/etc/security/limits.d/sagecell.conf", "w") as f:
        f.write(limits_conf)
    log.info("Finish this session and start a new one for system configuration"
             " changes to take effect.")
    exit()
if not os.path.exists("/etc/rsyslog.d/sagecell.conf"):
    log.info("setting up rsyslog configuration file")
    with open("/etc/rsyslog.d/sagecell.conf", "w") as f:
        f.write(rsyslog_conf)
    check_call("systemctl restart rsyslog")

# Main chain: base -- precell -- (sagecell, backup)
base = SCLXC(lxcn_base)
if args.base:
    base.create()

sagecell = SCLXC(lxcn_sagecell)
if args.savemaster:
    sagecell.clone(lxcn_backup)
if args.restoremaster:
    sagecell = SCLXC(lxcn_backup).clone(lxcn_sagecell)

if args.master or not sagecell.is_defined():
    precell = SCLXC(lxcn_precell)
    if precell.is_defined() and args.useprecell:
        precell.update()
        if not args.keeprepos:
            precell.inside(
                "su -c 'git -C /home/{server}/github/sagecell pull' {server}")
    else:
        precell = base.clone(lxcn_precell, update=True)
        precell.prepare_for_sagecell(args.keeprepos)
    sagecell = precell.clone(lxcn_sagecell)
    sagecell.install_sagecell()
else:
    sagecell.update()

# Autostart containers: tester and deployed nodes.
if args.tester:
    sagecell.clone(lxcn_tester, autostart=True).start()

A_names = ["{}{}{}".format(lxcn_prefix, n, "A")
             for n in range(number_of_compute_nodes)]
B_names = ["{}{}{}".format(lxcn_prefix, n, "B")
             for n in range(number_of_compute_nodes)]
if all(SCLXC(n).is_defined() for n in A_names):
    up_names, old_names = A_names, B_names
elif all(SCLXC(n).is_defined() for n in B_names):
    up_names, old_names = B_names, A_names
else:
    up_names, old_names = [], A_names

if args.deploy:
    up_names, old_names = old_names, up_names
    for n in up_names:
        sagecell.clone(n, autostart=True).start()
    log.info("waiting for new containers to fully initialize...")
    timer_delay(start_delay)
    old_nodes = list(map(SCLXC, old_names))
    if old_nodes and not args.nodelay:
        old_haproxy = []
        for p in psutil.process_iter():
            try:
                if p.username() == 'haproxy':
                    old_haproxy.append(p)
            except psutil.NoSuchProcess:
                pass

        def test():
            return psutil.wait_procs(old_haproxy, timeout=1)[1]
            
        restart_haproxy(up_names, old_names)
        log.info("waiting for users to stop working with old containers...")
        timer_delay(deploy_delay, test)

restart_haproxy(up_names)

if args.deploy:
    for n in old_nodes:
        n.save_logs()
        n.destroy()
