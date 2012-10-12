<?php
	// Add the JS from aleph to embed the sagecell
	drupal_add_js('http://aleph.sagemath.org/static/jquery.min.js', array('scope' => 'header', 'every_page' => TRUE));
	drupal_add_js('http://aleph.sagemath.org/embedded_sagecell.js', array('scope' => 'header', 'every_page' => TRUE));

	// Add the inline JS to create the cell, performed after the page is loaded.
	// The long callback function changes the sagecell's buttons "type's" to "button" so they don't default to "submit" and submit the page when pressed
	drupal_add_js("sagecell.jQuery(function () { sagecell.makeSagecell({inputLocation: '#editcelltextarea', hide: ['files', 'sageMode'], evalButtonText: 'Evaluate', callback: function () {sagecell.jQuery('.sagecell button').each(function (i) {this.setAttribute('type', 'button');});}});});", array('type' => 'inline', 'defer' => TRUE, 'every_page' => TRUE));

