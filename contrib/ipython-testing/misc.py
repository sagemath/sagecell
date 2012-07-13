"""
Misc functions / classes
"""
from functools import wraps
from contextlib import contextmanager
# note: ensure sage's version of python has nose installed or starting new sessions may hang!
from nose.tools import assert_is, assert_equal, assert_in, assert_not_in, assert_raises, assert_regexp_matches, assert_is_instance, assert_is_not_none, assert_greater
import sys
import re

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
        possible. If the attribute is a dictionary, the items
        in config and default_config will be merged.

        :arg attr str: the name of the attribute to get
        :returns: the value of the named attribute, or
            None if the attribute does not exist.
        """
        default_config_val = self.get_default_config(attr)
        config_val = default_config_val

        if self.config is not None:
            try:
                config_val = getattr(self.config, attr)
            except AttributeError:
                pass

        if isinstance(config_val, dict):
            config_val = dict(default_config_val.items() + config_val.items())

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
        


def decorator_defaults(func):
    """
    This function allows a decorator to have default arguments.

    Normally, a decorator can be called with or without arguments.
    However, the two cases call for different types of return values.
    If a decorator is called with no parentheses, it should be run
    directly on the function.  However, if a decorator is called with
    parentheses (i.e., arguments), then it should return a function
    that is then in turn called with the defined function as an
    argument.

    This decorator allows us to have these default arguments without
    worrying about the return type.

    EXAMPLES::
    
        sage: from sage.misc.decorators import decorator_defaults
        sage: @decorator_defaults
        ... def my_decorator(f,*args,**kwds):
        ...     print kwds
        ...     print args
        ...     print f.__name__
        ...       
        sage: @my_decorator
        ... def my_fun(a,b):
        ...     return a,b
        ...  
        {}
        ()
        my_fun
        sage: @my_decorator(3,4,c=1,d=2)
        ... def my_fun(a,b):
        ...     return a,b
        ...   
        {'c': 1, 'd': 2}
        (3, 4)
        my_fun
    """
    from inspect import isfunction
    @wraps(func)
    def my_wrap(*args,**kwargs):
        if len(kwargs)==0 and len(args)==1 and isfunction(args[0]):
            # call without parentheses
            return func(*args)
        else:
            def _(f):
                return func(f, *args, **kwargs)
            return _
    return my_wrap

@contextmanager
def stream_metadata(metadata):
    streams = {'stdout': sys.stdout, 'stderr': sys.stderr}
    old_metadata={}
    for k,stream in streams.items():
        # flush out messages that need old metadata before we update the 
        # metadata dictionary (since update actually modifies the dictionary)
        stream.flush()
        new_metadata = stream.metadata
        old_metadata[k] = new_metadata.copy()
        new_metadata.update(metadata)
    try:
        yield None
    finally:
        for k,stream in streams.items():
            # set_metadata does the flush for us
            stream.set_metadata(old_metadata[k])

@contextmanager
def session_metadata(metadata):
    # flush any messages waiting in buffers
    sys.stdout.flush()
    sys.stderr.flush()
    
    session = sys.stdout.session
    old_metadata = session.subheader.get('metadata',None)
    new_metadata = old_metadata.copy() if old_metadata is not None else {}
    new_metadata.update(metadata)
    session.subheader['metadata'] = new_metadata
    try:
        yield None
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        if old_metadata is None:
            del session.subheader['metadata']
        else:
            session.subheader['metadata'] = old_metadata

def display_message(data):
    session = sys.stdout.session
    content = {'data': data, 'source': 'sagecell'}
    session.send(sys.stdout.pub_socket, 'display_data', content=content, parent = sys.stdout.parent_header)

"""
Unit Testing Misc Functions
"""
def assert_len(obj,l):
    return assert_equal(len(obj), l, "Object %s should have length %s, but has length %s"%(obj,l,len(obj)))

def assert_uuid(s):
    uuid_re = re.compile('[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}')
    return assert_regexp_matches(s, uuid_re)

# from the attest python package - license is modified BSD
from StringIO import StringIO
@contextmanager
def capture_output(split=False):
    """Captures standard output and error during the context. Returns a
    tuple of the two streams as lists of lines, added after the context has
    executed.

    .. testsetup::

        from attest import capture_output

    >>> with capture_output() as (out, err):
    ...    print 'Captured'
    ...
    >>> out
    ['Captured']

    """
    stdout, stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = StringIO(), StringIO()
    out, err = [], []
    try:
        yield out, err
    finally:
        if split:
            out.extend(sys.stdout.getvalue().splitlines())
            err.extend(sys.stderr.getvalue().splitlines())
        else:
            out.append(sys.stdout.getvalue())
            err.append(sys.stderr.getvalue())
        sys.stdout, sys.stderr = stdout, stderr
