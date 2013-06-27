#########################################################################################
#       Copyright (C) 2012 Jason Grout, Ira Hanson, Alex Kramer                         #
#                                                                                       #
#  Distributed under the terms of the GNU General Public License (GPL), version 2+      #
#                                                                                       #
#                  http://www.gnu.org/licenses/                                         #
#########################################################################################

# the only reason this file is distributed under GPLv2+ is because it
# imports functions from interact_sagecell.py, which is distributed as
# GPLv2+.  The actual code in this file is under the modified BSD
# license, which means that if those imports are replaced with
# BSD-compatible functions, this file can be distributed under the
# modified BSD license.


"""
This module defines a backwards-compatible API for interact controls from the first interact design.

"""

from interact_sagecell import *

"""
text_control: http://www.sagemath.org/doc/reference/sagenb/notebook/interact.html#sagenb.notebook.interact.text_control
slider: http://www.sagemath.org/doc/reference/sagenb/notebook/interact.html#sagenb.notebook.interact.slider
range_slider: http://www.sagemath.org/doc/reference/sagenb/notebook/interact.html#sagenb.notebook.interact.range_slider
selector: http://www.sagemath.org/doc/reference/sagenb/notebook/interact.html#sagenb.notebook.interact.selector
input_grid: http://www.sagemath.org/doc/reference/sagenb/notebook/interact.html#sagenb.notebook.interact.input_grid
input_box: http://www.sagemath.org/doc/reference/sagenb/notebook/interact.html#sagenb.notebook.interact.input_box
color_selector: http://www.sagemath.org/doc/reference/sagenb/notebook/interact.html#sagenb.notebook.interact.color_selector
checkbox: http://www.sagemath.org/doc/reference/sagenb/notebook/interact.html#sagenb.notebook.interact.checkbox
"""

import math
def __old_make_values_list(vmin, vmax, step_size):
    """
    This code is from slider_generic.__init__.

    This code requires sage mode to be checked.
    """
    from sagenb.misc.misc import srange
    if isinstance(vmin, list):
        vals=vmin
    else:
        if vmax is None:
            vmax=vmin
            vmin=0
        #Compute step size; vmin and vmax are both defined here
        #500 is the length of the slider (in px)
        if step_size is None:
            step_size = (vmax-vmin)/499.0
        elif step_size <= 0:
            raise ValueError, "invalid negative step size -- step size must be positive"

        #Compute list of values
        num_steps = int(math.ceil((vmax-vmin)/float(step_size)))
        if num_steps <= 1:
            vals = [vmin, vmax]
        else:
            vals = srange(vmin, vmax, step_size, include_endpoint=True)
            if vals[-1] != vmax:
                try:
                    if vals[-1] > vmax:
                        vals[-1] = vmax
                    else:
                        vals.append(vmax)
                except (ValueError, TypeError):
                    pass
    
    #If the list of values is small, use the whole list.
    #Otherwise, use evenly spaced values in the list.
    if len(vals) == 0:
        return_values = [0]
    elif(len(vals)<=500):
        return_values = vals
    else:
        vlen = (len(vals)-1)/499.0
        return_values = [vals[(int)(i*vlen)] for i in range(500)]
    return return_values



