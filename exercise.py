from interact_sagecell import interact,Button,HtmlBox, UpdateButton


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

    def _check_attempt(self, attempt):

        from sage.misc.all import walltime
        response = "<div class='well'>"
        correct=False
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

        #interact.feedback = response#HtmlBox(response,label='')

        return correct, response

    def ask(self, cb):
        from sage.misc.all import walltime
        self._start_time = walltime()
        self._number_of_attempts = 0
        attempts = []
        @interact(layout=[[('question',12)],[('attempt',12)], [('submit',12)],[('feedback',12)]])
        def f(fself, question = ("Question:", HtmlBox(self._question)),
              attempt   = ('Answer:',self._answer[1]),
              submit = UpdateButton('Submit'),
              feedback = HtmlBox('')):
            if 'attempt' in fself._changed and attempt != '':
                attempts.append(attempt)
                if self._start_time == 0:
                    self._start_time = walltime()
                self._number_of_attempts += 1
                correct, fself.feedback = self._check_attempt(attempt)
                if correct:
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
    title_html = '<h3>%s</h3>'

    the_times = []
    @interact(layout=[[('go',1), ('title',11,'')],[('_output')], [('times',12, "<b>Times:</b>")]])#, flicker=True)
    def h(self, go = Button(text="New Question", label=''),
          title = HtmlBox(title_html%title),
          times = HtmlBox('No times')):
        c = self._changed
        if 'go' in c or 'another' in c:
            self.title = title
            def cb(obj):
                the_times.append("%.1f"%obj['time'])
                h.times = ', '.join(the_times)

            obj['E'].ask(cb)
            title, question, answer, check, hints = g()   # get ready for next time.
                                                          #print title, question, answer, check, hints
            obj['title'] = title_html%title
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
    get_ipython().run_cell(closure)
    import sys
    c._f = sys._sage_.namespace[fname]
    del sys._sage_.namespace[fname]
    return c
#######################
## end salvus code
#######################

imports = {'exercise': exercise}
