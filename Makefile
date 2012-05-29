all: submodules static/jquery.min.js static/all.min.js static/all.min.css

.PHONY: submodules
submodules:
	@if git submodule status | grep -q ^[+-]; then git submodule update --init > /dev/null; fi

static/jquery.min.js:
	python -c "import urllib; urllib.urlretrieve('http://code.jquery.com/jquery-1.7.1.min.js','static/jquery.min.js')"

static/all.min.js: submodules/jsmin-bin static/all.js
	rm -f static/all.min.js
	submodules/jsmin-bin < static/all.js > static/all.min.js

static/all.js: submodules/codemirror2/lib/codemirror.js submodules/codemirror2/mode/python/python.js static/jmol/appletweb/Jmol.js static/jqueryui/js/jquery-ui-1.8.17.custom.min.js submodules/jquery-ui-touch-punch/jquery.ui.touch-punch.min.js static/colorpicker/js/colorpicker.js static/compute_server.js static/sagecell.js
	echo '' > static/all.js
	cat submodules/codemirror2/lib/codemirror.js submodules/codemirror2/mode/python/python.js >> static/all.js
	cat static/jmol/appletweb/Jmol.js >> static/all.js
	cat static/jqueryui/js/jquery-ui-1.8.17.custom.min.js >> static/all.js
	cat submodules/jquery-ui-touch-punch/jquery.ui.touch-punch.min.js >> static/all.js
	cat static/colorpicker/js/colorpicker.js >> static/all.js
	echo ';' >> static/all.js
	cat static/compute_server.js >> static/all.js
	cat static/sagecell.js >> static/all.js

static/all.min.css: submodules/codemirror2/lib/codemirror.css static/stylesheet.css
	echo '' > static/all.css
	cat 'submodules/codemirror2/lib/codemirror.css' >> static/all.css
	# We can't include the following in our file because they have references to their image directories
	# so instead, we include them as separate CSS links.
	#cat 'jqueryui/css/sage/jquery-ui-1.8.17.custom.css' >> all.css
	#cat 'colorpicker/css/colorpicker.css' >> all.css
	cat 'static/stylesheet.css' >> static/all.css
	rm -f static/all.min.css
	python submodules/cssmin/src/cssmin.py < static/all.css > static/all.min.css

submodules/jsmin-bin:  submodules/jsmin/jsmin.c
	gcc -o submodules/jsmin-bin submodules/jsmin/jsmin.c

