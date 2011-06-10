# encoding: utf-8

# This version modified (returns list from VerboseTB() rather than
# string and removes a number of functions) from the version that
# shipped with IPython 0.9.1.
#   Alex Kramer <kramer.alex.kramer@gmail.com>

# Comments and documentation can be found in Ipython/ultraTB.py in your
# IPython install, if needed. This file is purposely sparse for efficiency.

__docformat__ = "restructuredtext en"

#-------------------------------------------------------------------------------
#  Copyright (C) 2008  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------

from IPython import Release
__author__  = '%s <%s>\n%s <%s>' % (Release.authors['Nathan']+
                                    Release.authors['Fernando'])
__license__ = Release.license

# Required modules
import inspect
import keyword
import linecache
import os
import pydoc
import re
import string
import sys
import time
import tokenize
import traceback
import types

# For purposes of monkeypatching inspect to fix a bug in it.
from inspect import getsourcefile, getfile, getmodule,\
     ismodule,  isclass, ismethod, isfunction, istraceback, isframe, iscode


# IPython's own modules
# Modified pdb which doesn't damage IPython's readline handling
from IPython import Debugger, PyColorize
from IPython.ipstruct import Struct
from IPython.excolors import ExceptionColors
from IPython.genutils import Term,uniq_stable,error,info

# Globals
# amount of space to put line numbers before verbose tracebacks
INDENT_SIZE = 8

# Default color scheme.  This is used, for example, by the traceback
# formatter.  When running in an actual IPython instance, the user's rc.colors
# value is used, but havinga module global makes this functionality available
# to users of ultraTB who are NOT running inside ipython.
DEFAULT_SCHEME = 'NoColor'

#---------------------------------------------------------------------------
# Code begins

# Utility functions
def inspect_error():
    """Print a message about internal inspect errors.

    These are unfortunately quite common."""
    
    error('Internal Python error in the inspect module.\n'
          'Below is the traceback from this internal error.\n')


def findsource(object):
    """Return the entire source file and starting line number for an object.

    The argument may be a module, class, method, function, traceback, frame,
    or code object.  The source code is returned as a list of all the lines
    in the file and the line number indexes a line in that list.  An IOError
    is raised if the source code cannot be retrieved.

    FIXED version with which we monkeypatch the stdlib to work around a bug."""

    file = getsourcefile(object) or getfile(object)
    module = getmodule(object, file)
    if module:
        lines = linecache.getlines(file, module.__dict__)
    else:
        lines = linecache.getlines(file)
    if not lines:
        raise IOError('could not get source code')

    if ismodule(object):
        return lines, 0

    if isclass(object):
        name = object.__name__
        pat = re.compile(r'^(\s*)class\s*' + name + r'\b')
        # make some effort to find the best matching class definition:
        # use the one with the least indentation, which is the one
        # that's most probably not inside a function definition.
        candidates = []
        for i in range(len(lines)):
            match = pat.match(lines[i])
            if match:
                # if it's at toplevel, it's already the best one
                if lines[i][0] == 'c':
                    return lines, i
                # else add whitespace to candidate list
                candidates.append((match.group(1), i))
        if candidates:
            # this will sort by whitespace, and by line number,
            # less whitespace first
            candidates.sort()
            return lines, candidates[0][1]
        else:
            raise IOError('could not find class definition')

    if ismethod(object):
        object = object.im_func
    if isfunction(object):
        object = object.func_code
    if istraceback(object):
        object = object.tb_frame
    if isframe(object):
        object = object.f_code
    if iscode(object):
        if not hasattr(object, 'co_firstlineno'):
            raise IOError('could not find function definition')
        pat = re.compile(r'^(\s*def\s)|(.*(?<!\w)lambda(:|\s))|^(\s*@)')
        pmatch = pat.match
        # fperez - fix: sometimes, co_firstlineno can give a number larger than
        # the length of lines, which causes an error.  Safeguard against that.
        lnum = min(object.co_firstlineno,len(lines))-1
        while lnum > 0:
            if pmatch(lines[lnum]): break
            lnum -= 1
 
        return lines, lnum
    raise IOError('could not find code object')

