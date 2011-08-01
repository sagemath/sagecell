"""
This module defines a backwards-compatible API for interact controls from the first interact design.

"""

from interact_singlecell import *

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
        if num_steps <= 2:
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
                
        #Is the list of values is small (len<=50), use the whole list.
        #Otherwise, use part of the list.
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


def input_box(default=None, label=None, type=lambda x: x, width=80, height=1, **kwargs):
    r"""
    An input box interactive control.  Use this in conjunction
    with the :func:`interact` command.

    INPUT:

    - ``default`` - an object; the default put in this input box

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
    # TODO: make input_box take a type
    from sagenb.misc.misc import Color

    if type is Color:
        # kwargs are only used if the type is Color.  
        widget=kwargs.get('widget', None)
        hide_box=kwargs.get('hide_box', False)
        return color_selector(default=default, label=label, 
                              widget=widget, hide_box=hide_box)
    
    if not isinstance(default, basestring):
        default=repr(default)
    from sage.all import sage_eval
    if type is None:
        adapter = lambda x, globs: sage_eval(x, globs)
    elif type is str:
        adapter=lambda x, globs: x
    else:
        adapter = lambda x, globs: sage_eval(x, globs)
    return InputBox(default=default, width=width, 
                    label=label, adapter=adapter, height=height)

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
        
    return Selector(values=values, default=default, label=label, selector_type=selector_type,
                    nrows=nrows, ncols=ncols, width=width)

def input_grid(nrows, ncols, default=None, label=None, to_value=lambda x: x, width=4):
    r"""
    An input grid interactive control.  Use this in conjunction
    with the :func:`interact` command.

    INPUT:

    - ``nrows`` - an integer

    - ``ncols`` - an integer

    - ``default`` - an object; the default put in this input box

    - ``label`` - a string; the label rendered to the left of the
      box.

    - ``to_value`` - a list; the grid output (list of rows) is
      sent through this function.  This may reformat the data or
      coerce the type.

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
    def adapter(x, globs):
        return to_value(x)
    return InputGrid(nrows=nrows, ncols=ncols, width=width,
                     default=default, label=label, adapter=adapter)    

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
