({
    name: "main",
    out: "main_build.js",
    //optimize: "none",
    packages: [
        {
            name: "codemirror",
            location: "components/codemirror",
            main: "lib/codemirror"
        }
    ],
    paths: {
        'es6-promise': 'components/es6-promise/promise',
        "jquery" : "components/jquery/jquery.min",
        "jquery-ui" : "components/jquery-ui/ui/minified/jquery-ui.min",
        "moment" : "components/moment/min/moment.min",
        "requireLib": "components/requirejs/require",
        "underscore" : "components/underscore/underscore-min"
    },
    waitSeconds: 70,
    wrap: true,
    include: [
        "requireLib"
    ]
})
