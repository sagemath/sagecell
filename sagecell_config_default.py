# Set the path to Sage here:
sage=''

if sage=='':
   import os
   sage=os.environ['SAGE_ROOT']+'/sage '

python=sage+' -python'


# DATABASE
db='sqlalchemy'
fs=db

# SQLAlchemy
sqlalchemy_config={
    'uri': 'sqlite:///sqlite.db'
}

# MONGODB
mongo_config={
    'mongo_uri': 'mongodb://localhost',
    'mongo_db': 'sagecelldb'
    }

# WEB SERVER
webserver='flaskweb'
#webserver='twistd'
#webserver='uwsgi'

flaskweb_config={
    'port': 8080,
    'processes': 20,
    'host': '127.0.0.1'
}

twistd=sage+' -twistd'
twistd_config={
    'port': 8080,
}

uwsgi='./uwsgi'
uwsgi_config={
    'processes': 50,
    'listen': 500,
    'disable-logging': '',
    'socket': '/tmp/uwsgi.sock',
    }

# DEVICE
device_config={
    'workers': 5,
    'quiet': '',
    'python': python,
    'untrusted-account': 'localhost',
    'untrusted-python': python,
    'untrusted-cpu': -1, # seconds
    'untrusted-mem': -1, # megabytes
    }

flask_config={
    'max_files': 10,
    }

LOGGING=True
