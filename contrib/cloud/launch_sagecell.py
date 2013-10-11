#!/usr/bin/env python

import os
import sys
import json
import subprocess
import uuid

with open(os.path.join(os.environ['HOME'],".sagemathcloud/info.json")) as f:
    projectid=uuid.UUID(json.loads(f.read())['project_id'])

import argparse
parser = argparse.ArgumentParser(description='Launch a SageCell web server',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

# the default port is derived from the project id
parser.add_argument('-p', '--port', type=int, default=50000+(projectid.int%10000),
                    help='port to launch the server')

args = parser.parse_args()
port = args.port
baseurl = "/%s/port/%d/"%(projectid, port)
tmp_dir = '/tmp/sagecell-%s'%uuid.uuid4()
command="../sage/sage web_server.py --tmp_dir %s --port %d --interface tun0 --baseurl %s"%(tmp_dir, port, baseurl)
print "Go to:"
print "https://cloud.sagemath.com%s"%baseurl
print
print "Computations in %s"%tmp_dir
print "Running: %s"%command

subprocess.call("../sage/sage -sh -c 'make coffee'", shell=True)
subprocess.call("../sage/sage -sh -c 'make -B'", shell=True)
subprocess.call(command, shell=True)
