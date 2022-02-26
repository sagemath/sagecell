/** Statically import CSS files and re-export them as a string */

import codemirror from "codemirror/lib/codemirror.css";
import fullscreen from "codemirror/addon/display/fullscreen.css";
import foldgutter from "codemirror/addon/fold/foldgutter.css";
import show_hint from "codemirror/addon/hint/show-hint.css";
import jquery from "jquery-ui-themes/themes/smoothness/jquery-ui.min.css";

import _colorpicker from "colorpicker.css";
// Fix colorpicker's relative paths
const colorpicker = _colorpicker.replace(/url\(\.\./g, "url(colorpicker");
import fontawesome from "fontawesome.css";
import sagecell_css from "sagecell.css";

const css = `${codemirror}\n\n${fullscreen}\n\n${foldgutter}\n\n${show_hint}\n\n${jquery}\n\n${colorpicker}\n\n${fontawesome}\n\n${sagecell_css}`;

export { css };
