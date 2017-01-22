import os.path

# Global database running on Google Compute Engine with a static IP
db = "web"
db_config = {"uri": "http://130.211.113.153"}

requires_tos = False

pid_file = '/home/{server}/sagecell.pid'

from config_default import _default_config

_default_config.update({
    "username": "{worker}",
    "location": os.path.dirname(os.path.abspath(__file__)),
    "max_kernels": 120,
    "preforked_kernels": 20,
    })
