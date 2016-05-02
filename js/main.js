// TODO: put this tracking code in a site-specific file.
// TODO: finish implementing our own stats service that handles,
//       the phone apps, for example.
var _gaq = _gaq || [];
_gaq.push(['sagecell._setAccount', 'UA-29124745-1']);
_gaq.push(['sagecell._setDomainName', 'sagemath.org']);
_gaq.push(['sagecell._trackPageview']);

(function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
})();

(function() {
"use strict";
var undefined;

if (!document.head) {
    document.head = document.getElementsByTagName("head")[0];
}

window.sagecell = window.sagecell || {};

sagecell.templates = {
    "minimal": { // for an evaluate button and nothing else.
        "editor": "textarea-readonly",
        "hide": ["editor", "files", "permalink"],
    },
    "restricted": { // to display/evaluate code that can't be edited.
        "editor": "codemirror-readonly",
        "hide": ["files", "permalink"],
    }
};

sagecell.allLanguages = ["sage", "gap", "gp", "html", "maxima", "octave", "python", "r", "singular"];

sagecell.init = function (callback) {
    require(['sagecell_r'], function() {
        sagecell.init(callback);
    });
};
sagecell.makeSagecell = function (args, k) {
    require(['sagecell_r'], function() {
        sagecell.makeSagecell(args, k);
    });
};
sagecell.deleteSagecell = function (sagecellInfo) {
    require(['sagecell_r'], function() {
        sagecell.deleteSagecell(sagecellInfo);
    });
};
sagecell.moveInputForm = function (sagecellInfo) {
    require(['sagecell_r'], function() {
        sagecell.moveInputForm(sagecellInfo);
    });
};
sagecell.restoreInputForm = function (sagecellInfo) {
    require(['sagecell_r'], function() {
        sagecell.restoreInputForm(sagecellInfo);
    });
};

// Purely for backwards compability
window.singlecell = window.sagecell;
window.singlecell.makeSinglecell = window.singlecell.makeSagecell;
})();