# Monkeypatch inspect to apply our bugfix.  This code only works with py25
if sys.version_info[:2] >= (2,5):
    inspect.findsource = findsource

def _fixed_getinnerframes(etb, context=1,tb_offset=0):
    import linecache
    LNUM_POS, LINES_POS, INDEX_POS =  2, 4, 5

    records  = inspect.getinnerframes(etb, context)

    # If the error is at the console, don't build any context, since it would
    # otherwise produce 5 blank lines printed out (there is no file at the
    # console)
    rec_check = records[tb_offset:]
    try:
        rname = rec_check[0][1]
        if rname == '<ipython console>' or rname.endswith('<string>'):
            return rec_check
    except IndexError:
        pass

    aux = traceback.extract_tb(etb)
    assert len(records) == len(aux)
    for i, (file, lnum, _, _) in zip(range(len(records)), aux):
        maybeStart = lnum-1 - context//2
        start =  max(maybeStart, 0)
        end   = start + context
        lines = linecache.getlines(file)[start:end]
        # pad with empty lines if necessary
        if maybeStart < 0:
            lines = (['\n'] * -maybeStart) + lines
        if len(lines) < context:
            lines += ['\n'] * (context - len(lines))
        buf = list(records[i])
        buf[LNUM_POS] = lnum
        buf[INDEX_POS] = lnum - 1 - start
        buf[LINES_POS] = lines
        records[i] = tuple(buf)
    return records[tb_offset:]

# Helper function -- largely belongs to VerboseTB, but we need the same
# functionality to produce a pseudo verbose TB for SyntaxErrors, so that they
# can be recognized properly by ipython.el's py-traceback-line-re
# (SyntaxErrors have to be treated specially because they have no traceback)

_parser = PyColorize.Parser()
    
def _formatTracebackLines(lnum, index, lines, Colors, lvals=None,scheme=None):
    numbers_width = INDENT_SIZE - 1
    res = []
    i = lnum - index

    # This lets us get fully syntax-highlighted tracebacks.
    if scheme is None:
        try:
            scheme = __IPYTHON__.rc.colors
        except:
            scheme = DEFAULT_SCHEME
    _line_format = _parser.format2

    for line in lines:
        new_line, err = _line_format(line,'str',scheme)
        if not err: line = new_line
        
        if i == lnum:
            # This is the line with the error
            pad = numbers_width - len(str(i))
            if pad >= 3:
                marker = '-'*(pad-3) + '-> '
            elif pad == 2:
                marker = '> '
            elif pad == 1:
                marker = '>'
            else:
                marker = ''
            num = marker + str(i)
            line = '%s%s%s %s%s' %(Colors.linenoEm, num, 
                                   Colors.line, line, Colors.Normal)
        else:
            num = '%*s' % (numbers_width,i)
            line = '%s%s%s %s' %(Colors.lineno, num, 
                                 Colors.Normal, line)

        res.append(line)
        if lvals and i == lnum:
            res.append(lvals + '\n')
        i = i + 1
    return res


