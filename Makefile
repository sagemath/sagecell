wrap-jquery    = ./wrap-jquery
fix-wrap       = ./fix-wrap.py
all-css        = static/all.css
all-js         = static/all.js
all-min-css    = static/all.min.css
all-min-js     = static/all.min.js
colorpicker    = static/colorpicker/js/colorpicker.js
compute_server = static/compute_server.js
jmol           = static/jmol
jmol-js        = $(jmol)/appletweb/Jmol.js
jquery         = static/jquery.min.js
jquery-ui      = static/jquery-ui/js/jquery-ui-1.10.2.custom.min.js
tos-default    = templates/tos_default.html
tos            = templates/tos.html
tos-static     = static/tos.html
sagecell       = static/sagecell.js
sagecell-css   = static/sagecell.css
sockjs-client  = static/sockjs.js
codemirror-cat = static/codemirror.js
codemirror-css = submodules/codemirror/lib/codemirror.css
codemirror     = submodules/codemirror/lib/codemirror.js
cm-brackets    = submodules/codemirror/addon/edit/matchbrackets.js
cm-python-mode = submodules/codemirror/mode/python/python.js
cm-xml-mode    = submodules/codemirror/mode/xml/xml.js
cm-html-mode   = submodules/codemirror/mode/htmlmixed/htmlmixed.js
cm-js-mode     = submodules/codemirror/mode/javascript/javascript.js
cm-css-mode    = submodules/codemirror/mode/css/css.js
cm-r-mode      = submodules/codemirror/mode/r/r.js
cm-runmode     = submodules/codemirror/addon/runmode/runmode.js
cm-colorize    = submodules/codemirror/addon/runmode/colorize.js
jquery-ui-tp   = submodules/jquery-ui-touch-punch/jquery.ui.touch-punch.min.js
cssmin         = submodules/cssmin/src/cssmin.py
jsmin          = submodules/jsmin/jsmin.c
jsmin-bin      = submodules/jsmin-bin
wrap-js        = static/wrap.js
sage-root     := $(shell [ -n "$$SAGE_ROOT" ] && echo "$$SAGE_ROOT" || sage --root || echo "\$$SAGE_ROOT")
ip-js          = $(shell $(sage-root)/sage -python -c "import os,IPython; print '/'+os.path.join(*IPython.__file__.split(os.sep)[:-1]+'frontend/html/notebook/static/js'.split(os.sep))")
ip-namespace   = $(ip-js)/namespace.js
ip-events      = $(ip-js)/events.js
ip-utils       = $(ip-js)/utils.js
ip-kernel      = $(ip-js)/kernel.js
jquery-url     = http://code.jquery.com/jquery-1.7.2.min.js
sockjs-url     = http://cdn.sockjs.org/sockjs-0.3.js
jmol-sage      = $(sage-root)/local/share/jmol

all: submodules $(jquery) $(all-min-js) $(all-min-css) $(tos-static)

.PHONY: submodules $(tos-static)

submodules:
	if git submodule status | grep -q ^[+-]; then git submodule update --init > /dev/null; fi

$(jquery):
	python -c "import urllib; urllib.urlretrieve('$(jquery-url)', '$(jquery)')"

$(all-min-js): $(jsmin-bin) $(all-js)
	$(jsmin-bin) < $(all-js) > $(all-min-js)

$(codemirror-cat): $(codemirror) $(cm-python-mode) \
           $(cm-xml-mode) $(cm-html-mode) $(cm-js-mode) $(cm-css-mode) \
           $(cm-r-mode) $(cm-brackets) $(cm-runmode) $(cm-colorize)
	cat $(codemirror) $(cm-brackets) $(cm-python-mode) $(cm-xml-mode) \
	    $(cm-html-mode) $(cm-js-mode) $(cm-css-mode) $(cm-r-mode) \
	    $(cm-runmode) $(cm-colorize) > $(codemirror-cat)

$(all-js): $(ip-namespace) $(wrap-js) $(codemirror-cat) $(jmol-js) \
           $(sockjs-client) $(compute_server) $(sagecell)
	cat $(codemirror-cat) $(jmol-js) $(ip-namespace) $(wrap-js) > $(all-js)
	echo ';' >> $(all-js)
	cat $(sockjs-client) $(compute_server) $(sagecell) >> $(all-js)

$(wrap-js): $(wrap-jquery) $(ip-events) $(ip-utils) $(ip-kernel) \
            $(jquery-ui) $(jquery-ui-tp) $(colorpicker)
	cat $(ip-events) $(ip-utils) $(ip-kernel) $(jquery-ui) $(jquery-ui-tp) \
	    $(colorpicker) | $(wrap-jquery) > $(wrap-js)
	python $(fix-wrap) $(wrap-js)

$(all-min-css): $(codemirror-css) $(sagecell-css)
	cat $(codemirror-css) $(sagecell-css) | python $(cssmin) > $(all-min-css)

$(jsmin-bin):  $(jsmin)
	gcc -o $(jsmin-bin) $(jsmin)

$(jmol-js): $(jmol-sage)
	rm -f $(jmol)
	ln -s $(jmol-sage) $(jmol)

$(tos-static): $(tos)
	@[ -e $(tos) ] && cp $(tos) $(tos-static) || cp $(tos-default) $(tos-static)

$(sockjs-client):
	python -c "import urllib; urllib.urlretrieve('$(sockjs-url)', '$(sockjs-client)')"
