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
import stat
import sys
import tempfile


from sage.repl.rich_output.backend_ipython import BackendIPython
from sage.repl.rich_output.output_catalog import *


from misc import display_file, display_html, display_message


class BackendCell(BackendIPython):
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

    def display_immediately(self, plain_text, rich_output):
        """
        Show output immediately.

        This method is similar to the rich output :meth:`displayhook`,
        except that it can be invoked at any time.

        INPUT:

        Same as :meth:`displayhook`.

        EXAMPLES::

            sage: from sage.repl.rich_output.output_basic import OutputPlainText
            sage: plain_text = OutputPlainText.example()
            sage: from sage.repl.rich_output.backend_cell import BackendCell
            sage: backend = BackendCell()
            sage: _ = backend.display_immediately(plain_text, plain_text)
            Example plain text output
        """
        if isinstance(rich_output, OutputPlainText):
            return {u'text/plain': rich_output.text.get()}, {}
        if isinstance(rich_output, OutputAsciiArt):
            return {u'text/plain': rich_output.ascii_art.get()}, {}

        if isinstance(rich_output, OutputLatex):
            display_html(rich_output.mathjax())
        elif isinstance(rich_output, OutputHtml):
            display_html(rich_output.html.get())

        elif isinstance(rich_output, OutputImageGif):
            display_file(rich_output.gif.filename(), 'text/image-filename')
        elif isinstance(rich_output, OutputImageJpg):
            display_file(rich_output.jpg.filename(), 'text/image-filename')
        elif isinstance(rich_output, OutputImagePdf):
            display_file(rich_output.pdf.filename(), 'text/image-filename')
        elif isinstance(rich_output, OutputImagePng):
            display_file(rich_output.png.filename(), 'text/image-filename')
        elif isinstance(rich_output, OutputImageSvg):
            display_file(rich_output.svg.filename(), 'text/image-filename')
            
        elif isinstance(rich_output, OutputSceneCanvas3d):
            display_file(
                rich_output.canvas3d.filename(), 'application/x-canvas3d')
        elif isinstance(rich_output, OutputSceneJmol):
            path = tempfile.mkdtemp(suffix=".jmol", dir=".")
            os.chmod(path, stat.S_IRWXU + stat.S_IXGRP + stat.S_IXOTH)
            rich_output.scene_zip.save_as(os.path.join(path, 'scene.zip'))
            rich_output.preview_png.save_as(os.path.join(path, 'preview.png'))
            display_message({'text/plain': 'application/x-jmol file',
                             'application/x-jmol': path})
        elif isinstance(rich_output, OutputSceneThreejs):
            path = tempfile.mkstemp(suffix='.html', dir='.')[1]
            path = os.path.relpath(path)
            rich_output.html.save_as(path)
            os.chmod(path, stat.S_IRUSR + stat.S_IRGRP + stat.S_IROTH)
            display_html("""
                <iframe
                    scrolling="no"
                    src="cell://{}"
                    style="
                        border: 1px silver solid;
                        height: 500px;
                        min-width: 500px;
                        width: 75%;
                        "
                    >
                </iframe>
                """.format(path))
            sys._sage_.sent_files[path] = os.path.getmtime(path)
            
        else:
            raise TypeError('rich_output type not supported, got {0}'.format(rich_output))
        return {u'text/plain': None}, {}
        
    displayhook = display_immediately
    
    def supported_output(self):
        """
        Return the outputs that are supported by SageMathCell backend.

        OUTPUT:

        Iterable of output container classes, that is, subclass of
        :class:`~sage.repl.rich_output.output_basic.OutputBase`).
        The order is ignored.

        EXAMPLES::

            sage: from sage.repl.rich_output.backend_cell import BackendCell
            sage: backend = BackendCell()
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
            OutputHtml,
            
            OutputImageGif,
            OutputImageJpg,
            OutputImagePdf,
            OutputImagePng,
            OutputImageSvg,
            
            OutputSceneCanvas3d,
            OutputSceneJmol,
            OutputSceneThreejs,
            #OutputSceneWavefront,
        ])

    def threejs_offline_scripts(self):
        """
        Return script tags for ``viewer=threejs`` with ``online=False``.

        OUTPUT:

        - a string

        EXAMPLES::

            sage: from sage.repl.rich_output.backend_cell import BackendCell
            sage: backend = BackendCell()
            sage: backend.threejs_offline_scripts()
            '...<script ...</script>...'
        """
        return """
<script src="/static/threejs/three.min.js"></script>
<script src="/static/threejs/OrbitControls.js"></script>
        """
