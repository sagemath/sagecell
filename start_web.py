#!/usr/bin/env python

import sagecell_config

command='./uwsgi --module web_server:app'
for k,v in sagecell_config.web_server_config.items():
    command+=' --%s %r '%(k,v)

import os
print 'Executing: ', command
os.system(command)
