#!/usr/bin/env python

import sagecell_config
import uuid
options=sagecell_config.device_config
python=options.pop('python')

pidfile=''
command=python+' trusted_db.py '
for k,v in options.items():
    if k=='pidfile':
        v+=str(uuid.uuid4())+'.pid'
        pidfile=v
    command+=' --%s %r '%(k,v)


import os
print 'Executing: ', command
os.system(command)
if pidfile and os.path.isfile(pidfile):
    os.remove(pidfile)
