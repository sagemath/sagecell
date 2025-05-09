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
	-rm -r build
	npm run build:deps
	ln -sfn $(SAGE_VENV)/share/jupyter/nbextensions/jupyter-jsmol/jsmol static/jsmol
	ln -sfn $(sage-root)/local/share/threejs-sage/r122 static/threejs
	ln -sf $(sage-root)/local/share/jmol/appletweb/SageMenu.mnu static/SageMenu.mnu
	cp static/jsmol/JSmol.min.nojq.js build/vendor/JSmol.js

$(all-min-js): build js/*
	npm run build
	cp build/embedded_sagecell.js $(all-min-js)
	cp build/embedded_sagecell.js.map $(all-min-js-map)
	cp build/embedded_sagecell.js.LICENSE.txt $(all-min-js-license)
	# Host standalone jquery for compatibility with old instructions
	cp build/vendor/jquery*.min.js static/jquery.min.js

$(embed-css): $(sagecell-css)
	sed -e 's/;/ !important;/g' < $(sagecell-css) > $(embed-css)

$(tos-static): $(tos-default)
	@[ -e $(tos) ] && cp $(tos) $(tos-static) || cp $(tos-default) $(tos-static)
