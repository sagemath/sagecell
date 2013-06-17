This extension defines a directive 'sagecellserver' which allows to embedd sage cell inside sphinx doc. To learn more about sage cell server visit: http://aleph.sagemath.org/static/about.html


Installation
=========
   1. Install this extension: 'python setup.py install --user'
   2. Move 'layout.html' to your '_templates' directory. Change sagecell paths if necessary
   3. Add 'icsecontrib.sagecellserver' to your extensions in 'conf.py'


How to use it
===========

Example of usage::

	.. sagecellserver::

	    sage: A = matrix([[1,1],[-1,1]])
	    sage: D = [vector([0,0]), vector([1,0])]
	    sage: @interact
	    sage: def f(A = matrix([[1,1],[-1,1]]), D = '[[0,0],[1,0]]', k=(3..17)):
	    ...       print "Det = ", A.det()
	    ...       D = matrix(eval(D)).rows()
	    ...       def Dn(k):
	    ...           ans = []
	    ...           for d in Tuples(D, k):
	    ...               s = sum(A^n*d[n] for n in range(k))
	    ...               ans.append(s)
	    ...           return ans
	    ...       G = points([v.list() for v in Dn(k)],size=50)
	    ...       show(G, frame=True, axes=False)


	.. end of output

Options
======

The sage prompts can be removed by adding setting 'prompt_tag' option to False::

	.. sagecellserver::
	    :prompt_tag: False

Setting 'prompt_tag' to True has same effect as removing ':prompt_tag:'.

During latex/pdf generation sagecell code can be displayed inside '\begin{verbatim}' and '\end{verbatim}' tags or as a single \textbf '***SAGE CELL***' message. This message is a reminder of sage cell exsistence. For example later this text can be manually replaced by screenshoot of sagcell example (mostly @interact example). 

This option is controlled using 'is_verbatim' option. Default is 'True'.::

	.. sagecellserver::
	    :is_verbatim: True





