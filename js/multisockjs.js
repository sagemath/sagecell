import { URLs } from "./urls";
import SockJS from "sockjs-client";
import utils from "./utils";

define(function () {
    "use strict";
    var undefined;

    function MultiSockJS(url, prefix) {
        console.debug(
            "Starting sockjs connection to " + url + " with prefix " + prefix
        );
        if (
            !MultiSockJS.sockjs ||
            MultiSockJS.sockjs.readyState === SockJS.CLOSING ||
            MultiSockJS.sockjs.readyState === SockJS.CLOSED
        ) {
            MultiSockJS.channels = {};
            MultiSockJS.to_init = [];
            console.debug("Initializing MultiSockJS to " + URLs.sockjs);
            MultiSockJS.sockjs = new SockJS(
                URLs.sockjs + "?CellSessionID=" + utils.cellSessionID()
            );

            MultiSockJS.sockjs.onopen = function (e) {
                while (MultiSockJS.to_init.length > 0) {
                    MultiSockJS.to_init.shift().init_socket(e);
                }
            };

            MultiSockJS.sockjs.onmessage = function (e) {
                var i = e.data.indexOf(",");
                var prefix = e.data.substring(0, i);
                console.debug("MultiSockJS.sockjs.onmessage prefix: " + prefix);
                e.data = e.data.substring(i + 1);
                console.debug("other data: " + e.data);
                if (
                    MultiSockJS.channels[prefix] &&
                    MultiSockJS.channels[prefix].onmessage
                ) {
                    MultiSockJS.channels[prefix].onmessage(e);
                }
            };

            MultiSockJS.sockjs.onclose = function (e) {
                var readyState = MultiSockJS.sockjs.readyState;
                for (var prefix in MultiSockJS.channels) {
                    MultiSockJS.channels[prefix].readyState = readyState;
                    if (MultiSockJS.channels[prefix].onclose) {
                        MultiSockJS.channels[prefix].onclose(e);
                    }
                }
                // Maybe we should just remove the sockjs object from MultiSockJS now
            };
        }
        this.prefix = url
            ? url.match(/^\w+:\/\/.*?\/kernel\/(.*\/channels).*$/)[1]
            : prefix;
        console.debug("this.prefix: " + this.prefix);
        this.readyState = MultiSockJS.sockjs.readyState;
        MultiSockJS.channels[this.prefix] = this;
        this.init_socket();
    }

    MultiSockJS.prototype.init_socket = function (e) {
        if (MultiSockJS.sockjs.readyState) {
            var that = this;
            // Run the onopen function after the current thread has finished,
            // so that onopen has a chance to be set.
            setTimeout(function () {
                that.readyState = MultiSockJS.sockjs.readyState;
                if (that.onopen) {
                    that.onopen(e);
                }
            }, 0);
        } else {
            MultiSockJS.to_init.push(this);
        }
    };

    MultiSockJS.prototype.send = function (msg) {
        MultiSockJS.sockjs.send(this.prefix + "," + msg);
    };

    MultiSockJS.prototype.close = function () {
        delete MultiSockJS.channels[this.prefix];
    };

    return MultiSockJS;
});
