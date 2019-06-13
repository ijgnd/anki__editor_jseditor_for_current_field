/* mostly extracts from editor.js which is
 * Copyright: Ankitects Pty Ltd and contributors
 * License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html */


var dropTarget = null;

function onDragOver(elem) {
    alert('_____________drop event');
    console.log('_____________drop event')
    var e = window.event;
    e.dataTransfer.dropEffect = "copy";
    e.preventDefault();
    // if we focus the target element immediately, the drag&drop turns into a
    // copy, so note it down for later instead
    dropTarget = elem;
}

function makeDropTargetCurrent() {
    dropTarget.focus();
    // the focus event may not fire if the window is not active, so make sure
    // the current field is set
    currentField = dropTarget;
}

function onCutOrCopy() {
    pycmd("cutOrCopy");
    return true;
}


var allowedTagsBasic = {};
var allowedTagsExtended = {};

var TAGS_WITHOUT_ATTRS = ["P", "DIV", "BR",
    "B", "I", "U", "EM", "STRONG", "SUB", "SUP"];
var i;
for (i = 0; i < TAGS_WITHOUT_ATTRS.length; i++) {
    allowedTagsBasic[TAGS_WITHOUT_ATTRS[i]] = {"attrs": []};
}

TAGS_WITHOUT_ATTRS = ["H1", "H2", "H3", "LI", "UL", "OL", "BLOCKQUOTE", "CODE",
    "PRE", "TABLE", "DD", "DT", "DL"];
for (i = 0; i < TAGS_WITHOUT_ATTRS.length; i++) {
    allowedTagsExtended[TAGS_WITHOUT_ATTRS[i]] = {"attrs": []};
}

allowedTagsBasic["IMG"] = {"attrs": ["SRC"]};

allowedTagsExtended["A"] = {"attrs": ["HREF"]};
allowedTagsExtended["TR"] = {"attrs": ["ROWSPAN"]};
allowedTagsExtended["TD"] = {"attrs": ["COLSPAN", "ROWSPAN"]};
allowedTagsExtended["TH"] = {"attrs": ["COLSPAN", "ROWSPAN"]};

// add basic tags to extended
Object.assign(allowedTagsExtended, allowedTagsBasic);


var pasteHTML = function (html) {
    html = filterHTML(html, false, true);
    if (html !== "") {
        tinymce.activeEditor.execCommand('mceInsertContent', false, html);
    }
};


var filterHTML = function (html, internal, extendedMode) {
    // wrap it in <top> as we aren't allowed to change top level elements
    var top = $.parseHTML("<ankitop>" + html + "</ankitop>")[0];
    if (internal) {
        filterInternalNode(top);
    }  else {
        filterNode(top, extendedMode);
    }
    var outHtml = top.innerHTML;
    if (!extendedMode) {
        // collapse whitespace
        outHtml = outHtml.replace(/[\n\t ]+/g, " ");
    }
    outHtml = outHtml.trim();
    //console.log(`input html: ${html}`);
    //console.log(`outpt html: ${outHtml}`);
    return outHtml;
};


// filtering from external sources
var filterNode = function (node, extendedMode) {
    // text node?
    if (node.nodeType === 3) {
        return;
    }

    // descend first, and take a copy of the child nodes as the loop will skip
    // elements due to node modifications otherwise

    var nodes = [];
    var i;
    for (i = 0; i < node.childNodes.length; i++) {
        nodes.push(node.childNodes[i]);
    }
    for (i = 0; i < nodes.length; i++) {
        filterNode(nodes[i], extendedMode);
    }

    if (node.tagName === "ANKITOP") {
        return;
    }

    var tag;
    if (extendedMode) {
        tag = allowedTagsExtended[node.tagName];
    } else {
        tag = allowedTagsBasic[node.tagName];
    }
    if (!tag) {
        if (!node.innerHTML || node.tagName === 'TITLE') {
            node.parentNode.removeChild(node);
        } else {
            node.outerHTML = node.innerHTML;
        }
    } else {
        // allowed, filter out attributes
        var toRemove = [];
        for (i = 0; i < node.attributes.length; i++) {
            var attr = node.attributes[i];
            var attrName = attr.name.toUpperCase();
            if (tag.attrs.indexOf(attrName) === -1) {
                toRemove.push(attr);
            }
        }
        for (i = 0; i < toRemove.length; i++) {
            node.removeAttributeNode(toRemove[i]);
        }
    }
};


