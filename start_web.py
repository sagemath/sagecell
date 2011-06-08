#!/usr/bin/env python

import singlecell_config

command='./uwsgi '
for k,v in singlecell_config.web_server_config.items():
    command+=' --%s %r '%(k,v)

import os
print 'Executing: ', command
os.system(command)
