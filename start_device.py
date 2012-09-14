#!/usr/bin/env python

try:
    import sagecell_config
except:
    import sagecell_config_default as sagecell_config

import uuid
options=sagecell_config.device_config
python=options.pop('python')

pidfile=''
command=python+' trusted_db.py '
for k,v in options.items():
    if k=='quiet' or k=='print': # quiet and print have no arguments
        command += ' --%s '%(k,)
        continue
    elif k=='pidfile':
        v+=str(uuid.uuid4())+'.pid'
        pidfile=v

    command+=' --%s %r '%(k,v)
        

import os
print 'Executing: ', command
os.system(command)
if pidfile and os.path.isfile(pidfile):
    os.remove(pidfile)
