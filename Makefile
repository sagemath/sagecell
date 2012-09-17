wrap-jquery    = ./wrap-jquery
all-css        = static/all.css
all-js         = static/all.js
all-min-css    = static/all.min.css
all-min-js     = static/all.min.js
colorpicker    = static/colorpicker/js/colorpicker.js
compute_server = static/compute_server.js
jmol           = static/jmol
jmol-js        = $(jmol)/appletweb/Jmol.js
jquery         = static/jquery.min.js
jquery-ui      = static/jquery-ui/js/jquery-ui-1.8.21.custom.min.js
sagecell       = static/sagecell.js
sagecell-css   = static/sagecell.css
sockjs-client  = static/sockjs.js
codemirror-css = submodules/codemirror2/lib/codemirror.css
codemirror     = submodules/codemirror2/lib/codemirror.js
codemirror-py  = submodules/codemirror2/mode/python/python.js
jquery-ui-tp   = submodules/jquery-ui-touch-punch/jquery.ui.touch-punch.min.js
cssmin         = submodules/cssmin/src/cssmin.py
jsmin          = submodules/jsmin/jsmin.c
jsmin-bin      = submodules/jsmin-bin
wrap-js        = static/wrap.js
sage-root     := $(shell [ -n "$$SAGE_ROOT" ] && echo "$$SAGE_ROOT" || sage --root || echo "\$$SAGE_ROOT")
ip-js          = $(sage-root)/local/lib/python2.7/site-packages/IPython/frontend/html/notebook/static/js
ip-namespace   = $(ip-js)/namespace.js
ip-events      = $(ip-js)/events.js
ip-utils       = $(ip-js)/utils.js
ip-kernel      = $(ip-js)/kernel.js
jquery-url     = http://code.jquery.com/jquery-1.7.2.min.js
sockjs-url     = http://cdn.sockjs.org/sockjs-0.3.js
jmol-sage      = $(sage-root)/local/share/jmol

all: submodules $(jquery) $(all-min-js) $(all-min-css)

.PHONY: submodules
submodules:
	if git submodule status | grep -q ^[+-]; then git submodule update --init > /dev/null; fi

$(jquery):
	python -c "import urllib; urllib.urlretrieve('$(jquery-url)', '$(jquery)')"

$(all-min-js): $(jsmin-bin) $(all-js)
	$(jsmin-bin) < $(all-js) > $(all-min-js)

$(all-js): $(ip-namespace) $(wrap-js) $(codemirror) $(codemirror-py) \
           $(jmol-js) $(sockjs-client) $(compute_server) $(sagecell)
	cat $(codemirror) $(codemirror-py) $(jmol-js) $(ip-namespace) $(wrap-js) > $(all-js)
	echo ';' >> $(all-js)
	cat $(sockjs-client) $(compute_server) $(sagecell) >> $(all-js)

$(wrap-js): $(wrap-jquery) $(ip-events) $(ip-utils) $(ip-kernel) \
            $(jquery-ui) $(jquery-ui-tp) $(colorpicker)
	cat $(ip-events) $(ip-utils) $(ip-kernel) $(jquery-ui) $(jquery-ui-tp) \
	    $(colorpicker) | $(wrap-jquery) > $(wrap-js)

$(all-min-css): $(codemirror-css) $(sagecell-css)
	cat $(codemirror-css) $(sagecell-css) | python $(cssmin) > $(all-min-css)

$(jsmin-bin):  $(jsmin)
	gcc -o $(jsmin-bin) $(jsmin)

$(jmol-js): $(jmol-sage)
	rm -f $(jmol)
	ln -s $(jmol-sage) $(jmol)

$(sockjs-client):
	python -c "import urllib; urllib.urlretrieve('$(sockjs-url)', '$(sockjs-client)')"
