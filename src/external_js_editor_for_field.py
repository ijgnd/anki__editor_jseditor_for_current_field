"""
anki-addon: open field contents in WYSIWYG-Editor (like TinyMCE)

Copyright (c) 2019- ignd
          (c) Ankitects Pty Ltd and contributors
          (c) 2018 Hyun Woo Park
                   (the cloze functions in template file are taken from
                   https://github.com/phu54321/kian which is AGPLv3) 


This add-on is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This add-on is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this add-on.  If not, see <https://www.gnu.org/licenses/>.



This add-on bundles "TinyMCE4" in the folder web/tinymce4
    Copyright (c) Tiny Technologies, Inc.
    "TinyMCE" was downloaded from http://download.tiny.cloud/tinymce/community/tinymce_4.9.11.zip
    "TinyMCE" contains web/tinymce4/js/tinymce/license.txt
    "TinyMCE" is licensed as LPGL 2.1 (or later)


This add-on bundles "TinyMCE5" in the folder web/tinymce5
    Copyright (c) Tiny Technologies, Inc.
    "TinyMCE" was downloaded from http://download.tiny.cloud/tinymce/community/tinymce_5.4.0.zip
    "TinyMCE" contains web/tinymce5/js/tinymce/license.txt
    "TinyMCE" is licensed as LPGL 2.1 (or later)


This add-on bundles the file "sync_execJavaScript.py" which has this copyright and permission
notice: 
    Copyright: 2014 - 2016 Detlev Offenbach <detlev@die-offenbachs.de>
                  (taken from https://github.com/pycom/EricShort/blob/master/UI/Previewers/PreviewerHTML.py)
    License: GPLv3 or later, https://github.com/pycom/EricShort/blob/025a9933bdbe92f6ff1c30805077c59774fa64ab/LICENSE.GPL3


This add-on bundles "ckEditor4" (version 4.3.4) in the folder web/ckeditor4_old
    Copyright (c) 2003-2014, CKSource - Frederico Knabben. All rights reserved.
    Licensed under the terms of any of the following licenses at your choice:
    GNU General Public License Version 2 or later (the "GPL"), http://www.gnu.org/licenses/gpl.html
    for details see web/ckeditor4_old/LICENSE.md


This add-on bundles the ckeditor theme "moono-dark" in  web/ckeditor4_old/skins/moono-dark/
    downloaded form https://ckeditor.com/cke4/addon/moono-dark
    Copyright and License are the same as ckeditor4 according to web/ckeditor4/skins/moono-dark/readme.md



This add-on bundles "ckEditor4" (version 4.14.1) in the folder web/ckeditor4_new
    Copyright (c) 2003-2020, CKSource - Frederico Knabben. All rights reserved.
    Licensed under the terms of any of the following licenses at your choice:
    GNU General Public License Version 2 or later (the "GPL"), http://www.gnu.org/licenses/gpl.html
    for details see web/ckeditor4_new/LICENSE.md
I added the following plugins and skins which have the same copyright and permission notice:
    - moono-dark,  https://ckeditor.com/cke4/addon/moono-dark
    - moono, https://ckeditor.com/cke4/addon/moono
    - pastefromlibreoffice, https://ckeditor.com/cke4/addon/pastefromlibreoffice
    - Tab Key Handling, https://ckeditor.com/cke4/addon/tab
    - Show Table Borders (showborders), https://ckeditor.com/cke4/addon/showborders
    - Table Resize (tableresize), https://ckeditor.com/cke4/addon/tableresize
    - Stylesheet Parser, https://ckeditor.com/cke4/addon/stylesheetparser
    - Auto Link, https://ckeditor.com/cke4/addon/autolink


This add-on bundles "jquery-3.5.1.min.js" in the folder web which has this copyright and permission
notice (jquery.org/license, https://github.com/jquery/jquery/blob/master/LICENSE.txt):

    Copyright OpenJS Foundation and other contributors, https://openjsf.org/

    Permission is hereby granted, free of charge, to any person obtaining
    a copy of this software and associated documentation files (the
    "Software"), to deal in the Software without restriction, including
    without limitation the rights to use, copy, modify, merge, publish,
    distribute, sublicense, and/or sell copies of the Software, and to
    permit persons to whom the Software is furnished to do so, subject to
    the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
    LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
    OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
    WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


This add-on bundles "CKEditor 5 classic editor build" (version 19.1.1) in the folder web/ckeditor5
    https://github.com/ckeditor/ckeditor5-build-classic
    Copyright (c) 2003-2020, [CKSource](http://cksource.com) Frederico Knabben. All rights reserved.
    Licensed under the terms of [GNU General Public License Version 2 or later](http://www.gnu.org/licenses/gpl.html).

"""

