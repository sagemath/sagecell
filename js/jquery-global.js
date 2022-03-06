import _jquery from "jquery";

// Some users depend on jQuery being globally set by sage_cell.
// We take care to initialize the jQuery global variable only if
// another jQuery is not set.
window.jQuery = window.jQuery || window.$ || _jquery;
window.$ = window.$ || window.jQuery || _jquery;
