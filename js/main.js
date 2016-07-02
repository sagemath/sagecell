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

window.sagecell = window.sagecell || {};
if (!document.head) {
    document.head = document.getElementsByTagName("head")[0];
}
require(['utils'], function(utils) {
    document.head.appendChild(utils.createElement(
        "link", {rel: "stylesheet", href: utils.URLs.root + "static/all.min.css"}));
    console.debug('SageMathCell stylesheet inserted');
});

sagecell.templates = {
    minimal: { // for an evaluate button and nothing else.
        editor: "textarea-readonly",
        hide: ["editor", "files", "permalink"],
    },
    restricted: { // to display/evaluate code that can't be edited.
        editor: "codemirror-readonly",
        hide: ["files", "permalink"],
    }
};

sagecell.allLanguages = ["sage", "gap", "gp", "html", "maxima", "octave", "python", "r", "singular"];

sagecell.makeSagecell = function(args) {
    console.info('sagecell.makeSagecell called');
    var cellInfo = {};
    require(['cell'], function(cell) {
        cell.make(args, cellInfo);
        console.info('sagecell.makeSagecell finished');
    });
    return cellInfo;
};
sagecell.deleteSagecell = function(cellInfo) {
    require(['cell'], function(cell) {
        cell.delete(cellInfo);
    });
};
sagecell.moveInputForm = function(cellInfo) {
    require(['cell'], function(cell) {
        cell.moveInputForm(cellInfo);
    });
};
sagecell.restoreInputForm = function(cellInfo) {
    require(['cell'], function(cell) {
        cell.restoreInputForm(cellInfo);
    });
};

// Purely for backwards compability
window.singlecell = window.sagecell;
window.singlecell.makeSinglecell = window.singlecell.makeSagecell;
})();
