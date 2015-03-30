# -*- encoding: utf-8 -*-
"""
SageMathCell Backend for the Sage Rich Output System

This module defines the SageMathCell backends for
:mod:`sage.repl.rich_output`.
"""

#*****************************************************************************
#       Copyright (C) 2015 Andrey Novoseltsev <novoselt@gmail.com>
#
#  Distributed under the terms of the GNU General Public License (GPL)
#  as published by the Free Software Foundation; either version 2 of
#  the License, or (at your option) any later version.
#                  http://www.gnu.org/licenses/
#*****************************************************************************

import os
from sage.repl.rich_output.backend_base import BackendBase
from sage.repl.rich_output.output_catalog import *


from misc import display_message


class BackendCell(BackendBase):
    """
    Backend for SageMathCell

    EXAMPLES::

        sage: from sage.repl.rich_output.backend_cell import BackendCell
        sage: BackendCell()
        SageMathCell
    """
    
    def _repr_(self):
        """
        Return a string representation

        OUTPUT:

        String.

        EXAMPLES::

            sage: from sage.repl.rich_output.backend_cell import BackendCell
            sage: backend = BackendCell()
            sage: backend._repr_()
            'SageMathCell'
        """
        return 'SageMathCell'

    def display_file(path, mimetype=None):
        path = os.path.relpath(path)
        if mimetype is None:
            mimetype = 'application/x-file'
        msg = {'text/plain': '%s file'%mimetype, mimetype: path}
        display_message(msg)
        sys._sage_.sent_files[path] = os.path.getmtime(path)

    def display_html(s):
        display_message({'text/plain': 'html', 'text/html': s})
                                      
    def display_immediately(self, plain_text, rich_output):
        """
        Show output immediately.

        This method is similar to the rich output :meth:`displayhook`,
        except that it can be invoked at any time.

        INPUT:

        Same as :meth:`displayhook`.

        OUTPUT:

        This method does not return anything.

        EXAMPLES::

            sage: from sage.repl.rich_output.output_basic import OutputPlainText
            sage: plain_text = OutputPlainText.example()
            sage: from sage.repl.rich_output.backend_cell import BackendCell
            sage: backend = BackendCell()
            sage: _ = backend.display_immediately(plain_text, plain_text)
            Example plain text output
        """
        if isinstance(rich_output, (OutputPlainText, OutputAsciiArt)):
            rich_output.print_to_stdout()
        elif isinstance(rich_output, OutputLatex):
            display_html(rich_output.mathjax())
            
        elif isinstance(rich_output, OutputImageGif):
            self.display_file(rich_output.gif.filename(), 'text/image-filename')
        elif isinstance(rich_output, OutputImageJpg):
            self.display_file(rich_output.jpg.filename(), 'text/image-filename')
        elif isinstance(rich_output, OutputImagePdf):
            self.display_file(rich_output.pdf.filename(), 'text/image-filename')
        elif isinstance(rich_output, OutputImagePng):
            self.display_file(rich_output.png.filename(), 'text/image-filename')
        elif isinstance(rich_output, OutputImageSvg):
            self.display_file(rich_output.svg.filename(), 'text/image-filename')
            
        elif isinstance(rich_output, OutputSceneCanvas3d):
            self.display_file(rich_output.canvas3d.filename(), 'text/image-filename')

        elif isinstance(rich_output, OutputSceneJmol):
            rich_output.embed()
            
        else:
            raise TypeError('rich_output type not supported, got {0}'.format(rich_output))
    
    def supported_output(self):
        """
        Return the outputs that are supported by SageMathCell backend.

        OUTPUT:

        Iterable of output container classes, that is, subclass of
        :class:`~sage.repl.rich_output.output_basic.OutputBase`).
        The order is ignored.

        EXAMPLES::

            sage: raise
            sage: from sage.repl.rich_output.backend_ipython import BackendIPythonCommandline
            sage: backend = BackendIPythonCommandline()
            sage: supp = backend.supported_output();  supp     # random output
            set([<class 'sage.repl.rich_output.output_graphics.OutputImageGif'>, 
                 ...,
                 <class 'sage.repl.rich_output.output_graphics.OutputImagePng'>])
            sage: from sage.repl.rich_output.output_basic import OutputLatex
            sage: OutputLatex in supp
            True
        """
        return set([
            OutputPlainText,
            OutputAsciiArt,
            OutputLatex,
            
            OutputImageGif,
            OutputImageJpg,
            OutputImagePdf,
            OutputImagePng,
            OutputImageSvg,
            
            OutputSceneCanvas3d,
            #OutputSceneJmol,
            #OutputSceneWavefront,
        ])
