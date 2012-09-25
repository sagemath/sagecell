"""
  MoinMoin - Sage Cell Parser

  @copyright: 2012 Jason Grout <jason-sage@creativetrax.com>
  @license: Modified BSD

Usage::

    {{{#!sagecell
    1+1
    }}}

Installation

Put this file in ``data/plugin/parser/``.

You must also something like these lines in your wikiconfig::

    html_head = '<script type="text/javascript" src="http://aleph.sagemath.org/static/jquery.min.js"></script>'
    html_head += '<script type="text/javascript" src="http://aleph.sagemath.org/static/embedded_sagecell.js"></script>'
    html_head += '<style type="text/css">.sagecell_output th, .sagecell_output td {border: none;}</style>'


"""
from MoinMoin.parser._ParserBase import ParserBase
from uuid import uuid4

Dependencies = ['user']

template="""
<div id="sagecell-%(random)s"><script type="text/x-sage">%(code)s</script></div>
<script type="text/javascript">
$(function () {
    sagecell.makeSagecell({inputLocation: '#sagecell-%(random)s'});
});
</script>
"""

class Parser(ParserBase):

    parsername = "sagecell"
    Dependencies = []

    def __init__(self, code, request, **kw):
        self.code = self.sanitize(code)
        self.request = request

    def sanitize(self, code):
        """
        Sanitize the code, for example, escape any instances of </script>
        """
        sanitized=code.replace("</script>", "<\/script>")
        return sanitized

    def format(self, formatter):
        self.request.write(formatter.rawHTML(template%{'random': uuid4(), 'code': self.code}))