def slider(vmin, vmax=None,step_size=None, default=None, label=None,
           display_value=True):
    r"""
    An interactive slider control, which can be used in conjunction
    with the :func:`interact` command.

    INPUT:

    - ``vmin`` - an object

    - ``vmax`` - an object (default: None); if None then ``vmin``
      must be a list, and the slider then varies over elements of
      the list.

    - ``step_size`` - an integer (default: 1)

    - ``default`` - an object (default: None); default value is
      "closest" in ``vmin`` or range to this default.

    - ``label`` - a string

    - ``display_value`` - a bool, whether to display the current
      value to the right of the slider

    EXAMPLES:

    We specify both ``vmin`` and ``vmax``.  We make the default
    `3`, but since `3` isn't one of `3/17`-th spaced values
    between `2` and `5`, `52/17` is instead chosen as the
    default (it is closest)::

        sage: slider(2, 5, 3/17, 3, 'alpha')
        Slider: alpha [2--|52/17|---5]

    Here we give a list::

        sage: slider([1..10], None, None, 3, 'alpha')
        Slider: alpha [1--|3|---10]

    The elements of the list can be anything::

        sage: slider([1, 'x', 'abc', 2/3], None, None, 'x', 'alpha')
        Slider: alpha [1--|x|---2/3]            
        """        r"""
    An interactive slider control, which can be used in conjunction
    with the :func:`interact` command.

    INPUT:

    - ``vmin`` - an object

    - ``vmax`` - an object (default: None); if None then ``vmin``
      must be a list, and the slider then varies over elements of
      the list.

    - ``step_size`` - an integer (default: 1)

    - ``default`` - an object (default: None); default value is
      "closest" in ``vmin`` or range to this default.

    - ``label`` - a string

    - ``display_value`` - a bool, whether to display the current
      value to the right of the slider

    EXAMPLES:

    We specify both ``vmin`` and ``vmax``.  We make the default
    `3`, but since `3` isn't one of `3/17`-th spaced values
    between `2` and `5`, `52/17` is instead chosen as the
    default (it is closest)::

        sage: slider(2, 5, 3/17, 3, 'alpha')
        Slider: alpha [2--|52/17|---5]

    Here we give a list::

        sage: slider([1..10], None, None, 3, 'alpha')
        Slider: alpha [1--|3|---10]

    The elements of the list can be anything::

        sage: slider([1, 'x', 'abc', 2/3], None, None, 'x', 'alpha')
        Slider: alpha [1--|x|---2/3]            
    """
    values=__old_make_values_list(vmin, vmax, step_size)
    return DiscreteSlider(range_slider=False, values=values, 
                          default=default, label=label, display_value=display_value)


def range_slider(vmin, vmax=None, step_size=None, default=None, label=None, display_value=True):
    r"""
    An interactive range slider control, which can be used in conjunction
    with the :func:`interact` command.

    INPUT:

    - ``vmin`` - an object

    - ``vmax`` - object or None; if None then ``vmin`` must be a
      list, and the slider then varies over elements of the list.

    - ``step_size`` - integer (default: 1)

    - ``default`` - a 2-tuple of objects (default: None); default
      range is "closest" in ``vmin`` or range to this default.

    - ``label`` - a string

    - ``display_value`` - a bool, whether to display the current
      value below the slider

    EXAMPLES:

    We specify both ``vmin`` and ``vmax``.  We make the default
    `(3,4)` but since neither is one of `3/17`-th spaced
    values between `2` and `5`, the closest values: `52/17`
    and `67/17`, are instead chosen as the default::

        sage: range_slider(2, 5, 3/17, (3,4), 'alpha')
        Range Slider: alpha [2--|52/17==67/17|---5]

    Here we give a list::

        sage: range_slider([1..10], None, None, (3,7), 'alpha')
        Range Slider: alpha [1--|3==7|---10]
    """
    values=__old_make_values_list(vmin, vmax, step_size)
    return DiscreteSlider(range_slider=True, values=values, 
                          default=default, label=label, display_value=display_value)


def input_box(default=None, label=None, type=None, width=80, height=1, **kwargs):
    r"""
    An input box interactive control.  Use this in conjunction
    with the :func:`interact` command.

    INPUT:

    - ``default`` - an string; the default string for the input box
      and adapter.  If this is not a string, then the default string
      is set to ``repr(object)``.

    - ``label`` - a string; the label rendered to the left of the
      box.

    - ``type`` - a type; coerce inputs to this; this doesn't
      have to be an actual type, since anything callable will do.

    - ``height`` - an integer (default: 1); the number of rows.  
      If greater than 1 a value won't be returned until something
      outside the textarea is clicked.

    - ``width`` - an integer; width of text box in characters

    - ``kwargs`` - a dictionary; additional keyword options

    EXAMPLES::

        sage: input_box("2+2", 'expression')
        Interact input box labeled 'expression' with default value '2+2'
        sage: input_box('sage', label="Enter your name", type=str)
        Interact input box labeled 'Enter your name' with default value 'sage'   
        sage: input_box('Multiline\nInput',label='Click to change value',type=str,height=5)
        Interact input box labeled 'Click to change value' with default value 'Multiline\nInput'
    """
    from sagenb.misc.misc import Color

    if type is Color:
        # kwargs are only used if the type is Color.  
        widget=kwargs.get('widget', None)
        hide_box=kwargs.get('hide_box', False)
        return color_selector(default=default, label=label,
                              widget=widget, hide_box=hide_box)
    if type is str or height>1:
        return InputBox(default=default, label=label, width=width, height=height, keypress=False)
    else:
        return ExpressionBox(default=default, label=label, width=width, height=height,
            adapter=(lambda x, globs: type(x)) if type is not None else None)

