all: ../minifiers/jsmin all.min.js all.min.css

all.min.js:
	echo '' > all.js
	cat codemirror2/lib/codemirror.js codemirror2/mode/python/python.js >> all.js
	cat jmol/appletweb/Jmol.js >> all.js
	cat jqueryui/js/jquery-ui-1.8.13.custom.min.js colorpicker/js/colorpicker.js >> all.js
	cat singlecell.js >> all.js
	../minifiers/jsmin < all.js > all.min.js

all.min.css:
	echo '' > all.css
	cat 'codemirror2/lib/codemirror.css' >> all.css
	cat 'codemirror2/theme/default.css' >> all.css
	cat 'jqueryui/css/sage/jquery-ui-1.8.13.custom.css' >> all.css
	cat 'colorpicker/css/colorpicker.css' >> all.css
	cat 'stylesheet.css' >> all.css
	python ../minifiers/cssmin/src/cssmin.py < all.css > all.min.css

jsmin: ../minifiers/jsmin.c
	cd ../minifiers/
	gcc -o jsmin jsmin.c
	cd ../static/

