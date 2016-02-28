cm-dir = build/components/codemirror/
codemirror-css-components = \
	$(cm-dir)/lib/codemirror.css \
	$(cm-dir)/addon/display/fullscreen.css \
	$(cm-dir)/addon/fold/foldgutter.css \
	$(cm-dir)/addon/hint/show-hint.css
colorpicker = static/colorpicker/js/colorpicker.js
cssmin = submodules/cssmin/src/cssmin.py
jquery-ui-tp   = submodules/jquery-ui-touch-punch/jquery.ui.touch-punch.min.js

sage-root     := $(shell [ -n "$$SAGE_ROOT" ] && echo "$$SAGE_ROOT" || sage --root || echo "\$$SAGE_ROOT")

tos-default    = templates/tos_default.html
tos            = templates/tos.html
tos-static     = static/tos.html

embed-css      = static/sagecell_embed.css
sagecell-css   = static/sagecell.css

compute_server = build/compute_server_build.js
threed         = build/3d.js
threed-coffee  = js/3d.coffee

all-min-js     = static/all.min.js
all-css-components = \
	$(codemirror-css-components) \
	$(sagecell-css) \
	static/fontawesome.css
all-min-css    = static/all.min.css

all: submodules $(threed) $(all-min-js) $(all-min-css) $(embed-css) $(tos-static)

.PHONY: submodules $(tos-static)

submodules:
	if git submodule status | grep -q ^[+-]; then git submodule update --init > /dev/null; fi

build:
	-rm -r build
	cp -a $(sage-root)/local/lib/python/site-packages/notebook/static build
	cp $(sage-root)/local/lib/python/site-packages/sagenb-*.egg/sagenb/data/sage/js/canvas3d_lib.js \
	   $(sage-root)/local/share/threejs/build/three.js \
	   $(sage-root)/local/share/threejs/examples/js/controls/OrbitControls.js \
	   $(sage-root)/local/share/threejs/examples/js/Detector.js \
	   $(colorpicker) \
	   build
	ln -sfn $(sage-root)/local/share/jsmol static/jsmol
	ln -sf $(sage-root)/local/share/jmol/appletweb/SageMenu.mnu static/SageMenu.mnu
	cp static/jsmol/JSmol.min.nojq.js build/JSmol.js
	python -c "import urllib; urllib.urlretrieve('https://raw.githubusercontent.com/sockjs/sockjs-client/master/dist/sockjs.js', 'build/sockjs.js')"
	python -c "from matplotlib.backends.backend_webagg_core import FigureManagerWebAgg; print FigureManagerWebAgg.get_javascript().encode('utf8')" > build/mpl.js

$(threed): build $(threed-coffee)
	coffee -o build -c $(threed-coffee)

$(compute_server): build js/*
	cp build/components/jquery/jquery.min.js static
	cp $(jquery-ui-tp) build/jquery-ui-tp.js
	cp -a js/* build
	cd build && r.js -o build.js

$(all-min-js): $(compute_server)
	cp $(compute_server) $(all-min-js)

$(all-min-css): $(all-css-components)
	cat $(all-css-components) | python $(cssmin) > $(all-min-css)

$(embed-css): $(sagecell-css)
	sed -e 's/;/ !important;/g' < $(sagecell-css) > $(embed-css)

$(tos-static): $(tos-default)
	@[ -e $(tos) ] && cp $(tos) $(tos-static) || cp $(tos-default) $(tos-static)