def color_selector(default=(0,0,1), label=None,
                 widget='colorpicker', hide_box=False):
    r"""
    A color selector (also called a color chooser, picker, or
    tool) interactive control.  Use this with the :func:`interact`
    command.

    INPUT:

    - ``default`` - an instance of or valid constructor argument
      to :class:`Color` (default: (0,0,1)); the selector's default
      color; a string argument must be a valid color name (e.g.,
      'red') or HTML hex color (e.g., '#abcdef')

    - ``label`` - a string (default: None); the label rendered to
      the left of the selector.

    - ``widget`` - a string (default: 'jpicker'); the color
      selector widget to use; choices are 'colorpicker', 'jpicker'
      and 'farbtastic'

    - ``hide_box`` - a boolean (default: False); whether to hide
      the input box associated with the color selector widget

    EXAMPLES::

        sage: color_selector()
        Interact color selector labeled None, with default RGB color (0.0, 0.0, 1.0), widget 'jpicker', and visible input box
        sage: color_selector((0.5, 0.5, 1.0), widget='jpicker')
        Interact color selector labeled None, with default RGB color (0.5, 0.5, 1.0), widget 'jpicker', and visible input box
        sage: color_selector(default = Color(0, 0.5, 0.25))
        Interact color selector labeled None, with default RGB color (0.0, 0.5, 0.25), widget 'jpicker', and visible input box
        sage: color_selector('purple', widget = 'colorpicker')
        Interact color selector labeled None, with default RGB color (0.50..., 0.0, 0.50...), widget 'colorpicker', and visible input box
        sage: color_selector('crayon', widget = 'colorpicker')
        Traceback (most recent call last):
        ...
        ValueError: unknown color 'crayon'
        sage: color_selector('#abcdef', label='height', widget='jpicker')
        Interact color selector labeled 'height', with default RGB color (0.6..., 0.8..., 0.9...), widget 'jpicker', and visible input box
        sage: color_selector('abcdef', label='height', widget='jpicker')
        Traceback (most recent call last):
        ...
        ValueError: unknown color 'abcdef'
    """
    # TODO: look at various other widgets we used to support
        #'widget': 'jpicker, 'colorpicker', 'farbtastic' 
        #    -- we don't need to support each one right now
    if widget!='colorpicker':
        print "ColorSelector: Only widget='colorpicker' is supported; changing color widget"
    return ColorSelector(default=default, label=label, hide_input=hide_box)

def selector(values, label=None, default=None,
                 nrows=None, ncols=None, width=None, buttons=False):
    r"""
    A drop down menu or a button bar that when pressed sets a
    variable to a given value.  Use this in conjunction with the
    :func:`interact` command.

    We use the same command to create either a drop down menu or
    selector bar of buttons, since conceptually the two controls
    do exactly the same thing - they only look different.  If
    either ``nrows`` or ``ncols`` is given, then you get a buttons
    instead of a drop down menu.

    INPUT:

    - ``values`` - [val0, val1, val2, ...] or [(val0, lbl0),
      (val1,lbl1), ...] where all labels must be given or given as
      None.

    - ``label`` - a string (default: None); if given, this label
      is placed to the left of the entire button group

    - ``default`` - an object (default: 0); default value in values
      list

    - ``nrows`` - an integer (default: None); if given determines
      the number of rows of buttons; if given buttons option below
      is set to True

    - ``ncols`` - an integer (default: None); if given determines
      the number of columns of buttons; if given buttons option
      below is set to True

    - ``width`` - an integer (default: None); if given, all
      buttons are the same width, equal to this in HTML ex
      units's.

    - ``buttons`` - a bool (default: False); if True, use buttons

    EXAMPLES::

        sage: selector([1..5])    
        Drop down menu with 5 options
        sage: selector([1,2,7], default=2)
        Drop down menu with 3 options
        sage: selector([1,2,7], nrows=2)
        Button bar with 3 buttons
        sage: selector([1,2,7], ncols=2)
        Button bar with 3 buttons
        sage: selector([1,2,7], width=10)
        Drop down menu with 3 options
        sage: selector([1,2,7], buttons=True)
        Button bar with 3 buttons

    We create an :func:`interact` that involves computing charpolys of
    matrices over various rings::

        sage: @interact 
        ... def _(R=selector([ZZ,QQ,GF(17),RDF,RR]), n=(1..10)):
        ...      M = random_matrix(R, n)
        ...      show(M)
        ...      show(matrix_plot(M,cmap='Oranges'))
        ...      f = M.charpoly()
        ...      print f
        <html>...

    Here we create a drop-down::

        sage: @interact
        ... def _(a=selector([(2,'second'), (3,'third')])):
        ...       print a
        <html>...
    """
    if buttons:
        selector_type='button'
    else:
        selector_type='list'

    # in the old code, if a selector had a single button, then it was
    # actually a pushbutton (i.e., it would trigger an update every time
    # it was pushed)
    if selector_type=='button' and len(values)==1:
        if isinstance(values[0], (list,tuple)) and len(values[0])==2:
            buttonvalue, buttontext=values[0]
        else:
            buttonvalue, buttontext=values[0],str(values[0])
        return Button(value=buttonvalue, text=buttontext, default=buttonvalue, label=label, width=width)

    return Selector(values=values, default=default, label=label, selector_type=selector_type,
                    nrows=nrows, ncols=ncols, width=width)

