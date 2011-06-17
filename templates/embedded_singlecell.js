makeSinglecell=(function() {
    var scripts=[
	{%- for script in scripts -%}
	"{{- url_for('static',filename=script,_external=True) -}}",
	{%- endfor -%}];
    for(var i=0; i<scripts.length; i++) {
	var s=document.createElement("script");
	s.setAttribute("type","text/javascript");
	s.setAttribute("src",scripts[i]);
	document.head.appendChild(s);
    }
    var stylesheets=[
	{%- for stylesheet in stylesheets -%}
	"{{- url_for('static',filename=stylesheet,_external=True) -}}",
	{%- endfor -%}];
    for(var i=0; i<stylesheets.length; i++) {
	var s=document.createElement("link");
	s.setAttribute("rel","stylesheet");
	s.setAttribute("href",stylesheets[i]);
	document.head.appendChild(s);
    }
    var body={% filter tojson %}{% include 'singlecell.html' %}{% endfilter %};
    // Wait for jQuery to load before using the $ function
    setTimeout(function() {
	if(typeof jQuery=="undefined") {
	    setTimeout(arguments.callee,100);
	} else {
	    $(function(){
		$.ajaxSetup({'dataType':'jsonp'});
		$('#singlecell').html(body);
		initPage();
	    });
	}
    },100);
})();

// Make the script root available to jquery
$URL={'root': {{ request.url_root|tojson|safe }},
      'evaluate': {{url_for('evaluate',_external=True)|tojson|safe}},
      'output_poll': {{url_for('output_poll',_external=True)|tojson|safe}} +
          '?callback=?',
      'output_long_poll': {{url_for('output_long_poll',_external=True)|tojson|safe}}
     };