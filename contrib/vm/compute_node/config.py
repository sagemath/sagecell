import config_default


# Global database running on Google Compute Engine with a static IP
db = "web"
db_config = {"uri": "http://130.211.113.153"}

requires_tos = False

pid_file = '/home/{server}/sagecell.pid'

config_default.provider_settings.update({
    "max_kernels": 120,
    "max_preforked": 20,
    })

config_default.provider_info.update({
    "username": "{worker}",
    })
