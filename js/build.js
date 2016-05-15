({
    name: "main",
    out: "main_build.js",
    //optimize: "none",
    paths: {
        "codemirror" : "components/codemirror",
        "jquery" : "components/jquery/jquery.min",
        "jquery-ui" : "components/jquery-ui/ui/minified/jquery-ui.min",
        "moment" : "components/moment/min/moment.min",
        "requireLib": "components/requirejs/require",
        "underscore" : "components/underscore/underscore-min"
    },
    include: [
        "requireLib"
    ]
})