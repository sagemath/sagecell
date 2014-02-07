#!/usr/bin/env python

# extra things you need to do
# npm install -g inherits requirejs
# ssh-keygen
# cp ~/.ssh/id_rsa.pub ~/.ssh/authorized_keys

import os
import sys
import json
import subprocess
import uuid

SAGE='../sage '

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
command=SAGE+"web_server.py --tmp_dir %s --port %d --interface tun0 --baseurl %s"%(tmp_dir, port, baseurl)
print
print "https://cloud.sagemath.com%s"%baseurl
print
print "Computations in %s"%tmp_dir
print "Running: %s"%command

subprocess.call(SAGE+"-sh -c 'make coffee'", shell=True)
subprocess.call(SAGE+"-sh -c 'make -B'", shell=True)
stars="*"*60
print
print
for i in range(3): print stars
print
print "https://cloud.sagemath.com%s"%baseurl
print
for i in range(3): print stars
print "Computations in %s"%tmp_dir
print "Running: %s"%command
subprocess.call(command, shell=True)