#---------------------------------------------------------------------------
# Module classes
class TBTools:
    """Basic tools used by all traceback printer classes."""

    def __init__(self,color_scheme = 'NoColor',call_pdb=False):
        # Whether to call the interactive pdb debugger after printing
        # tracebacks or not
        self.call_pdb = call_pdb

        # Create color table
        self.color_scheme_table = ExceptionColors 

        self.set_colors(color_scheme)
        self.old_scheme = color_scheme  # save initial value for toggles

        if call_pdb:
            self.pdb = Debugger.Pdb(self.color_scheme_table.active_scheme_name)
        else:
            self.pdb = None

    def set_colors(self,*args,**kw):
        """Shorthand access to the color table scheme selector method."""

        # Set own color table
        self.color_scheme_table.set_active_scheme(*args,**kw)
        # for convenience, set Colors to the active scheme
        self.Colors = self.color_scheme_table.active_colors
        # Also set colors of debugger
        if hasattr(self,'pdb') and self.pdb is not None:
            self.pdb.set_colors(*args,**kw)

    def color_toggle(self):
        """Toggle between the currently active color scheme and NoColor."""
        
        if self.color_scheme_table.active_scheme_name == 'NoColor':
            self.color_scheme_table.set_active_scheme(self.old_scheme)
            self.Colors = self.color_scheme_table.active_colors
        else:
            self.old_scheme = self.color_scheme_table.active_scheme_name
            self.color_scheme_table.set_active_scheme('NoColor')
            self.Colors = self.color_scheme_table.active_colors

