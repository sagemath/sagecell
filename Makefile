sage-root := $(shell [ -n "$$SAGE_ROOT" ] && echo "$$SAGE_ROOT" || sage --root || echo "\$$SAGE_ROOT")
all-min-js = static/embedded_sagecell.js
all-min-js-map = static/embedded_sagecell.js.map
all-min-js-license = static/embedded_sagecell.js.LICENSE.txt

sagecell-css = static/sagecell.css
embed-css = static/sagecell_embed.css

tos-default = templates/tos_default.html
tos = templates/tos.html
tos-static = static/tos.html

all: submodules $(all-min-js) $(embed-css) $(tos-static)

.PHONY: submodules $(tos-static)

submodules:
	if git submodule status | grep -q ^[+-]; then git submodule update --init > /dev/null; fi

build:
	npm install
	npm run build:deps

$(all-min-js): build js/*
	npm run build
	cp build/embedded_sagecell.js $(all-min-js)
	cp build/embedded_sagecell.js.map $(all-min-js-map)
	cp build/embedded_sagecell.js.LICENSE.txt $(all-min-js-license)

$(embed-css): $(sagecell-css)
	sed -e 's/;/ !important;/g' < $(sagecell-css) > $(embed-css)

$(tos-static): $(tos-default)
	@[ -e $(tos) ] && cp $(tos) $(tos-static) || cp $(tos-default) $(tos-static)
