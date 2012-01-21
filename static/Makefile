all: ../minifiers/jsmin all.min.js all.min.css

all.min.js: codemirror2/lib/codemirror.js codemirror2/mode/python/python.js jmol/appletweb/Jmol.js jqueryui/js/jquery-ui-1.8.17.custom.min.js jquery.ui.touch-punch.min.js colorpicker/js/colorpicker.js compute_server.js singlecell.js ../minifiers/jsmin 
	echo '' > all.js
	cat codemirror2/lib/codemirror.js codemirror2/mode/python/python.js >> all.js
	cat jmol/appletweb/Jmol.js >> all.js
	cat jqueryui/js/jquery-ui-1.8.17.custom.min.js >> all.js
	cat jquery.ui.touch-punch.min.js >> all.js
	cat colorpicker/js/colorpicker.js >> all.js
	cat compute_server.js >> all.js
	cat singlecell.js >> all.js
	../minifiers/jsmin < all.js > all.min.js

all.min.css: codemirror2/lib/codemirror.css stylesheet.css
	echo '' > all.css
	cat 'codemirror2/lib/codemirror.css' >> all.css
	# We can't include the following in our file because they have references to their image directories
	# so instead, we include them as separate CSS links.
	#cat 'jqueryui/css/sage/jquery-ui-1.8.17.custom.css' >> all.css
	#cat 'colorpicker/css/colorpicker.css' >> all.css
	cat 'stylesheet.css' >> all.css
	python ../minifiers/cssmin/src/cssmin.py < all.css > all.min.css

jsmin: ../minifiers/jsmin.c
	cd ../minifiers/
	gcc -o jsmin jsmin.c
	cd ../static/

