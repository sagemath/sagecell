<?php
/**
 * Default settings for the sagecell plugin
 *
 * @author Jason Grout <jason.grout@drake.edu>
 */

$conf['url']    = 'https://sagecell.sagemath.org';
$conf['style']  = '.sagecell .CodeMirror pre {
    padding: 0 4px !important; 
    border: 0px !important; 
    margin: 0 !important;}
.sagecell .CodeMirror {
  height: auto;
}
.sagecell .CodeMirror-scroll {
  overflow-y: auto;
  overflow-x: auto;
  max-height: 200px;
}
';
