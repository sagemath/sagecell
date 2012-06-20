"""
Misc functions / classes
"""

class Config:
    def __init__(self):
        try:
            import config
        except ImportError:
            import config_default as config
        self.config = config

    def get_config(self, value):
        """
        Get a config attribute
        """
        config_val = None

        try:
            config_val = getattr(self.config, value)
        except AttributeError:
            pass

        return config_val

    def set_config(self, attr, value):
        """
        Set a config attribute
        """
        setattr(self.config, attr, value)

    def get_attrs(self):
        """
        Get a list of all the config object's attributes
        """
        return dir(self.config)

def get_db_file(config):
    db_file = None

    db = config.get_config("db")
    db_config = config.get_config("db_config")
    if db == "sqlalchemy":
        db_file = db_config.get("uri")

    return db_file
        
