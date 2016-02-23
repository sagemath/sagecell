cm-dir = build/components/codemirror/
codemirror-css-components = \
	$(cm-dir)/lib/codemirror.css \
	$(cm-dir)/addon/display/fullscreen.css \
	$(cm-dir)/addon/fold/foldgutter.css \
	$(cm-dir)/addon/hint/show-hint.css
colorpicker = static/colorpicker/js/colorpicker.js
cssmin = submodules/cssmin/src/cssmin.py
jquery-ui-tp   = submodules/jquery-ui-touch-punch/jquery.ui.touch-punch.min.js
sockjs-client  = js/sockjs.js
sockjs-url     = https://raw.githubusercontent.com/sockjs/sockjs-client/master/dist/sockjs.js

sage-root     := $(shell [ -n "$$SAGE_ROOT" ] && echo "$$SAGE_ROOT" || sage --root || echo "\$$SAGE_ROOT")
nb-static      = $(sage-root)/local/lib/python/site-packages/notebook/static
canvas3d       = $(sage-root)/local/lib/python/site-packages/sagenb-*.egg/sagenb/data/sage/js/canvas3d_lib.js
threejs        = $(sage-root)/local/share/threejs/build/three.js
threejs-control= $(sage-root)/local/share/threejs/examples/js/controls/OrbitControls.js
threejs-detect = $(sage-root)/local/share/threejs/examples/js/Detector.js
jsmol-path     = static/jsmol
jsmol          = $(jsmol-path)/JSmol.min.nojq.js


tos-default    = templates/tos_default.html
tos            = templates/tos.html
tos-static     = static/tos.html

embed-css      = static/sagecell_embed.css
sagecell-css   = static/sagecell.css

compute_server = build/compute_server_build.js
threed         = build/3d.js
threed-coffee  = js/3d.coffee
mpl-js         = build/mpl.js

all-components = \
	$(jsmol) \
	$(canvas3d) \
	$(compute_server) \
	$(colorpicker) \
	$(threejs) \
	$(threejs-control) \
	$(threejs-detect) \
	$(threed) \
	$(mpl-js) \
	js/sagecell.js
all-min-js     = static/all.min.js
all-css-components = \
	$(codemirror-css-components) \
	$(sagecell-css) \
	static/fontawesome.css
all-min-css    = static/all.min.css

all: submodules $(sockjs-client) $(all-min-js) $(all-min-css) $(embed-css) $(tos-static)

.PHONY: submodules $(tos-static)

submodules:
	if git submodule status | grep -q ^[+-]; then git submodule update --init > /dev/null; fi

$(sockjs-client):
	python -c "import urllib; urllib.urlretrieve('$(sockjs-url)', '$(sockjs-client)')"

$(jsmol):
	ln -sfn $(sage-root)/local/share/jsmol $(jsmol-path)
	ln -sf $(sage-root)/local/share/jmol/appletweb/SageMenu.mnu static/SageMenu.mnu

$(threed): $(threed-coffee)
	coffee -o build -c $(threed-coffee)

$(compute_server): js/*
	cp -a $(nb-static) build
	cp build/components/jquery/jquery.min.js static
	cp $(jquery-ui-tp) build/jquery-ui-tp.js
	cp -a js/* build
	cd build && r.js -o build.js

$(mpl-js):
	python -c "from matplotlib.backends.backend_webagg_core import FigureManagerWebAgg; print FigureManagerWebAgg.get_javascript().encode('utf8')" > $(mpl-js)

$(all-min-js): $(all-components)
	cat $(all-components) > $(all-min-js)

$(all-min-css): $(all-css-components)
	cat $(all-css-components) | python $(cssmin) > $(all-min-css)

$(embed-css): $(sagecell-css)
	sed -e 's/;/ !important;/g' < $(sagecell-css) > $(embed-css)

$(tos-static): $(tos-default)
	@[ -e $(tos) ] && cp $(tos) $(tos-static) || cp $(tos-default) $(tos-static)