def input_grid(nrows, ncols, default=None, label=None, to_value=None, width=4, type=None):
    r"""
    An input grid interactive control.  Use this in conjunction
    with the :func:`interact` command.

    INPUT:

    - ``nrows`` - an integer

    - ``ncols`` - an integer

    - ``default`` - an object; the default put in this input box

    - ``label`` - a string; the label rendered to the left of the
      box.

    - ``to_value`` - a function; the grid output (list of rows) is
      sent through this function.  This may reformat the data or
      coerce the type.

    - ``type`` - a function; each input box string is sent through
      this function before sending the list through to_value

    - ``width`` - an integer; size of each input box in characters

    NOTEBOOK EXAMPLE::

        @interact
        def _(m = input_grid(2,2, default = [[1,7],[3,4]],
                             label='M=', to_value=matrix), 
              v = input_grid(2,1, default=[1,2],
                             label='v=', to_value=matrix)):
            try:
                x = m\v
                html('$$%s %s = %s$$'%(latex(m), latex(x), latex(v)))
            except:
                html('There is no solution to $$%s x=%s$$'%(latex(m), latex(v)))

    EXAMPLES::

        sage: input_grid(2,2, default = 0, label='M')
        Interact 2 x 2 input grid control labeled M with default value 0
        sage: input_grid(2,2, default = [[1,2],[3,4]], label='M')
        Interact 2 x 2 input grid control labeled M with default value [[1, 2], [3, 4]]
        sage: input_grid(2,2, default = [[1,2],[3,4]], label='M', to_value=MatrixSpace(ZZ,2,2))
        Interact 2 x 2 input grid control labeled M with default value [[1, 2], [3, 4]]
        sage: input_grid(1, 3, default=[[1,2,3]], to_value=lambda x: vector(flatten(x)))
        Interact 1 x 3 input grid control labeled None with default value [[1, 2, 3]]

    """
    # this mirrors the code in input_box
    element_adapter = None
    evaluate = True
    if type is str:
        evaluate = False
    elif type is not None:
        element_adapter = lambda x, globs: type(x)

    if to_value is None:
        adapter=None
    else:
        adapter=lambda x,globs: to_value(x)

    return InputGrid(nrows=nrows, ncols=ncols, width=width,
                     default=default, label=label, adapter=adapter,
                     element_adapter=element_adapter, evaluate=evaluate)

def checkbox(default=True, label=None):
    """
    A checkbox interactive control.  Use this in conjunction with
    the :func:`interact` command.

    INPUT:

    - ``default`` - a bool (default: True); whether box should be
      checked or not

    - ``label`` - a string (default: None) text label rendered to
      the left of the box

    EXAMPLES::

        sage: checkbox(False, "Points")
        Interact checkbox labeled 'Points' with default value False
        sage: checkbox(True, "Points")
        Interact checkbox labeled 'Points' with default value True
        sage: checkbox(True)
        Interact checkbox labeled None with default value True
        sage: checkbox()
        Interact checkbox labeled None with default value True
    """
    return Checkbox(default=default, label=label)

