import $ from "jquery";
import sagecell from "./sagecell";

export const URLs = {};

/**
 * Initialize the important URLs. The root URL derived from one of
 * the following locations:
 *   1. the variable sagecell.root
 *   2. a tag of the form <link property="sagecell-root" href="...">
 *   3. the root of the URL of the executing script
 */
export function initializeURLs() {
    var root;
    var el;
    if (sagecell.root) {
        root = sagecell.root;
    } else if ((el = $("link[property=sagecell-root]")).length > 0) {
        root = el.last().attr("href");
    } else {
        /* get the first part of the last script element's src that loaded something called 'embedded_sagecell.js'
        also, strip off the static/ part of the url if the src looked like 'static/embedded_sagecell.js'
        modified from MathJax source
        We could use the jquery reverse plugin at  http://www.mail-archive.com/discuss@jquery.com/msg04272.html
        and the jquery .each() to get this as well, but this approach avoids creating a reversed list, etc. */
        var scripts = (
            document.documentElement || document
        ).getElementsByTagName("script");
        var namePattern = /^.*?(?=(?:static\/)?embedded_sagecell.js)/;
        for (var i = scripts.length - 1; i >= 0; i--) {
            var m = (scripts[i].src || "").match(namePattern);
            if (m) {
                root = m[0];
                break;
            }
        }
        if (!root || root === "/") {
            root = window.location.protocol + "//" + window.location.host + "/";
        }
    }
    if (root.slice(-1) !== "/") {
        root += "/";
    }
    if (root === "http://sagecell.sagemath.org/") {
        root = "https://sagecell.sagemath.org/";
    }

    Object.assign(URLs, {
        cell: root + "sagecell.html",
        completion: root + "complete",
        help: root + "help.html",
        kernel: root + "kernel",
        permalink: root + "permalink",
        root: root,
        sockjs: root + "sockjs",
        spinner: root + "static/spinner.gif",
        terms: root + "tos.html",
    });
}
