fix-js         = ./fix-js.py
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
embed-css      = static/sagecell_embed.css
sockjs-client  = static/sockjs.js
codemirror-cat = static/codemirror.js
codemirror-css = submodules/codemirror/lib/codemirror.css
cm-dir         = submodules/codemirror/
cm-compress    = bin/compress
codemirror     = lib/codemirror.js
cm-brackets    = addon/edit/matchbrackets.js
cm-python-mode = mode/python/python.js
cm-xml-mode    = mode/xml/xml.js
cm-html-mode   = mode/htmlmixed/htmlmixed.js
cm-js-mode     = mode/javascript/javascript.js
cm-css-mode    = mode/css/css.js
cm-r-mode      = mode/r/r.js
cm-runmode     = addon/runmode/runmode.js
cm-colorize    = addon/runmode/colorize.js
cm-hint-js     = addon/hint/show-hint.js
cm-hint-css    = submodules/codemirror/addon/hint/show-hint.css
jquery-ui-tp   = submodules/jquery-ui-touch-punch/jquery.ui.touch-punch.min.js
cssmin         = submodules/cssmin/src/cssmin.py
jsmin          = submodules/jsmin/jsmin.c
jsmin-bin      = submodules/jsmin-bin
wrap-js        = static/wrap.js
sage-root     := $(shell [ -n "$$SAGE_ROOT" ] && echo "$$SAGE_ROOT" || sage --root || echo "\$$SAGE_ROOT")
ip-static      = $(shell $(sage-root)/sage -python -c "import os,IPython; print '/'+os.path.join(*IPython.__file__.split(os.sep)[:-1]+'html/static/'.split(os.sep))")
ip-namespace   = $(ip-static)/base/js/namespace.js
ip-events      = $(ip-static)/base/js/events.js
ip-utils       = $(ip-static)/base/js/utils.js
ip-kernel      = $(ip-static)/services/kernels/js/kernel.js
jquery-url     = http://code.jquery.com/jquery-2.0.3.min.js
sockjs-url     = http://cdn.sockjs.org/sockjs-0.3.js
jmol-sage      = $(sage-root)/local/share/jmol
canvas3d       = $(sage-root)/devel/sagenb/sagenb/data/sage/js/canvas3d_lib.js

all: submodules $(jquery) $(all-min-js) $(all-min-css) $(tos-static) $(embed-css)

.PHONY: submodules $(tos-static)

submodules:
	if git submodule status | grep -q ^[+-]; then git submodule update --init > /dev/null; fi

$(jquery):
	python -c "import urllib; urllib.urlretrieve('$(jquery-url)', '$(jquery)')"

$(all-min-js): $(jsmin-bin) $(all-js) $(codemirror-cat)
	cp $(codemirror-cat) $(all-min-js)
	$(jsmin-bin) < $(all-js) >> $(all-min-js)
$(codemirror-cat): $(cm-dir)/$(cm-compress) $(cm-dir)/$(codemirror) $(cm-dir)/$(cm-python-mode) \
           $(cm-dir)/$(cm-xml-mode) $(cm-dir)/$(cm-html-mode) $(cm-dir)/$(cm-js-mode) \
           $(cm-dir)/$(cm-css-mode) $(cm-dir)/$(cm-r-mode) $(cm-dir)/$(cm-brackets) \
           $(cm-dir)/$(cm-runmode) $(cm-dir)/$(cm-colorize) $(cm-dir)/$(cm-hint-js)
	cd $(cm-dir); $(cm-compress) $(codemirror) $(cm-brackets) $(cm-python-mode) $(cm-xml-mode) \
	    $(cm-html-mode) $(cm-js-mode) $(cm-css-mode) $(cm-r-mode) \
	    $(cm-runmode) $(cm-colorize) $(cm-hint-js) > ../../$(codemirror-cat)

$(all-js): $(ip-namespace) $(wrap-js) $(jmol-js) $(canvas3d)\
           $(sockjs-client) $(compute_server) $(sagecell)
	cat $(jmol-js) $(canvas3d) $(ip-namespace) $(wrap-js) > $(all-js)
	echo ';' >> $(all-js)
	cat $(sockjs-client) $(compute_server) $(sagecell) >> $(all-js)

$(wrap-js): $(ip-events) $(ip-utils) $(ip-kernel) $(jquery-ui) $(jquery-ui-tp) \
            $(colorpicker)
	cat $(ip-events) $(ip-utils) $(ip-kernel) $(jquery-ui) $(jquery-ui-tp) \
	    $(colorpicker) > $(wrap-js)
	python $(fix-js) $(wrap-js)

$(all-min-css): $(codemirror-css) $(cm-hint-css) $(sagecell-css)
	cat $(codemirror-css) $(cm-hint-css) $(sagecell-css) | python $(cssmin) > $(all-min-css)

$(jsmin-bin):  $(jsmin)
	gcc -o $(jsmin-bin) $(jsmin)

$(jmol-js): $(jmol-sage)
	rm -f $(jmol)
	ln -s $(jmol-sage) $(jmol)

$(tos-static): $(tos-default)
	@[ -e $(tos) ] && cp $(tos) $(tos-static) || cp $(tos-default) $(tos-static)

$(sockjs-client):
	python -c "import urllib; urllib.urlretrieve('$(sockjs-url)', '$(sockjs-client)')"

$(embed-css): $(sagecell-css)
	sed -e 's/;/ !important;/g' < $(sagecell-css) > $(embed-css)
