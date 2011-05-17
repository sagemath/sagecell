# -*- coding: utf-8 -*-

# This version slightly modified (returns list from VerboseTB() rather than
# string) from the version that shipped with IPython 0.10.
#   Alex Kramer <kramer.alex.kramer@gmail.com>

# Comments and documentation can be found in Ipython/ultraTB.py in your
# IPython install, if needed. This file is purposely sparse for efficiency.

#*****************************************************************************
#       Copyright (C) 2001 Nathaniel Gray <n8gray@caltech.edu>
#       Copyright (C) 2001-2004 Fernando Perez <fperez@colorado.edu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************

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

from inspect import getsourcefile, getfile, getmodule,\
     ismodule,  isclass, ismethod, isfunction, istraceback, isframe, iscode

from IPython import Debugger, PyColorize, ipapi
from IPython.ipstruct import Struct
from IPython.excolors import exception_colors
from IPython.genutils import Term,uniq_stable,error,info

# Globals
INDENT_SIZE = 8

# Default color scheme.
DEFAULT_SCHEME = 'None'

# Utility functions
def inspect_error():
    """Print a message about internal inspect errors.

    These are unfortunately quite common."""
    
    error('Internal Python error in the inspect module.\n'
          'Below is the traceback from this internal error.\n')

def findsource(object):
    # Return the entire source file and starting line number for an object.

    file = getsourcefile(object) or getfile(object)
    globals_dict = None
    if inspect.isframe(object):
        globals_dict = object.f_globals
    else:
        module = getmodule(object, file)
        if module:
            globals_dict = module.__dict__
    lines = linecache.getlines(file, globals_dict)
    if not lines:
        raise IOError('could not get source code')

    if ismodule(object):
        return lines, 0

    if isclass(object):
        name = object.__name__
        pat = re.compile(r'^(\s*)class\s*' + name + r'\b')
        candidates = []
        for i in range(len(lines)):
            match = pat.match(lines[i])
            if match:
                if lines[i][0] == 'c':
                    return lines, i
                candidates.append((match.group(1), i))
        if candidates:
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
        lnum = min(object.co_firstlineno,len(lines))-1
        while lnum > 0:
            if pmatch(lines[lnum]): break
            lnum -= 1
 
        return lines, lnum
    raise IOError('could not find code object')

# Monkeypatch inspect to apply our bugfix.  This code only works with py25
if sys.version_info[:2] >= (2,5):
    inspect.findsource = findsource

def fix_frame_records_filenames(records):
    """Try to fix the filenames in each record from inspect.getinnerframes()."""
    
    fixed_records = []
    for frame, filename, line_no, func_name, lines, index in records:
        better_fn = frame.f_globals.get('__file__', None)
        if isinstance(better_fn, str):
            filename = better_fn
        fixed_records.append((frame, filename, line_no, func_name, lines, index))
    return fixed_records

def _fixed_getinnerframes(etb, context=1,tb_offset=0):
    import linecache
    LNUM_POS, LINES_POS, INDEX_POS =  2, 4, 5

    records  = fix_frame_records_filenames(inspect.getinnerframes(etb, context))

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

# Helper function -- largely belongs to VerboseTB

_parser = PyColorize.Parser()
    
def _formatTracebackLines(lnum, index, lines, Colors, lvals=None,scheme=None):
    numbers_width = INDENT_SIZE - 1
    res = []
    i = lnum - index

    if scheme is None:
        ipinst = ipapi.get()
        if ipinst is not None:
            scheme = ipinst.IP.rc.colors
        else:
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

        self.color_scheme_table = exception_colors()

        self.set_colors(color_scheme)
        self.old_scheme = color_scheme  # save initial value for toggles

        if call_pdb:
            self.pdb = Debugger.Pdb(self.color_scheme_table.active_scheme_name)
        else:
            self.pdb = None

    def set_colors(self,*args,**kw):
        """Shorthand access to the color table scheme selector method."""

        self.color_scheme_table.set_active_scheme(*args,**kw)
        self.Colors = self.color_scheme_table.active_colors
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
        """Specify traceback offset, headers and color scheme."""
        TBTools.__init__(self,color_scheme=color_scheme,call_pdb=call_pdb)
        self.tb_offset = tb_offset
        self.long_header = long_header
        self.include_vars = include_vars

    def text(self, etype, evalue, etb, context=5):
        """Return a nice text document describing the traceback."""

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
                        name = getattr(value, '__name__', None)
                        if name:
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
        linecache.checkcache()
        try:
            records = _fixed_getinnerframes(etb, context,self.tb_offset)
        except:
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

        abspath = os.path.abspath
        for frame, file, lnum, func, lines, index in records:
            #print '*** record:',file,lnum,func,lines,index  # dbg
            try:
                file = file and abspath(file) or '?'
            except OSError:
                pass
            link = tpl_link % file
            try:
                args, varargs, varkw, locals = inspect.getargvalues(frame)
            except:
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
                    inspect_error()
                    traceback.print_exc(file=Term.cerr)
                    info("\nIPython's exception reporting continues...\n")
                    call = tpl_call_fail % func

            names = []

            def tokeneater(token_type, token, start, end, line):
                """Stateful tokeneater which builds dotted names."""
                
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
                        names.append(token)
                elif token_type == tokenize.NEWLINE:
                    raise IndexError
            tokeneater.name_cont = False

            def linereader(file=file, lnum=[lnum], getline=linecache.getline):
                line = getline(file, lnum[0])
                lnum[0] += 1
                return line

            try:
                tokenize.tokenize(linereader, tokeneater)
            except IndexError:
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
                _m = '%sException reporting error (object with broken dir())%s:'
                exception.append(_m % (Colors.excName,ColorsNormal))
                etype_str,evalue_str = map(str,sys.exc_info()[:2])
                exception.append('%s%s%s: %s' % (Colors.excName,etype_str,
                                     ColorsNormal, evalue_str))
                names = []
            for name in names:
                value = text_repr(getattr(evalue, name))
                exception.append('\n%s%s = %s' % (indent, name, value))

        if records:
             filepath, lnum = records[-1][1:3]
             filepath = os.path.abspath(filepath)
             ipinst = ipapi.get()
             if ipinst is not None:
                 ipinst.IP.hooks.synchronize_with_editor(filepath, lnum, 0)
                
        # return all our info assembled as a single list:        
        # Old code: 
        # return '%s\n\n%s\n%s' % (head,'\n'.join(frames),''.join(exception[0]) )
        return [head] + frames + [''.join(exception[0])]

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
    
