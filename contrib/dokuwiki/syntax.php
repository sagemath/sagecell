<?php
/**
 * DokuWiki Plugin sagecell (Syntax Component)
 *
 * @license GPL 2 http://www.gnu.org/licenses/gpl-2.0.html
 * @author  Jason Grout <jason.grout@drake.edu>
 */

// must be run within Dokuwiki
if (!defined('DOKU_INC')) die();

if (!defined('DOKU_LF')) define('DOKU_LF', "\n");
if (!defined('DOKU_TAB')) define('DOKU_TAB', "\t");
if (!defined('DOKU_PLUGIN')) define('DOKU_PLUGIN',DOKU_INC.'lib/plugins/');

require_once DOKU_PLUGIN.'syntax.php';

class syntax_plugin_sagecell extends DokuWiki_Syntax_Plugin {
    public function getType() {
        return 'protected';
    }

    public function getPType() {
        return 'normal';
    }

    public function getSort() {
        return 65;
    }


    public function connectTo($mode) {
        $this->Lexer->addSpecialPattern('<sagecell>.*?</sagecell>', $mode, 'plugin_sagecell');
    }

    public function handle($match, $state, $pos, &$handler){
        $data = array("code" => str_replace('</script>', '<\/script>', substr($match,10,-11)));
        return $data;
    }

    public function render($mode, &$renderer, $data) {
        if($mode != 'xhtml') return false;
        $renderer->doc .= "<div class=\"sage\"><script type=\"text/x-sage\">".$data["code"]."</script></div>";
        return true;
    }
}

// vim:ts=4:sw=4:et:
