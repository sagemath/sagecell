/** Statically import CSS files and re-export them as a string */

import codemirror from "codemirror/lib/codemirror.css";
import fullscreen from "codemirror/addon/display/fullscreen.css";
import foldgutter from "codemirror/addon/fold/foldgutter.css";
import show_hint from "codemirror/addon/hint/show-hint.css";
import jquery from "jquery-ui-themes/themes/smoothness/jquery-ui.min.css";

import colorpicker from "colorpicker.css";
import fontawesome from "fontawesome.css";
import sagecell_css from "sagecell.css";

export const css = `${codemirror}\n\n${fullscreen}\n\n${foldgutter}\n\n${show_hint}\n\n${jquery}\n\n${colorpicker}\n\n${fontawesome}\n\n${sagecell_css}`;
