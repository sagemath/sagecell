<?php
/**
 * DokuWiki Plugin sagecell (Action Component)
 *
 * @license GPL 2 http://www.gnu.org/licenses/gpl-2.0.html
 * @author  Jason Grout <jason.grout@drake.edu>
 */

// must be run within Dokuwiki
if (!defined('DOKU_INC')) die();

if (!defined('DOKU_LF')) define('DOKU_LF', "\n");
if (!defined('DOKU_TAB')) define('DOKU_TAB', "\t");
if (!defined('DOKU_PLUGIN')) define('DOKU_PLUGIN',DOKU_INC.'lib/plugins/');

require_once DOKU_PLUGIN.'action.php';

class action_plugin_sagecell extends DokuWiki_Action_Plugin {

    public function register(Doku_Event_Handler &$controller) {

       $controller->register_hook('TPL_METAHEADER_OUTPUT', 'BEFORE', $this, 'handle_tpl_metaheader_output');

    }

    public function handle_tpl_metaheader_output(Doku_Event &$event, $param) {
      $url = rtrim($this->getConf('url'), '/');
      // Adding js
      $event->data["script"][] = array (
                                        "type" => "text/javascript",
                                        "src" => $url . "/static/jquery.min.js",
                                        "_data" => "",
                                        );
      $event->data["script"][] = array (
                                        "type" => "text/javascript",
                                        "src" => $url . "/static/embedded_sagecell.js",
                                        "_data" => "",
                                        );
      // Initializing cells
      $event->data["script"][] = array (
                                        "type" => "text/javascript",
                                        "charset" => "utf-8",
                                        "_data" => "sagecell.makeSagecell({inputLocation: '.sage'});",
                                        );
      // Adding stylesheet
      $event->data["link"][] = array (
                                      "type" => "text/css",
                                      "rel" => "stylesheet",
                                      "href" => $url . "/static/sagecell_embed.css",
                                      );
      $event->data['style'][] = array('type'  => 'text/css',
                                '_data' => $this->getConf('style'));
    }

}

// vim:ts=4:sw=4:et:
