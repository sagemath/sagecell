import $ from "jquery";
import utils from "base/js/utils";
import { URLs } from "./urls";
import { console } from "./console";

/* IPython url_join_encode and url_path_join is used in the cell server with URLs with hostnames, so we make it handle those correctly
    this is a temporary kludge.  A much better fix would be to introduce a kernel_base_url parameter in the kernel
    initialization, which would default to the empty string, and would be prepended to every kernel request.  Also, the
    ws_host attribute would derive from the kernel_base_url parameter.

    Right now, the IPython websocket connection urls are messed up (they prepend a phony ws_host), but that's okay because the regexp
    pulls out the kernel id and everything is fine.

    We make sure not to apply our handling multiple time (possible when
    the embedding script is included many times).
*/
var url_parts = new RegExp("^((([^:/?#]+):)?(//([^/?#]*))?)?(.*)");

function strip_hostname(f) {
    if (f._strip_hostname_applied) {
        return f;
    }
    function wrapped() {
        // override IPython function to account for leading protocol and hostname
        // assume that the first argument has the part to strip off, if any
        var hostname = "";
        if (arguments.length > 0) {
            var parts = arguments[0].match(url_parts);
            hostname = parts[1]; // everything up to the url path
            arguments[0] = parts[6]; // url path
        }
        return hostname + f.apply(null, arguments);
    }
    wrapped._strip_hostname_applied = true;
    return wrapped;
}

utils.url_join_encode = strip_hostname(utils.url_join_encode);
utils.url_path_join = strip_hostname(utils.url_path_join);

var ID;

function cellSessionID() {
    return (ID = ID || utils.uuid());
}

function sendRequest(method, url, data, callback, files) {
    var isXDomain =
        URLs.root !==
        window.location.protocol + "//" + window.location.host + "/";

    method = method.toUpperCase();
    var hasFiles = false;
    /* files code
    if (files === undefined) {
        files = [];
    }
    for (var i = 0; i < files.length; i++) {
        if (files[i]) {
            hasFiles = true;
            break;
        }
    }
    */
    var xhr = new XMLHttpRequest();
    var fd = undefined;
    if (method === "GET") {
        data.rand = Math.random().toString();
    }
    if (method === "POST" && localStorage.accepted_tos) {
        data.accepted_tos = "true";
    }
    // Format parameters to send as a string or a FormData object
    if (window.FormData && method !== "GET") {
        fd = new FormData();
        for (var k in data) {
            if (data.hasOwnProperty(k)) {
                fd.append(k, data[k]);
            }
        }
        /* files code
        for (var i = 0; i < files.length; i++) {
            if (files[i]) {
                fd.append("file", files[i]);
            }
        }
        */
    } else {
        fd = "";
        for (var k in data) {
            if (data.hasOwnProperty(k)) {
                fd +=
                    "&" +
                    encodeURIComponent(k) +
                    "=" +
                    encodeURIComponent(data[k]);
            }
        }
        fd = fd.substr(1);
        if (fd.length > 0 && method === "GET") {
            url += "?" + fd;
            fd = undefined;
        }
    }
    if (window.FormData || !(isXDomain /*|| hasFiles*/)) {
        // If an XMLHttpRequest is possible, use it
        xhr.open(method, url, true);
        xhr.withCredentials = true;
        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4 /* DONE */ && callback) {
                callback(xhr.responseText);
            }
        };
        if (typeof fd === "string") {
            xhr.setRequestHeader(
                "Content-type",
                "application/x-www-form-urlencoded"
            );
        }
        xhr.send(fd);
    } else if (method === "GET") {
        // Use JSONP to send cross-domain GET requests
        url += (url.indexOf("?") === -1 ? "?" : "&") + "callback=?";
        $.getJSON(url, callback);
    } else {
        // Use a form submission to send POST requests
        // Methods such as DELETE and OPTIONS will be sent as POST instead
        var iframe = document.createElement("iframe");
        iframe.name = utils.uuid();
        var form = document.createElement("form", {
            method: "POST",
            action: url,
            target: iframe.name,
        });
        if (data === undefined) {
            data = {};
        }
        data.method = method;
        for (var k in data) {
            if (data.hasOwnProperty(k)) {
                form.appendChild(
                    document.createElement("input", { name: k, value: data[k] })
                );
            }
        }
        form.appendChild(
            document.createElement("input", { name: "frame", value: "on" })
        );
        /* file code
        if (hasFiles) {
            form.setAttribute("enctype", "multipart/form-data");
            for (var i = 0; i < files.length; i++) {
                if (files[i]) {
                    form.appendChild(files[i]);
                }
            }
        }
        */
        form.style.display = iframe.style.display = "none";
        document.body.appendChild(iframe);
        document.body.appendChild(form);
        var listen = function (evt) {
            if (
                evt.source === iframe.contentWindow &&
                evt.origin + "/" === URLs.root
            ) {
                if (window.removeEventListener) {
                    removeEventListener("message", listen);
                } else {
                    detachEvent("onmessage", listen);
                }
                callback(evt.data);
                document.body.removeChild(iframe);
            }
        };
        if (window.addEventListener) {
            window.addEventListener("message", listen);
        } else {
            window.attachEvent("onmessage", listen);
        }
        form.submit();
        document.body.removeChild(form);
    }
}

export default {
    always_new: utils.always_new,
    cellSessionID: cellSessionID,
    createElement: function (type, attrs, children) {
        var node = document.createElement(type);
        for (var k in attrs) {
            if (attrs.hasOwnProperty(k)) {
                node.setAttribute(k, attrs[k]);
            }
        }
        if (children) {
            for (var i = 0; i < children.length; i++) {
                if (typeof children[i] == "string") {
                    node.appendChild(document.createTextNode(children[i]));
                } else {
                    node.appendChild(children[i]);
                }
            }
        }
        return node;
    },
    fixConsole: utils.fixConsole,
    /* var p = proxy(['list', 'of', 'methods'])
     will save any method calls in the list.  At some later time, you can invoke
     each method on an object by doing p._run_callbacks(my_obj) */
    proxy: function (methods) {
        var proxy = { _callbacks: [] };
        $.each(methods, function (i, method) {
            proxy[method] = function () {
                proxy._callbacks.push([method, arguments]);
                console.log("stored proxy for " + method);
            };
        });
        proxy._run_callbacks = function (obj) {
            $.each(proxy._callbacks, function (i, cb) {
                obj[cb[0]].apply(obj, cb[1]);
            });
        };
        return proxy;
    },
    sendRequest: sendRequest,
    simpleTimer: function () {
        var t = new Date().getTime();
        console.debug("starting timer from " + t);
        return function (reset) {
            var old_t = t;
            var new_t = new Date().getTime();
            if (reset) {
                t = new_t;
            }
            return new_t - old_t + " ms";
        };
    },
    //     throttle is from:
    //     Underscore.js 1.4.3
    //     http://underscorejs.org
    //     (c) 2009-2012 Jeremy Ashkenas, DocumentCloud Inc.
    //     Underscore may be freely distributed under the MIT license.
    // Returns a function, that, when invoked, will only be triggered at most once
    // during a given window of time.
    throttle: function (func, wait) {
        var context, args, timeout, result;
        var previous = 0;
        var later = function () {
            previous = new Date();
            timeout = null;
            result = func.apply(context, args);
        };
        return function () {
            var now = new Date();
            var remaining = wait - (now - previous);
            context = this;
            args = arguments;
            if (remaining <= 0) {
                clearTimeout(timeout);
                timeout = null;
                previous = now;
                result = func.apply(context, args);
            } else if (!timeout) {
                timeout = setTimeout(later, remaining);
            }
            return result;
        };
    },
    uuid: utils.uuid,
};
