/**
 * a simple zoom in/out/reset for remark.js
 *
 * Hot key:
 *   + : zoom in
 *   - : zoom out
 *   0 : reset zoom
 *
 * CAVEAT: when switching between full screen and normal screen,
 *         the zoom factor may not function correctly.
 *         RELOAD the page, if necessary.
 *
 * 
 * @author William Yeh <william.pjyeh@gmail.com>
 * @date   2015-01-15
 *
 * @license Apache License, Version 2.0.
 * Copyright © 2015 William Yeh.
 */

var ZOOM_TEXT_SELECTOR =
            ".remark-slide-content p"
    + "," + ".remark-slide-content .remark-code-line"
    ;

var ZOOM_IMG_SELECTOR =
            ".remark-slide-content img:hover"
    ;

/*  // works for Chrome, but not for Firefox
var ZOOM_TEXT_SELECTOR =
            ".remark-visible .remark-slide-content p"
    + "," + ".remark-visible .remark-slide-content .remark-code-line"
    ;

var ZOOM_IMG_SELECTOR =
            ".remark-visible .remark-slide-content img:hover"
    ;
*/


var ZOOM_IMG_RULE;

var zoom_factor = 100.0;
document.body.style.zoom = "100%"


function init_zoom_rule() {
    // @see http://davidwalsh.name/add-rules-stylesheets
    var styles = document.styleSheets[0];
    var index = styles.insertRule(
        ZOOM_IMG_SELECTOR + ' { transform:scale(1); }',
        styles.cssRules.length
        );

    ZOOM_IMG_RULE = styles.cssRules.item(index);
}


function apply_zoom() {
    var elements = document.querySelectorAll(ZOOM_TEXT_SELECTOR);
    //console.log('length:', elements.length);
    for (var i = 0; i < elements.length; ++i) {
        var item = elements[i];
        item.style.fontSize = zoom_factor.toString() + '%';
    }

    ZOOM_IMG_RULE.style.transform = 'scale(' + (zoom_factor / 100) + ')';
}

function zoom_in() {
    zoom_factor += 10;
    if (zoom_factor >= 200.0)  zoom_factor = 200.0;
    apply_zoom();
}

function zoom_out() {
    zoom_factor -= 10;
    if (zoom_factor <= 50.0)  zoom_factor = 50.0;
    apply_zoom();
}

function zoom_reset() {
    zoom_factor = 100.0;
    apply_zoom();
}


init_zoom_rule();
window.addEventListener("keydown", function(event) {
    //console.log(event.keyCode);
    switch (event.keyCode) {
       case 187:  // '+': 187 in Chrome & Safari, 61 in FF
       case 61:  // '+': 187 in Chrome, 61 in FF
          zoom_in(); 
          break;

       case 189:  // '-': 189 in Chrome & Safari, 173 in FF
       case 173:  // '-': 189 in Chrome, 173 in FF
          zoom_out();
          break;

       case 48:   // '0'
          zoom_reset();
          break;
    }
}, false);
