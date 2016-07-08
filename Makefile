sage-root := $(shell [ -n "$$SAGE_ROOT" ] && echo "$$SAGE_ROOT" || sage --root || echo "\$$SAGE_ROOT")
threed-coffee = js/3d.coffee
threed = build/3d.js
all-min-js = static/embedded_sagecell.js

sagecell-css = static/sagecell.css
all-min-css = build/all.min.css
embed-css = static/sagecell_embed.css

tos-default = templates/tos_default.html
tos = templates/tos.html
tos-static = static/tos.html

all: submodules $(threed) $(all-min-js) $(all-min-css) $(embed-css) $(tos-static)

.PHONY: submodules $(tos-static)

submodules:
	if git submodule status | grep -q ^[+-]; then git submodule update --init > /dev/null; fi

build:
	-rm -r build
	cp -a $(sage-root)/local/lib/python/site-packages/notebook/static build
	cp $(sage-root)/local/lib/python/site-packages/sagenb/data/sage/js/canvas3d_lib.js \
	   $(sage-root)/local/share/threejs/build/three.js \
	   $(sage-root)/local/share/threejs/examples/js/controls/OrbitControls.js \
	   $(sage-root)/local/share/threejs/examples/js/Detector.js \
	   static/colorpicker/js/colorpicker.js \
	   build
	ln -sfn $(sage-root)/local/share/jsmol static/jsmol
	ln -sf $(sage-root)/local/share/jmol/appletweb/SageMenu.mnu static/SageMenu.mnu
	cp static/jsmol/JSmol.min.nojq.js build/JSmol.js
	wget -P build \
		https://raw.githubusercontent.com/sockjs/sockjs-client/master/dist/sockjs.js \
		https://raw.githubusercontent.com/requirejs/domReady/latest/domReady.js \
		https://raw.githubusercontent.com/requirejs/text/latest/text.js
	python -c "from matplotlib.backends.backend_webagg_core import FigureManagerWebAgg; print FigureManagerWebAgg.get_javascript().encode('utf8')" > build/mpl.js

$(threed): build $(threed-coffee)
	coffee -o build -c $(threed-coffee)

$(all-min-js): build $(all-min-css) js/*
	cp build/components/jquery/jquery.min.js static
	cp submodules/jquery-ui-touch-punch/jquery.ui.touch-punch.min.js build/jquery-ui-tp.js
	cp -a js/* build
	cd build && r.js -o build.js
	cp build/main_build.js $(all-min-js)

$(all-min-css): build $(sagecell-css)
	cp -a build/components/jquery-ui/themes/smoothness/* static
	r.js -o cssIn=static/main.css out=$(all-min-css)

$(embed-css): $(sagecell-css)
	sed -e 's/;/ !important;/g' < $(sagecell-css) > $(embed-css)

$(tos-static): $(tos-default)
	@[ -e $(tos) ] && cp $(tos) $(tos-static) || cp $(tos-default) $(tos-static)
