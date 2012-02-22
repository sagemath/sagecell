#!/usr/bin/env python

import sagecell_config

if hasattr(sagecell_config, 'webserver'):
    webserver = sagecell_config.webserver
else:
    webserver = 'python'

pidfile=''
if webserver=='uwsgi':
    command=sagecell_config.uwsgi+' --module web_server:app'
    for k,v in sagecell_config.uwsgi_config.items():
        if k=='pidfile':
            pidfile=v
        command+=' --%s %r '%(k,v)
elif webserver=='twistd':
    command = sagecell_config.twistd+" -n web --wsgi web_server.app"
    for k,v in sagecell_config.twistd_config.items():
        if k=='pidfile':
            pidfile=v
        command+=' --%s %r '%(k,v)
elif webserver=='python':
    # Run in single-user mode
    command = sagecell_config.python+" ./web_server.py"

import os
print 'Executing: ', command
os.system(command)
if pidfile and os.path.isfile(pidfile):
    os.remove(pidfile)
