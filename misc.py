"""
Misc functions / classes
"""
from contextlib import contextmanager
# note: ensure sage's version of python has nose installed or starting new sessions may hang!
try:
    from nose.tools import assert_is, assert_equal, assert_in, assert_not_in, assert_raises, assert_regexp_matches, assert_is_instance, assert_is_not_none, assert_greater
except ImportError:    
    pass

from datetime import datetime
import os
import re
import shutil
import stat
import sys


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

    def get(self, attr):
        """
        Get a config attribute. If the attribute is defined
        in the user-specified file, that is used, otherwise
        the default config file attribute is used if
        possible. If the attribute is a dictionary, the items
        in config and default_config will be merged.

        :arg attr str: the name of the attribute to get
        :returns: the value of the named attribute, or
            None if the attribute does not exist.
        """
        default_config_val = self.get_default(attr)
        config_val = default_config_val

        if self.config is not None:
            try:
                config_val = getattr(self.config, attr)
            except AttributeError:
                pass

        if isinstance(config_val, dict):
            config_val = dict(default_config_val.items() + config_val.items())

        return config_val

    def get_default(self, attr):
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

    def set(self, attr, value):
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


@contextmanager
def session_metadata(metadata):
    # flush any messages waiting in buffers
    sys.stdout.flush()
    sys.stderr.flush()
    
    session = sys.stdout.session
    old_metadata = session.metadata
    new_metadata = old_metadata.copy()
    new_metadata.update(metadata)
    session.metadata = new_metadata
    yield
    sys.stdout.flush()
    sys.stderr.flush()
    session.metadata = old_metadata

def display_file(path, mimetype=None):
    path = os.path.relpath(path)
    if path.startswith("../"):
        shutil.copy(path, ".")
        path = os.path.basename(path)
    os.chmod(path, stat.S_IMODE(os.stat(path).st_mode) | stat.S_IRGRP)
    if mimetype is None:
        mimetype = 'application/x-file'
    mt = os.path.getmtime(path)
    display_message({
        'text/plain': '%s file' % mimetype,
        mimetype: path + '?m=%s' % mt})
    sys._sage_.sent_files[path] = mt

def display_html(s):
    display_message({'text/plain': 'html', 'text/html': s})

def display_message(data, metadata=None):
    sys.stdout.session.send(sys.stdout.pub_thread,
                            'display_data',
                            content={'data': data, 'source': 'sagecell'},
                            parent=sys.stdout.parent_header,
                            metadata=metadata)

def stream_message(stream, data, metadata=None):
    sys.stdout.session.send(sys.stdout.pub_thread,
                            'stream',
                            content={'name': stream, 'data': data},
                            parent=sys.stdout.parent_header,
                            metadata=metadata)

def reset_kernel_timeout(timeout):
    sys.stdout.session.send(sys.stdout.pub_thread,
                            'kernel_timeout',
                            content={'timeout': float(timeout)},
                            parent=sys.stdout.parent_header)

def javascript(code):
    sys._sage_.display_message({'application/javascript': code, 'text/plain': 'javascript code'})


def sage_json(obj):
    import sage.all
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, sage.rings.integer.Integer):
        return int(obj)
    elif isinstance(obj, (sage.rings.real_mpfr.RealLiteral, sage.rings.real_mpfr.RealNumber, sage.rings.real_double.RealDoubleElement)):
        return float(obj)
    else:
        raise TypeError("Object of type %s with value of %s is not JSON serializable" % (type(obj), repr(obj)))

##########################################
## Unit Testing Misc Functions
##########################################
def assert_len(obj,l):
    return assert_equal(len(obj), l, "Object %s should have length %s, but has length %s"%(obj,l,len(obj)))

uuid_re = re.compile('[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}')

def assert_uuid(s):
    return assert_regexp_matches(s, uuid_re)
