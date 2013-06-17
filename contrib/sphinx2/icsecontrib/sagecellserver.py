#!/usr/bin/env python
# -*- coding: utf-8 -*-

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.compat import Directive



class sagecellserver(nodes.General, nodes.Element): 
    pass


def html_visit_sagecellserver_node(self, node):
    self.body.append("<div class='sage'>")
    self.body.append("<script type='text/x-sage'>")	    
    self.body.append(node['python_code'])    
    self.body.append("</script>")    
    self.body.append("</div>")	


def html_depart_sagecellserver_node(self, node):
    pass


def latex_visit_sagecellserver_node(self, node):
    if node["is_verbatim"]  == "True":
        self.body.append("\n\n")
        self.body.append("\\begin{verbatim}\n")
        self.body.append(node['python_code'])
        self.body.append("\n\end{verbatim}")
        self.body.append("\n\n")
    else:
        self.body.append("\n\\textbf{***SAGE CELL***}\n")


def latex_depart_sagecellserver_node(self, node):
    pass


class SageCellServer(Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 2
    option_spec = {
        "prompt_tag": directives.unchanged,
        "is_verbatim": directives.unchanged,
    }
	
    def run(self):               
        if "prompt_tag" in self.options:
            annotation = self.options.get("prompt_tag")
        else:
            annotation = "False"

        if "is_verbatim" in self.options:
            is_verbatim = self.options.get("is_verbatim")
        else:
            is_verbatim = "True"

        content_list = self.content

        if annotation == "False":
            content_list = map(lambda x: x.replace("sage: ", "").replace("...   ", ""), content_list)
        
        node = sagecellserver()    
        node['is_verbatim'] = is_verbatim
        node['python_code'] = '\n'.join(content_list)        
    
        return [node]		


def setup(app):
    app.add_node(sagecellserver, 
                               html = (html_visit_sagecellserver_node, html_depart_sagecellserver_node),
                               latex = (latex_visit_sagecellserver_node, latex_depart_sagecellserver_node))
    app.add_directive("sagecellserver", SageCellServer)