#----------------------------------------------------------------------------
class VerboseTB(TBTools):
    """A port of Ka-Ping Yee's cgitb.py module that outputs color text instead
    of HTML.  Requires inspect and pydoc.  Crazy, man.

    Modified version which optionally strips the topmost entries from the
    traceback, to be used with alternate interpreters (because their own code
    would appear in the traceback)."""

    def __init__(self,color_scheme = 'Linux',tb_offset=0,long_header=0,
                 call_pdb = 0, include_vars=1):
        """Specify traceback offset, headers and color scheme.

        Define how many frames to drop from the tracebacks. Calling it with
        tb_offset=1 allows use of this handler in interpreters which will have
        their own code at the top of the traceback (VerboseTB will first
        remove that frame before printing the traceback info)."""
        TBTools.__init__(self,color_scheme=color_scheme,call_pdb=call_pdb)
        self.tb_offset = tb_offset
        self.long_header = long_header
        self.include_vars = include_vars

    def text(self, etype, evalue, etb, context=5):
        """Return a nice text document describing the traceback."""

        # some locals
        try:
            etype = etype.__name__
        except AttributeError:
            pass
        Colors        = self.Colors   # just a shorthand + quicker name lookup
        ColorsNormal  = Colors.Normal  # used a lot
        col_scheme    = self.color_scheme_table.active_scheme_name
        indent        = ' '*INDENT_SIZE
        em_normal     = '%s\n%s%s' % (Colors.valEm, indent,ColorsNormal)
        undefined     = '%sundefined%s' % (Colors.em, ColorsNormal)
        exc = '%s%s%s' % (Colors.excName,etype,ColorsNormal)

        # some internal-use functions
        def text_repr(value):
            """Hopefully pretty robust repr equivalent."""
            # this is pretty horrible but should always return *something*
            try:
                return pydoc.text.repr(value)
            except KeyboardInterrupt:
                raise
            except:
                try:
                    return repr(value)
                except KeyboardInterrupt:
                    raise
                except:
                    try:
                        # all still in an except block so we catch
                        # getattr raising
                        name = getattr(value, '__name__', None)
                        if name:
                            # ick, recursion
                            return text_repr(name)
                        klass = getattr(value, '__class__', None)
                        if klass:
                            return '%s instance' % text_repr(klass)
                    except KeyboardInterrupt:
                        raise
                    except:
                        return 'UNRECOVERABLE REPR FAILURE'
        def eqrepr(value, repr=text_repr): return '=%s' % repr(value)
        def nullrepr(value, repr=text_repr): return ''

        # meat of the code begins
        try:
            etype = etype.__name__
        except AttributeError:
            pass

        if self.long_header:
            # Header with the exception type, python version, and date
            pyver = 'Python ' + string.split(sys.version)[0] + ': ' + sys.executable
            date = time.ctime(time.time())
            
            head = '%s%s%s\n%s%s%s\n%s' % (Colors.topline, '-'*75, ColorsNormal,
                                           exc, ' '*(75-len(str(etype))-len(pyver)),
                                           pyver, string.rjust(date, 75) )
            head += "\nA problem occured executing Python code.  Here is the sequence of function"\
                    "\ncalls leading up to the error, with the most recent (innermost) call last."
        else:
            # Simplified header
            head = '%s%s%s\n%s%s' % (Colors.topline, '-'*75, ColorsNormal,exc,
                                     string.rjust('Traceback (most recent call last)',
                                                  75 - len(str(etype)) ) )
        frames = []
        # Flush cache before calling inspect.  This helps alleviate some of the
        # problems with python 2.3's inspect.py.
        linecache.checkcache()
        # Drop topmost frames if requested
        try:
            # Try the default getinnerframes and Alex's: Alex's fixes some
            # problems, but it generates empty tracebacks for console errors
            # (5 blanks lines) where none should be returned.
            #records = inspect.getinnerframes(etb, context)[self.tb_offset:]
            #print 'python records:', records # dbg
            records = _fixed_getinnerframes(etb, context,self.tb_offset)
            #print 'alex   records:', records # dbg
        except:

            # FIXME: I've been getting many crash reports from python 2.3
            # users, traceable to inspect.py.  If I can find a small test-case
            # to reproduce this, I should either write a better workaround or
            # file a bug report against inspect (if that's the real problem).
            # So far, I haven't been able to find an isolated example to
            # reproduce the problem.
            inspect_error()
            traceback.print_exc(file=Term.cerr)
            info('\nUnfortunately, your original traceback can not be constructed.\n')
            return ''

        # build some color string templates outside these nested loops
        tpl_link       = '%s%%s%s' % (Colors.filenameEm,ColorsNormal)
        tpl_call       = 'in %s%%s%s%%s%s' % (Colors.vName, Colors.valEm,
                                              ColorsNormal)
        tpl_call_fail  = 'in %s%%s%s(***failed resolving arguments***)%s' % \
                         (Colors.vName, Colors.valEm, ColorsNormal)
        tpl_local_var  = '%s%%s%s' % (Colors.vName, ColorsNormal)
        tpl_global_var = '%sglobal%s %s%%s%s' % (Colors.em, ColorsNormal,
                                                 Colors.vName, ColorsNormal)
        tpl_name_val   = '%%s %s= %%s%s' % (Colors.valEm, ColorsNormal)
        tpl_line       = '%s%%s%s %%s' % (Colors.lineno, ColorsNormal)
        tpl_line_em    = '%s%%s%s %%s%s' % (Colors.linenoEm,Colors.line,
                                            ColorsNormal)

        # now, loop over all records printing context and info
        abspath = os.path.abspath
        for frame, file, lnum, func, lines, index in records:
            #print '*** record:',file,lnum,func,lines,index  # dbg
            try:
                file = file and abspath(file) or '?'
            except OSError:
                # if file is '<console>' or something not in the filesystem,
                # the abspath call will throw an OSError.  Just ignore it and
                # keep the original file string.
                pass
            link = tpl_link % file
            try:
                args, varargs, varkw, locals = inspect.getargvalues(frame)
            except:
                # This can happen due to a bug in python2.3.  We should be
                # able to remove this try/except when 2.4 becomes a
                # requirement.  Bug details at http://python.org/sf/1005466
                inspect_error()
                traceback.print_exc(file=Term.cerr)
                info("\nIPython's exception reporting continues...\n")
                
            if func == '?':
                call = ''
            else:
                # Decide whether to include variable details or not
                var_repr = self.include_vars and eqrepr or nullrepr
                try:
                    call = tpl_call % (func,inspect.formatargvalues(args,
                                                varargs, varkw,
                                                locals,formatvalue=var_repr))
                except KeyError:
                    # Very odd crash from inspect.formatargvalues().  The
                    # scenario under which it appeared was a call to
                    # view(array,scale) in NumTut.view.view(), where scale had
                    # been defined as a scalar (it should be a tuple). Somehow
                    # inspect messes up resolving the argument list of view()
                    # and barfs out. At some point I should dig into this one
                    # and file a bug report about it.
                    inspect_error()
                    traceback.print_exc(file=Term.cerr)
                    info("\nIPython's exception reporting continues...\n")
                    call = tpl_call_fail % func

            # Initialize a list of names on the current line, which the
            # tokenizer below will populate.
            names = []

            def tokeneater(token_type, token, start, end, line):
                """Stateful tokeneater which builds dotted names.

                The list of names it appends to (from the enclosing scope) can
                contain repeated composite names.  This is unavoidable, since
                there is no way to disambguate partial dotted structures until
                the full list is known.  The caller is responsible for pruning
                the final list of duplicates before using it."""
                
                # build composite names
                if token == '.':
                    try:
                        names[-1] += '.'
                        # store state so the next token is added for x.y.z names
                        tokeneater.name_cont = True
                        return
                    except IndexError:
                        pass
                if token_type == tokenize.NAME and token not in keyword.kwlist:
                    if tokeneater.name_cont:
                        # Dotted names
                        names[-1] += token
                        tokeneater.name_cont = False
                    else:
                        # Regular new names.  We append everything, the caller
                        # will be responsible for pruning the list later.  It's
                        # very tricky to try to prune as we go, b/c composite
                        # names can fool us.  The pruning at the end is easy
                        # to do (or the caller can print a list with repeated
                        # names if so desired.
                        names.append(token)
                elif token_type == tokenize.NEWLINE:
                    raise IndexError
            # we need to store a bit of state in the tokenizer to build
            # dotted names
            tokeneater.name_cont = False

            def linereader(file=file, lnum=[lnum], getline=linecache.getline):
                line = getline(file, lnum[0])
                lnum[0] += 1
                return line

            # Build the list of names on this line of code where the exception
            # occurred.
            try:
                # This builds the names list in-place by capturing it from the
                # enclosing scope.
                tokenize.tokenize(linereader, tokeneater)
            except IndexError:
                # signals exit of tokenizer
                pass
            except tokenize.TokenError,msg:
                _m = ("An unexpected error occurred while tokenizing input\n"
                      "The following traceback may be corrupted or invalid\n"
                      "The error message is: %s\n" % msg)
                error(_m)
            
            # prune names list of duplicates, but keep the right order
            unique_names = uniq_stable(names)

            # Start loop over vars
            lvals = []
            if self.include_vars:
                for name_full in unique_names:
                    name_base = name_full.split('.',1)[0]
                    if name_base in frame.f_code.co_varnames:
                        if locals.has_key(name_base):
                            try:
                                value = repr(eval(name_full,locals))
                            except:
                                value = undefined
                        else:
                            value = undefined
                        name = tpl_local_var % name_full
                    else:
                        if frame.f_globals.has_key(name_base):
                            try:
                                value = repr(eval(name_full,frame.f_globals))
                            except:
                                value = undefined
                        else:
                            value = undefined
                        name = tpl_global_var % name_full
                    lvals.append(tpl_name_val % (name,value))
            if lvals:
                lvals = '%s%s' % (indent,em_normal.join(lvals))
            else:
                lvals = ''

            level = '%s %s\n' % (link,call)

            if index is None:
                frames.append(level)
            else:
                frames.append('%s%s' % (level,''.join(
                    _formatTracebackLines(lnum,index,lines,Colors,lvals,
                                          col_scheme))))

        # Get (safely) a string form of the exception info
        try:
            etype_str,evalue_str = map(str,(etype,evalue))
        except:
            # User exception is improperly defined.
            etype,evalue = str,sys.exc_info()[:2]
            etype_str,evalue_str = map(str,(etype,evalue))
        # ... and format it
        exception = ['%s%s%s: %s' % (Colors.excName, etype_str,
                                     ColorsNormal, evalue_str)]
        if type(evalue) is types.InstanceType:
            try:
                names = [w for w in dir(evalue) if isinstance(w, basestring)]
            except:
                # Every now and then, an object with funny inernals blows up
                # when dir() is called on it.  We do the best we can to report
                # the problem and continue
                _m = '%sException reporting error (object with broken dir())%s:'
                exception.append(_m % (Colors.excName,ColorsNormal))
                etype_str,evalue_str = map(str,sys.exc_info()[:2])
                exception.append('%s%s%s: %s' % (Colors.excName,etype_str,
                                     ColorsNormal, evalue_str))
                names = []
            for name in names:
                value = text_repr(getattr(evalue, name))
                exception.append('\n%s%s = %s' % (indent, name, value))
        # return all our info assembled as a single string
        # Old code:
        # return '%s\n\n%s\n%s' % (head,'\n'.join(frames),''.join(exception[0]) )
        return [head] + frames + [''.join(exception[0])]

    def debugger(self,force=False):
        """Call up the pdb debugger if desired, always clean up the tb
        reference.

        Keywords:

          - force(False): by default, this routine checks the instance call_pdb
          flag and does not actually invoke the debugger if the flag is false.
          The 'force' option forces the debugger to activate even if the flag
          is false.

        If the call_pdb flag is set, the pdb interactive debugger is
        invoked. In all cases, the self.tb reference to the current traceback
        is deleted to prevent lingering references which hamper memory
        management.

        Note that each call to pdb() does an 'import readline', so if your app
        requires a special setup for the readline completers, you'll have to
        fix that by hand after invoking the exception handler."""

        if force or self.call_pdb:
            if self.pdb is None:
                self.pdb = Debugger.Pdb(
                    self.color_scheme_table.active_scheme_name)
            # the system displayhook may have changed, restore the original
            # for pdb
            dhook = sys.displayhook
            sys.displayhook = sys.__displayhook__
            self.pdb.reset()
            # Find the right frame so we don't pop up inside ipython itself
            if hasattr(self,'tb'):
                etb = self.tb
            else:
                etb = self.tb = sys.last_traceback
            while self.tb.tb_next is not None:
                self.tb = self.tb.tb_next
            try:
                if etb and etb.tb_next:
                    etb = etb.tb_next
                self.pdb.botframe = etb.tb_frame
                self.pdb.interaction(self.tb.tb_frame, self.tb)
            finally:
                sys.displayhook = dhook
            
        if hasattr(self,'tb'):
            del self.tb

    def handler(self, info=None):
        (etype, evalue, etb) = info or sys.exc_info()
        self.tb = etb
        Term.cout.flush()
        Term.cerr.flush()
        print >> Term.cerr, self.text(etype, evalue, etb)

    # Changed so an instance can just be called as VerboseTB_inst() and print
    # out the right info on its own.
    def __call__(self, etype=None, evalue=None, etb=None):
        """This hook can replace sys.excepthook (for Python 2.1 or higher)."""
        if etb is None:
            self.handler()
        else:
            self.handler((etype, evalue, etb))
        self.debugger()

#----------------------------------------------------------------------------
# module testing (minimal)
if __name__ == "__main__":
    def spam(c, (d, e)):
        x = c + d
        y = c * d
        foo(x, y)

    def foo(a, b, bar=1):
        eggs(a, b + bar)

    def eggs(f, g, z=globals()):
        h = f + g
        i = f - g
        return h / i

    print ''
    print '*** Before ***'
    try:
        print spam(1, (2, 3))
    except:
        traceback.print_exc()
    print ''
    
    handler = ColorTB()
    print '*** ColorTB ***'
    try:
        print spam(1, (2, 3))
    except:
        apply(handler, sys.exc_info() )
    print ''
    
    handler = VerboseTB()
    print '*** VerboseTB ***'
    try:
        print spam(1, (2, 3))
    except:
        apply(handler, sys.exc_info() )
    print ''
    
