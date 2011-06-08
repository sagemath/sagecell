#!/usr/bin/env python

import singlecell_config

options=singlecell_config.device_config
python=options.pop('python')

command=python+' trusted_db.py '
for k,v in options.items():
    command+=' --%s %r '%(k,v)

import os
print 'Executing: ', command
os.system(command)
