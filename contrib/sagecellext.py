"""
Sphinx extension to insert sagecell in sphinx docs.

Add the following lines to your layout.html file (e.g., in source/_templates)

######### BEGIN layout.html ###############
{% extends "!layout.html" %}

{%- block extrahead %}
    <script type="text/javascript" src="http://aleph.sagemath.org/static/jquery.min.js"></script>
    <script type="text/javascript" src="http://aleph.sagemath.org/static/embedded_sagecell.js"></script>
    <style type="text/css">.sagecell_output th, .sagecell_output td {border: none;}</style>
{% endblock %}

############ END ########################

Add the directory of this file to the path in conf.py

import sys, os
sys.path.append(os.path.abspath('path/to/file'))

Add sagecellext to the list of extensions in conf.py.

extensions = ['sphinx.ext.mathjax', 'sphinx.ext.graphviz', 'sagecellext']


USAGE:
 .. sagecell::

    1+1
    print "hello world"


"""
from docutils import nodes, utils
from docutils.nodes import Body, Element
from docutils.parsers.rst import directives

from sphinx.util.nodes import set_source_info
from sphinx.util.compat import Directive

class sagecell(Body, Element):
   pass


class Sagecell(Directive):

    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False


    def run(self):
        node = sagecell()
        node['code'] = u'\n'.join(self.content)
        return [node]

def html_sagecell(self, node):
    """
    Convert block to the script here.
    """    
    from uuid import uuid4

    template= """
<div id="sagecell-%(random)s"><script type="text/x-sage">%(code)s</script></div>
<script type="text/javascript">
$(function () {
    sagecell.makeSagecell({inputLocation: '#sagecell-%(random)s'});
});
</script>
"""
    self.body.append(template%{'random': uuid4(), 'code': node['code']})
    raise nodes.SkipNode


def setup(app):
    app.add_node(sagecell,
                 html=(html_sagecell, None))

    app.add_directive('sagecell', Sagecell)