import os
import io
import time

from anki.hooks import addHook
from anki.utils import isLin

import aqt
from aqt import mw
from aqt.qt import (
    QDialog,
    QVBoxLayout,
    QDialogButtonBox,
    Qt,
    QMetaObject,
    QShortcut,
    QKeySequence,
    QNativeGestureEvent,
    QEvent,
)
from aqt.theme import theme_manager
from aqt.utils import (
     askUser,
     saveGeom,
     restoreGeom,
     showInfo,
     tooltip,
)
from aqt.webview import AnkiWebView, QWebEngineView

from .config import gc
from .sync_execJavaScript import sync_execJavaScript



"""
tinymce5 full screen resizing didn't work in 2020-05: so I added resize_tiny_mce as a workaround

Background:
- what worked in tinymce4 no longer works
- height : "100vh" didn't help though it should? https://www.tiny.cloud/docs/configure/editor-appearance/#height
- nothing else useful in https://www.tiny.cloud/docs/configure/editor-appearance
- autoresize plugin: no help
- github issues search for:   is:issue full screen  label:5.x 

to make sure it's not some interaction with my full config I tested with this minimal config
which made no difference:

<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>   
tinymce.init({
    selector: '.tinymce5_wysiwyg',
    plugins: [
        'fullscreen',       // maximize tinymce to window https://www.tiny.cloud/docs/plugins/fullscreen/
        ],
    setup: function(editor) {
        editor.on('init', function() {
            editor.execCommand('mceFullScreen');   //maximize,  https://stackoverflow.com/a/22959296
        });
    }
})
</script>
<div class="tinymce5_wysiwyg" id="tinymce5_wysiwyg_unique" style="height:100vh;">%(CONTENT)s</div>



or this minimal example:
<script>
tinymce.init({
    selector: 'textarea#basic-example',
    height: 500,
    menubar: false,
    plugins: [
    'fullscreen',
    ],
    menubar: 'file edit view insert format tools table help',
});
</script>
<textarea id="basic-example">%(CONTENT)s</textarea>
"""


addon_path = os.path.dirname(__file__)
addonfoldername = os.path.basename(addon_path)
regex = r"(web[/\\].*)"
mw.addonManager.setWebExports(__name__, regex)
web_path = "/_addons/%s/web/" % addonfoldername



def update_config():
    config = mw.addonManager.getConfig(__name__)
    if "shortcut: open dialog" in config:
        config["TinyMCE5 - shortcut to open dialog"] = config["shortcut: open dialog"]
        del config["shortcut: open dialog"]
        mw.addonManager.writeConfig(__name__, config)
update_config()


addon_cssfiles = ["webview_override.css",
                  ]
other_cssfiles = []
cssfiles = addon_cssfiles + other_cssfiles


addon_jsfiles = []
other_jsfiles = ["",
                 ]


class MyWebView(AnkiWebView):
    def sync_execJavaScript(self, script):
        return sync_execJavaScript(self, script)

    def bundledScript(self, fname):
        if fname in addon_jsfiles + other_jsfiles:
            return '<script src="%s"></script>' % (web_path + fname)
        else:
            return '<script src="%s"></script>' % self.webBundlePath(fname)

    def bundledCSS(self, fname):
        if fname in addon_cssfiles:
            return '<link rel="stylesheet" type="text/css" href="%s">' % (web_path + fname)
        else:
            return '<link rel="stylesheet" type="text/css" href="%s">' % self.webBundlePath(fname)

    def zoom_in(self):
        self.change_zoom_by(1.1)

    def zoom_out(self):
        self.change_zoom_by(1/1.1)

    def change_zoom_by(self, interval):
        currZoom = QWebEngineView.zoomFactor(self)
        self.setZoomFactor(currZoom * interval)

    def wheelEvent(self, event):
        # doesn't work in 2020-05?
        pass

    def eventFilter(self, obj, evt):
        # from aqt.webview.AnkiWebView
        #    because wheelEventdoesn't work in 2020-05?


        # disable pinch to zoom gesture
        if isinstance(evt, QNativeGestureEvent):
            return True

        ###my mod
        # event type 31  # https://doc.qt.io/qt-5/qevent.html
        # evt.angleDelta().x() == 0   =>  ignore sidecroll 
        elif evt.type() == QEvent.Wheel and evt.angleDelta().x() == 0 and (mw.app.keyboardModifiers() & Qt.ControlModifier): 
            dif = evt.angleDelta().y()
            if dif > 0:
                self.zoom_out()
            else:
                self.zoom_in()
        ### end my mode

        elif evt.type() == QEvent.MouseButtonRelease:
            if evt.button() == Qt.MidButton and isLin:
                self.onMiddleClickPaste()
                return True
            return False
        return False


class MyDialog(QDialog):
    def __init__(self, parent, bodyhtml, jsSavecommand, wintitle, dialogname):
        super(MyDialog, self).__init__(parent)

        self.jsSavecommand = jsSavecommand
        self.setWindowTitle(wintitle)
        self.resize(810, 700)
        restoreGeom(self, "805891399_winsize")

        mainLayout = QVBoxLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        self.setLayout(mainLayout)
        self.web = MyWebView(self)
        self.web.allowDrops = True   # default in webview/AnkiWebView is False
        self.web.title = dialogname
        self.web.contextMenuEvent = self.contextMenuEvent
        mainLayout.addWidget(self.web)

        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        mainLayout.addWidget(self.buttonBox)

        self.buttonBox.accepted.connect(self.onAccept)
        self.buttonBox.rejected.connect(self.onReject)
        QMetaObject.connectSlotsByName(self)
        acceptShortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        acceptShortcut.activated.connect(self.onAccept)

        zoomIn_Shortcut = QShortcut(QKeySequence("Ctrl++"), self)
        zoomIn_Shortcut.activated.connect(self.web.zoom_in)

        zoomOut_Shortcut = QShortcut(QKeySequence("Ctrl+-"), self)
        zoomOut_Shortcut.activated.connect(self.web.zoom_out)

        self.web.stdHtml(bodyhtml, cssfiles, addon_jsfiles + other_jsfiles)

    def onAccept(self):
        global editedfieldcontent
        editedfieldcontent = self.web.sync_execJavaScript(self.jsSavecommand)
        self.web = None  # doesn't remove?
        # self.web._page.windowCloseRequested()  # native qt signal not callable
        # self.web._page.windowCloseRequested.connect(self.web._page.window_close_requested)
        saveGeom(self, "805891399_winsize")
        self.accept()
        # self.done(0)

    def onReject(self):
        ok = askUser("Close and lose current input?")
        if ok:
            saveGeom(self, "805891399_winsize")
            self.reject()

    def closeEvent(self, event):
        ok = askUser("Close and lose current input?")
        if ok:
            event.accept()
        else:
            event.ignore()


def _onWYSIWYGUpdateField(editor):
    global editedfieldcontent
    if not isinstance(editedfieldcontent, str):
        tooltip("Unknown error in Add-on. Aborting ...")
        return
    to_remove = [
        "<!--StartFragment-->",
        "<!--EndFragment-->",
    ]
    for l in to_remove:
        editedfieldcontent = editedfieldcontent.replace(l, "")

    editor.note.fields[editor.myfield] = editedfieldcontent
    if not editor.addMode:
        editor.note.flush()
    editor.loadNote(focusTo=editor.myfield)


def on_WYSIWYGdialog_finished(editor, status):
    if status:
        editor.saveNow(lambda e=editor: _onWYSIWYGUpdateField(e))


hiliters_tinymce = """
    // TODO change to class applier
    hilite(editor, tinymce, 'hiliteGreen',"#00ff00",'alt+w','GR');
    hilite(editor, tinymce, 'hiliteBlue',"#00ffff",'alt+e','BL'); 
    hilite(editor, tinymce, 'hiliteRed',"#fd9796",'alt+r','RE'); 
    hilite(editor, tinymce, 'hiliteYellow',"#ffff00",'alt+q','YE');
"""   


def wysiwyg_dialog(editor, field, editorname):
    global addon_jsfiles

    editors_dict = {
        "T4": "tinymce4/js/tinymce/tinymce.min.js",
        "T5": "tinymce5/js/tinymce/tinymce.min.js",
        "cked4old": "ckeditor4_old/ckeditor.js",
        "cked4": "ckeditor4_new/ckeditor.js",
        "cked5": "ckeditor5/ckeditor.js",
    }
    addon_jsfiles = [editors_dict[editorname]]
    if editorname == "T4":
        # TODO
        jssavecmd = "tinyMCE.activeEditor.getContent();"
        wintitle = 'Anki - edit current field in TinyMCE4'
        dialogname = "tinymce4"
        bodyhtml = templatecontent_tinymce4 % {
            "FONTSIZE": gc('fontSize'),
            "FONTNAME": gc('font'),
            "CUSTOMBGCOLOR": "#e4e2e0",
            "HILITERS": hiliters_tinymce if gc("show background color buttons") else "",
            "CONTENT": editor.note.fields[field],
            }
    if editorname == "T5":
        jssavecmd = "tinyMCE.activeEditor.getContent();"
        wintitle = 'Anki - edit current field in TinyMCE5'
        dialogname = "tinymce5"
        bodyhtml = templatecontent_tinymce5 % {
            "FONTSIZE": gc('fontSize'),
            "FONTNAME": gc('font'),
            "CUSTOMBGCOLOR": "" if theme_manager.night_mode else """this.getDoc().body.style.backgroundColor = '#e4e2e0';""",
            #  https://www.tiny.cloud/blog/dark-mode-tinymce-rich-text-editor/
            "CONTENTCSS": '"dark",' if theme_manager.night_mode else "",
            "SKIN": "oxide-dark" if theme_manager.night_mode else "oxide",
            "THEME": "silver",
            "HILITERS": hiliters_tinymce if gc("show background color buttons") else "",
            "CONTENT": editor.note.fields[field],
            }
    if editorname == "cked4old":
        jssavecmd = "CKEDITOR.instances.cked4_editor.getData();" #""cked4_editor.getData();"
        wintitle = 'Anki - edit current field in ckEditor4 (old)'
        dialogname = "cked4"
        bodyhtml = templatecontent_cked4old % {
            "FONTSIZE": gc('fontSize'),
            "FONTNAME": gc('font'),
            "BASEURL": f"http://127.0.0.1:{mw.mediaServer.getPort()}/",
            "WEBPATH": f"http://127.0.0.1:{mw.mediaServer.getPort()}{web_path}",
            "CUSTOMBGCOLOR": "#2f2f31" if theme_manager.night_mode else "#e4e2e0",
            "CUSTOMCOLOR": "white" if theme_manager.night_mode else "black",
            "SKIN": "moono-dark" if theme_manager.night_mode else "moono",
            "CONTENT": editor.note.fields[field],
            }
    if editorname == "cked4":
        jssavecmd = "CKEDITOR.instances.cked4_editor.getData();" #""cked4_editor.getData();"
        wintitle = 'Anki - edit current field in ckEditor4'
        dialogname = "cked4"
        bodyhtml = templatecontent_cked4 % {
            "FONTSIZE": gc('fontSize'),
            "FONTNAME": gc('font'),
            "BASEURL": f"http://127.0.0.1:{mw.mediaServer.getPort()}/",
            "WEBPATH": f"http://127.0.0.1:{mw.mediaServer.getPort()}{web_path}",
            "CUSTOMBGCOLOR": "#2f2f31" if theme_manager.night_mode else "#e4e2e0",
            "CUSTOMCOLOR": "white" if theme_manager.night_mode else "black",
            "SKIN": "moono-dark" if theme_manager.night_mode else "moono", # "moono-lisa",
            "CONTENT": editor.note.fields[field],
            }
    if editorname == "cked5":
        """TODO 
// in cked4 that images from the media folder with relative links are displayed I use
// but in 2020-06-15 this doesn't work in cked5, see https://ckeditor.com/docs/ckeditor5/latest/builds/guides/migrate.html
// Not supported yet, see the relevant GitHub issue, https://github.com/ckeditor/ckeditor5/issues/665
"""
        jssavecmd = "cked5_editor.getData();" #""cked4_editor.getData();"
        wintitle = 'Anki - edit current field in ckEditor5'
        dialogname = "cked5"
        bodyhtml = templatecontent_cked5 % {
            "FONTSIZE": gc('fontSize'),
            "FONTNAME": gc('font'),
            "BASEURL": f"http://127.0.0.1:{mw.mediaServer.getPort()}/",
            "CUSTOMBGCOLOR": "#2f2f31" if theme_manager.night_mode else "#e4e2e0",
            "CUSTOMCOLOR": "white" if theme_manager.night_mode else "black",
            "SKIN": "moono-dark" if theme_manager.night_mode else "moono",
            "CONTENT": editor.note.fields[field],
            }
    d = MyDialog(None, bodyhtml, jssavecmd, wintitle, dialogname)
    # exec_() doesn't work, see  https://stackoverflow.com/questions/39638749/
    #d.finished.connect(editor.on_WYSIWYGdialog_finished)
    d.finished.connect(lambda status, func=on_WYSIWYGdialog_finished, e=editor: func(e, status))
    d.setModal(True)
    d.show()
    d.web.setFocus()



