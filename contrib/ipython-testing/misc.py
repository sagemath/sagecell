"""
Misc functions / classes
"""

class Config(object):
    """
    Config file wrapper / handler class

    This is designed to make loading and working with an
    importable configuration file with options relevant to
    multiple classes more convenient.

    Rather than re-importing a configuration module whenever
    a specific is attribute is needed, a Config object can
    be instantiated by some base application and the relevant
    attributes can be passed to whatever classes / functions
    are needed.

    This class tracks both the default and user-specified
    configuration files
    """
    def __init__(self):
        import config_default

        self.config = None
        self.config_default = config_default

        try:
            import config
            self.config = config
        except ImportError:
            pass

    def get_config(self, attr):
        """
        Get a config attribute. If the attribute is defined
        in the user-specified file, that is used, otherwise
        the default config file attribute is used if
        possible.

        :arg attr str: the name of the attribute to get
        :returns: the value of the named attribute, or
            None if the attribute does not exist.
        """
        config_val = self.get_default_config(attr)

        if self.config is not None:
            try:
                config_val = getattr(self.config, attr)
            except AttributeError:
                pass

        return config_val

    def get_default_config(self, attr):
        """
        Get a config attribute from the default config file.

        :arg attr str: the name of the attribute toget
        :returns: the value of the named attribute, or
            None if the attribute does not exist.
        """
        config_val = None

        try:
            config_val = getattr(self.config_default, attr)
        except AttributeError:
            pass

        return config_val

    def set_config(self, attr, value):
        """
        Set a config attribute

        :arg attr str: the name of the attribute to set
        :arg value: an arbitrary value to set the named
            attribute to
        """
        setattr(self.config, attr, value)

    def get_attrs(self):
        """
        Get a list of all the config object's attributes

        This isn't very useful right now, since it includes
        __<attr>__ attributes and the like.

        :returns: a list of all attributes belonging to
            the imported config module.
        :rtype: list
        """
        return dir(self.config)

def get_db_file(config):
    """
    A convenience function to get the correct location of a
    database from a config object.

    :arg config: a Config object
    :returns: the localation of the database file, for the
        purposes of instantiating a database.
    :rtype: str
    """
    db_file = None

    db = config.get_config("db")
    db_config = config.get_config("db_config")
    if db == "sqlalchemy":
        db_file = db_config.get("uri")

    return db_file
        