def text_control(value=""):
    """
    Text that can be inserted among other :func:`interact` controls.

    INPUT:

    - ``value`` - HTML for the control

    EXAMPLES::

        sage: text_control('something')
        Text field: something
    """
    return HtmlBox(value=value)

imports = {"slider": slider, "range_slider": range_slider,
           "input_box": input_box, "color_selector": color_selector,
           "selector": selector, "input_grid": input_grid,
           "text_control": text_control, "checkbox": checkbox}




#################

# The following code is from https://github.com/sagemath/cloud/blob/master/sage_salvus.py
# copyright William Stein, distributed under the GPL v2+
# it doesn't quite work yet.

##########################################################
# A "%exercise" cell mode -- a first step toward
# automated homework.
##########################################################
class Exercise:
    def __init__(self, question, answer, check=None, hints=None):
        import sage.all, sage.matrix.all
        if not (isinstance(answer, (tuple, list)) and len(answer) == 2):
            if sage.matrix.all.is_Matrix(answer):
                default = sage.all.parent(answer)(0)
            else:
                default = ''
            answer = [answer, default]

        if check is None:
            R = sage.all.parent(answer[0])
            def check(attempt):
                return R(attempt) == answer[0]

        if hints is None:
            hints = ['','','',"The answer is %s."%answer[0]]

        self._question       = question
        self._answer         = answer
        self._check          = check
        self._hints          = hints

    def _check_attempt(self, attempt, interact):
        from sage.misc.all import walltime
        response = "<div class='well'>"
        try:
            r = self._check(attempt)
            if isinstance(r, tuple) and len(r)==2:
                correct = r[0]
                comment = r[1]
            else:
                correct = bool(r)
                comment = ''
        except TypeError, msg:
            response += "<h3 style='color:darkgreen'>Huh? -- %s (attempt=%s)</h3>"%(msg, attempt)
        else:
            if correct:
                response += "<h1 style='color:blue'>RIGHT!</h1>"
                if self._start_time:
                    response += "<h2 class='lighten'>Time: %.1f seconds</h2>"%(walltime()-self._start_time,)
                if self._number_of_attempts == 1:
                    response += "<h3 class='lighten'>You got it first try!</h3>"
                else:
                    response += "<h3 class='lighten'>It took you %s attempts.</h3>"%(self._number_of_attempts,)
            else:
                response += "<h3 style='color:darkgreen'>Not correct yet...</h3>"
                if self._number_of_attempts == 1:
                    response += "<h4 style='lighten'>(first attempt)</h4>"
                else:
                    response += "<h4 style='lighten'>(%s attempts)</h4>"%self._number_of_attempts

                if self._number_of_attempts > len(self._hints):
                    hint = self._hints[-1]
                else:
                    hint = self._hints[self._number_of_attempts-1]
                if hint:
                    response += "<span class='lighten'>(HINT: %s)</span>"%(hint,)
            if comment:
                response += '<h4>%s</h4>'%comment

        response += "</div>"

        interact.feedback = text_control(response,label='')

        return correct

    def ask(self, cb):
        from sage.misc.all import walltime
        self._start_time = walltime()
        self._number_of_attempts = 0
        attempts = []
        @interact(layout=[[('question',12)],[('attempt',12)], [('feedback',12)]])
        def f(question = ("<b>Question:</b>", text_control(self._question)),
              attempt   = ('<b>Answer:</b>',self._answer[1])):
            if 'attempt' in interact.changed() and attempt != '':
                attempts.append(attempt)
                if self._start_time == 0:
                    self._start_time = walltime()
                self._number_of_attempts += 1
                if self._check_attempt(attempt, interact):
                    cb({'attempts':attempts, 'time':walltime()-self._start_time})

def exercise(code):
    r"""
    Use the %exercise cell decorator to create interactive exercise
    sets.  Put %exercise at the top of the cell, then write Sage code
    in the cell that defines the following (all are optional):

    - a ``question`` variable, as an HTML string with math in dollar
      signs

    - an ``answer`` variable, which can be any object, or a pair
      (correct_value, interact control) -- see the docstring for
      interact for controls.

    - an optional callable ``check(answer)`` that returns a boolean or
      a 2-tuple

            (True or False, message),

      where the first argument is True if the answer is correct, and
      the optional second argument is a message that should be
      displayed in response to the given answer.  NOTE: Often the
      input "answer" will be a string, so you may have to use Integer,
      RealNumber, or sage_eval to evaluate it, depending
      on what you want to allow the user to do.

    - hints -- optional list of strings to display in sequence each
      time the user enters a wrong answer.  The last string is
      displayed repeatedly.  If hints is omitted, the correct answer
      is displayed after three attempts.

    NOTE: The code that defines the exercise is executed so that it
    does not impact (and is not impacted by) the global scope of your
    variables elsewhere in your session.  Thus you can have many
    %exercise cells in a single worksheet with no interference between
    them.

    The following examples further illustrate how %exercise works.

    An exercise to test your ability to sum the first $n$ integers::

        %exercise
        title    = "Sum the first n integers, like Gauss did."
        n        = randint(3, 100)
        question = "What is the sum $1 + 2 + \\cdots + %s$ of the first %s positive integers?"%(n,n)
        answer   = n*(n+1)//2

    Transpose a matrix::

        %exercise
        title    = r"Transpose a $2 \times 2$ Matrix"
        A        = random_matrix(ZZ,2)
        question = "What is the transpose of $%s?$"%latex(A)
        answer   = A.transpose()

    Add together a few numbers::

        %exercise
        k        = randint(2,5)
        title    = "Add %s numbers"%k
        v        = [randint(1,10) for _ in range(k)]
        question = "What is the sum $%s$?"%(' + '.join([str(x) for x in v]))
        answer   = sum(v)

    The trace of a matrix::

        %exercise
        title    = "Compute the trace of a matrix."
        A        = random_matrix(ZZ, 3, x=-5, y = 5)^2
        question = "What is the trace of $$%s?$$"%latex(A)
        answer   = A.trace()

    Some basic arithmetic with hints and dynamic feedback::

        %exercise
        k        = randint(2,5)
        title    = "Add %s numbers"%k
        v        = [randint(1,10) for _ in range(k)]
        question = "What is the sum $%s$?"%(' + '.join([str(x) for x in v]))
        answer   = sum(v)
        hints    = ['This is basic arithmetic.', 'The sum is near %s.'%(answer+randint(1,5)), "The answer is %s."%answer]
        def check(attempt):
            c = Integer(attempt) - answer
            if c == 0:
                return True
            if abs(c) >= 10:
                return False, "Gees -- not even close!"
            if c < 0:
                return False, "too low"
            if c > 0:
                return False, "too high"
    """
    f = closure(code)
    def g():
        x = f()
        return x.get('title',''), x.get('question', ''), x.get('answer',''), x.get('check',None), x.get('hints',None)

    title, question, answer, check, hints = g()
    obj = {}
    obj['E'] = Exercise(question, answer, check, hints)
    obj['title'] = title
    def title_control(t):
        return text_control('<h3 class="lighten">%s</h3>'%t)

    the_times = []
    @interact(layout=[[('go',1), ('title',11,'')],[('')], [('times',12, "<b>Times:</b>")]], flicker=True)
    def h(go    = button("&nbsp;"*5 + "Go" + "&nbsp;"*7, label='', icon='icon-refresh', classes="btn-large btn-success"),
          title = title_control(title),
          times = text_control('')):
        c = interact.changed()
        if 'go' in c or 'another' in c:
            interact.title = title_control(obj['title'])
            def cb(obj):
                the_times.append("%.1f"%obj['time'])
                h.times = ', '.join(the_times)

            obj['E'].ask(cb)

            title, question, answer, check, hints = g()   # get ready for next time.
            obj['title'] = title
            obj['E'] = Exercise(question, answer, check, hints)

def closure(code):
    """
    Wrap the given code block (a string) in a closure, i.e., a
    function with an obfuscated random name.

    When called, the function returns locals().
    """
    import uuid
    # TODO: strip string literals first
    code = ' ' + ('\n '.join(code.splitlines()))
    fname = "__" + str(uuid.uuid4()).replace('-','_')
    closure = "def %s():\n%s\n return locals()"%(fname, code)
    class Closure:
        def __call__(self):
            return self._f()
    c = Closure()
    salvus.execute(closure)
    c._f = salvus.namespace[fname]
    del salvus.namespace[fname]
    return c
#######################
## end salvus code
#######################