def readfile(file):
    filefullpath = os.path.join(addon_path, file)
    with io.open(filefullpath, 'r', encoding='utf-8') as f:
        return f.read()
templatecontent_tinymce4 = readfile("template_tiny4_body.html")
templatecontent_tinymce5 = readfile("template_tiny5_body.html")
templatecontent_cked4 = readfile("template_cked4_body.html")
templatecontent_cked4old = readfile("template_cked4_old_body.html")
templatecontent_cked5 = readfile("template_cked5_body.html")


def external_editor_start(editor, editorname):
    if editor.currentField is None:
        tooltip("no field focussed. Aborting ...")        
        return
    editor.myfield = editor.currentField
    editor.saveNow(lambda e=editor, f=editor.myfield, n=editorname: wysiwyg_dialog(e,f,n))


def keystr(k):
    key = QKeySequence(k)
    return key.toString(QKeySequence.NativeText)


def setupEditorButtonsFilter(buttons, editor):
    cut_T5 = gc("TinyMCE5 - shortcut to open dialog")
    tip_T5 = "edit current field in external window"
    if cut_T5:
        tip_T5 += " ({})".format(keystr(cut_T5))

    cut_T4 = gc("TinyMCE4 - shortcut to open dialog")
    tip_T4 = "edit current field with TinyMCE4"
    if cut_T4:
        tip_T4 += " ({})".format(keystr(cut_T4))

    cut_cked4 = gc("Ckeditor4 - shortcut to open dialog")
    tip_cked4 = "edit current field in ckeditor4 (html code of the field will be modified a lot (cleaned))"
    if cut_cked4:
        tip_cked4 += " ({})".format(keystr(cut_cked4))

    cut_cked4old = gc("Ckeditor4 (old version) - shortcut to open dialog")
    tip_cked4old = "edit current field in ckeditor4 (html code of the field will be modified a lot (cleaned))"
    if cut_cked4old:
        tip_cked4old += " ({})".format(keystr(cut_cked4old))

    cut_cked5 = gc("Ckeditor5 - shortcut to open dialog")
    tip_cked5 = "edit current field in ckeditor5"
    if cut_cked5:
        tip_cked5 += " ({})".format(keystr(cut_cked5))

    arglist = [
        #  0                                       1           2            3            4       5
        # show                                   shortcut     tooltip    functionarg    cmd    icon 
        [gc("TinyMCE4 - enable")               , cut_T4,      tip_T4,      "T4"      ,  "T4",   None],
        [gc("TinyMCE5 - enable")               , cut_T5,      tip_T5,      "T5"      ,  "T5",   None],
        [gc("Ckeditor4 - enable")              , cut_cked4,   tip_cked4,   "cked4"   ,  "c4",   None],
        [gc("Ckeditor4 (old version) - enable"), cut_cked4old,tip_cked4old,"cked4old",  "c4o",  None],
        [gc("Ckeditor5 - enable")              , cut_cked5,   tip_cked5,   "cked5"   ,  "c5",   None],
    ]
    for line in arglist:
        if not line[0]:
            continue
        b = editor.addButton(
            icon=line[5],  # os.path.join(addon_path, "icons", "tm.png"),
            cmd=line[4],
            func=lambda e=editor,n=line[3]: external_editor_start(e, n),
            tip=line[2],
            keys=keystr(line[1]) if line[1] else "",
            )
        buttons.append(b)

    return buttons
addHook("setupEditorButtons", setupEditorButtonsFilter)
