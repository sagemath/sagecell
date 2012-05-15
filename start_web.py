#!/usr/bin/env python

try:
    import sagecell_config
except:
    import sagecell_config_default as sagecell_config

if hasattr(sagecell_config, 'webserver'):
    webserver = sagecell_config.webserver
else:
    webserver = 'flaskweb'

config = getattr(sagecell_config, webserver+'_config', {})

pidfile=''
if webserver=='uwsgi':
    command=sagecell_config.uwsgi+' --module web_server:app'
elif webserver=='twistd':
    command = sagecell_config.twistd+" -n web --wsgi web_server.app"
elif webserver=='flaskweb':
    command = sagecell_config.python+" ./web_server.py"

for k,v in config.items():
    if k=='pidfile':
        pidfile=v
    command+=' --%s %r '%(k,v)

import os
print 'Executing: ', command
os.system(command)
if pidfile and os.path.isfile(pidfile):
    os.remove(pidfile)
