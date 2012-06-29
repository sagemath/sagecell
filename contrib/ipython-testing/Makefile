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
jquery-ui      = static/jqueryui/js/jquery-ui-1.8.17.custom.min.js
sagecell       = static/sagecell.js
sagecell-css   = static/sagecell.css
codemirror-css = submodules/codemirror2/lib/codemirror.css
codemirror     = submodules/codemirror2/lib/codemirror.js
codemirror-py  = submodules/codemirror2/mode/python/python.js
jquery-ui-tp   = submodules/jquery-ui-touch-punch/jquery.ui.touch-punch.min.js
cssmin         = submodules/cssmin/src/cssmin.py
jsmin          = submodules/jsmin/jsmin.c
jsmin-bin      = submodules/jsmin-bin
# Set the SAGE_ROOT environmental variable to root of the Sage installation
ip-js          = $(SAGE_ROOT)/local/lib/python2.7/site-packages/IPython/frontend/html/notebook/static/js
ip-kernel      = $(ip-js)/kernel.js
ip-utils       = $(ip-js)/utils.js
ip-namespace   = $(ip-js)/namespace.js
jquery-url     = http://code.jquery.com/jquery-1.7.2.min.js
jmol-sage      = $(SAGE_ROOT)/local/share/jmol
wrapped        = $(foreach file,$(1),static/$(notdir $(basename $(file)).wrap$(suffix $(file))))

all: submodules $(jquery) $(all-min-js) $(all-min-css)

.PHONY: submodules
submodules:
	@cd ../..; if git submodule status | grep -q ^[+-]; then git submodule update --init > /dev/null; fi

$(jquery):
	python -c "import urllib; urllib.urlretrieve('$(jquery-url)','$(jquery)')"

$(all-min-js): $(jsmin-bin) $(all-js)
#	$(jsmin-bin) < 
	cp $(all-js) $(all-min-js)

$(call wrapped,$(jquery-ui)): $(wrap-jquery) $(jquery-ui)
	$(wrap-jquery) $(jquery-ui) > $(call wrapped,$(jquery-ui))

$(call wrapped,$(colorpicker)): $(wrap-jquery) $(colorpicker)
	$(wrap-jquery) $(colorpicker) > $(call wrapped,$(colorpicker))

$(call wrapped,$(jquery-ui-tp)): $(wrap-jquery) $(jquery-ui-tp)
	$(wrap-jquery) $(jquery-ui-tp) > $(call wrapped,$(jquery-ui-tp))

$(all-js): $(codemirror) $(codemirror-py) $(jmol-js) $(compute_server) \
           $(sagecell) $(ip-namespace) $(ip-utils) $(ip-kernel) \
           $(call wrapped,$(jquery-ui) $(jquery-ui-tp) $(colorpicker))
	cat $(codemirror) $(codemirror-py) $(jmol-js) $(ip-namespace) $(ip-utils) $(ip-kernel) \
	    $(call wrapped,$(jquery-ui) $(jquery-ui-tp) $(colorpicker)) > $(all-js)
	echo ';' >> $(all-js)
	cat $(compute_server) $(sagecell) >> $(all-js)

$(all-min-css): $(codemirror-css) $(sagecell-css)
	cat $(codemirror-css) $(sagecell-css) | python $(cssmin) > $(all-min-css)

$(jsmin-bin):  $(jsmin)
	gcc -o $(jsmin-bin) $(jsmin)

$(jmol-js): $(jmol-sage)
	rm -f $(jmol)
	ln -s $(jmol-sage) $(jmol)

