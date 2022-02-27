sage-root := $(shell [ -n "$$SAGE_ROOT" ] && echo "$$SAGE_ROOT" || sage --root || echo "\$$SAGE_ROOT")
all-min-js = static/embedded_sagecell.js
all-min-js-map = static/embedded_sagecell.js.map
all-min-js-license = static/embedded_sagecell.js.LICENSE.txt

sagecell-css = static/sagecell.css
embed-css = static/sagecell_embed.css

tos-default = templates/tos_default.html
tos = templates/tos.html
tos-static = static/tos.html

all: $(all-min-js) $(embed-css) $(tos-static)

.PHONY: $(tos-static)

build:
	npm install
ifeq ($(strip $(FETCH_SAGE_DEPS)),)
# The standard build process is to copy all Javascript dependencies from a existing sage install
	-rm -r build
	npm run build:copystatic
	cp -a $(SAGE_VENV)/lib/python3.9/site-packages/notebook/static -T build/vendor
	cp static/colorpicker/js/colorpicker.js build/vendor
	ln -sfn $(SAGE_VENV)/share/jupyter/nbextensions/jupyter_jsmol/jsmol static/jsmol
	ln -sfn $(sage-root)/local/share/threejs-sage/r122 static/threejs
	ln -sf $(sage-root)/local/share/jmol/appletweb/SageMenu.mnu static/SageMenu.mnu
	cp static/jsmol/JSmol.min.nojq.js build/vendor/JSmol.js
	wget -P build/vendor \
		https://raw.githubusercontent.com/sockjs/sockjs-client/master/dist/sockjs.js \
		https://raw.githubusercontent.com/requirejs/domReady/latest/domReady.js \
		https://raw.githubusercontent.com/requirejs/text/latest/text.js
	python3 -c "from matplotlib.backends.backend_webagg_core import FigureManagerWebAgg; f = open('build/vendor/mpl.js', 'w'); f.write(FigureManagerWebAgg.get_javascript())"

else
# Fetch Javascript dependencies from github
	npm run build:deps

endif

$(all-min-js): build js/*
	npm run build
	cp build/embedded_sagecell.js $(all-min-js)
	cp build/embedded_sagecell.js.map $(all-min-js-map)
	cp build/embedded_sagecell.js.LICENSE.txt $(all-min-js-license)

$(embed-css): $(sagecell-css)
	sed -e 's/;/ !important;/g' < $(sagecell-css) > $(embed-css)

$(tos-static): $(tos-default)
	@[ -e $(tos) ] && cp $(tos) $(tos-static) || cp $(tos-default) $(tos-static)
