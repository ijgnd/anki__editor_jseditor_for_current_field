# -*- coding: utf-8 -*-

"""
anki-addon: open field contents in WYSIWYG-Editor(like TinyMCE)
Copyright (C) 2018 ignd
with code form
Copyright (c) 2014 - 2016 Detlev Offenbach <detlev@die-offenbachs.de> (the function __execJavaScript)
Copyright: Damien Elmes <anki@ichi2.net>, https://github.com/dae/anki/blob/master/aqt/editor.py

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import pathlib, os, shutil, io, time

from aqt import mw
from aqt.qt import *
from anki.hooks import addHook, wrap
from aqt.utils import showInfo
from aqt.editor import Editor
from aqt.webview import AnkiWebView


# from PyQt5.QtGui import QKeySequence
# from PyQt5.QtWebEngineWidgets import QWebEngineView
# from PyQt5.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QShortcut
# from PyQt5.QtCore import Qt, QMetaObject, QObject, pyqtSlot
# from PyQt5.QtWebChannel import QWebChannel



config = mw.addonManager.getConfig(__name__)
regex = r"(tinymce4.*|tinymce5.*|ckeditor4.*|ckeditor5.*)"
mw.addonManager.setWebExports(__name__, regex)


"""
At the moment only tinymce4 works. The other editors are there so in the future
it's easier to change.


tinymce4
- the codemirror source code view plugin (https://github.com/christiaan/tinymce-codemirror) 
didn't work immediatly. I gave up because a separate view without the need to start tinymce might
be better.
- footnotes? this doesn't work https://github.com/rainywalker/footNotes/


tinymce5 


ckeditor5 doesn't offer anything over tinymce at the moment. But it might change?

ckeditor5 is sensitive: ckeditor doesn't load properly if the html
in the editor area contains "<!--StartFragment--><!--EndFragment-->"
so I need to remove them first.
ckeditor modifies the content more than tinymce: it removes some 
formatting.
a workaround to set the contents of ckeditor after loading with something like
self.web.page().runJavaScript('myeditor.setData( ' + '`' + self.contents + '`' + ');')
doesn't work.

ckeditor4 
- doesn't work:  I wanted to see what it offers but the editor doesn't load. So
I didn't even come to implementing a save command. 
- maybe footnotes plugin - https://github.com/andykirk/CKEditorFootnotes /
https://ckeditor.com/cke4/addon/footnotes ?

"""

class CallHandler(QObject):
    @pyqtSlot()
    def test(self):
        showInfo('call received')


class MyDialog(QDialog):
    def __init__(self, parent, bodyhtml, windowtitle, jsSavecommand):
        super(MyDialog, self).__init__(parent)

        self.jsSavecommand = jsSavecommand
        self.setWindowTitle(windowtitle)
        self.resize(810,1100)

        mainLayout = QVBoxLayout()
        mainLayout.setContentsMargins(0,0,0,0)
        mainLayout.setSpacing(0)
        self.setLayout(mainLayout)
        self.web = AnkiWebView(self)
        channel = QWebChannel()
        handler = CallHandler()
        channel.registerObject('handler', handler)
        self.web.page().setWebChannel(channel)
        self.web.contextMenuEvent = self.contextMenuEvent       
        mainLayout.addWidget(self.web)

        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Save)
        mainLayout.addWidget(self.buttonBox)
        
        self.buttonBox.accepted.connect(self.onAccept)
        self.buttonBox.rejected.connect(self.reject)
        QMetaObject.connectSlotsByName(self)
        acceptShortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        acceptShortcut.activated.connect(self.onAccept)

        """
        for key, fn in [
                # (QKeySequence.Copy, self.onCopy),
                (QKeySequence.Paste, self.onPaste),
                # (QKeySequence.Cut, self.onCut),
                # (QKeySequence.SelectAll, self.onSelectAll),
            ]:
                QShortcut(key, self.web,
                          context=Qt.WidgetWithChildrenShortcut,
                          activated=fn)
        # QShortcut(QKeySequence("ctrl+v"), self,
        #         context=Qt.WidgetWithChildrenShortcut, activated=self.onPaste)

        """
        # self.web.loadFinished.connect(self.load_finished)
        # self.web.load(QUrl(temphtmlfileUrl))
        js = None
        self.web.stdHtml(bodyhtml,None,js)
            


    def load_finished(self, ok):
        self.show() 
        self.web.setFocus()


    # def onPaste(self):
    #     print('pasted')

    # def paste(self):
    #     self._trigger_action(QWebEnginePage.Paste)
    #def paste(self):
    #     print('pasted')
    #     self._trigger_action(QWebEnginePage.Paste)
        

    def onAccept(self):
        global editedfieldcontent
        editedfieldcontent = self.__execJavaScript(self.jsSavecommand)
        self.accept() 


    #via https://riverbankcomputing.com/pipermail/pyqt/2016-May/037449.html
    #https://github.com/pycom/EricShort/blob/master/UI/Previewers/PreviewerHTML.py   
    def __execJavaScript(self, script):
        """
        Private function to execute a JavaScript function Synchroneously.
        
        @param script JavaScript script source to be executed
        @type str
        @return result of the script
        @rtype depending upon script result
        """
        from PyQt5.QtCore import QEventLoop
        loop = QEventLoop()
        resultDict = {"res": None}
        
        def resultCallback(res, resDict=resultDict):
            if loop and loop.isRunning():
                resDict["res"] = res
                loop.quit()
        
        self.web.page().runJavaScript(
            script, resultCallback)
        
        loop.exec_()
        return resultDict["res"]



def _onWYSIWYGUpdateField(self):
    try:   
        note = mw.col.getNote(self.nid)
    except:   # new note
        self.note.fields[self.myfield] = editedfieldcontent
        self.note.flush()
    else:
        note.fields[self.myfield] = editedfieldcontent
        note.flush()
        mw.requireReset()
        mw.reset()
    self.loadNote(focusTo=self.myfield)
Editor._onWYSIWYGUpdateField = _onWYSIWYGUpdateField


def on_WYSIWYGdialog_finished(self,status):
    if status:
        self.saveNow(lambda: self._onWYSIWYGUpdateField())
Editor.on_WYSIWYGdialog_finished = on_WYSIWYGdialog_finished


addondir = os.path.join(os.path.dirname(__file__))
temphtmlfile = os.path.join(addondir,'temp.html')
temphtmlfileUrl = pathlib.Path(temphtmlfile).as_uri()


def _wysiwyg_dialog(self, bodyhtml, windowtitle, jsSavecommand):
    d = MyDialog(None, bodyhtml, windowtitle, jsSavecommand)
    #exec_() doesn't work - tinymce isn't loaded = blocked
    #finished.connect via https://stackoverflow.com/questions/39638749/pyqt4-why-does-qdialog-returns-from-exec-when-setvisiblefalse
    d.finished.connect(self.on_WYSIWYGdialog_finished)
    d.setModal(True)
    d.show()
Editor._wysiwyg_dialog = _wysiwyg_dialog


def wysiwyg_dialog(self, bodyhtml, windowtitle, jsSavecommand):
    self.myfield = self.currentField
    self.saveNow(lambda: self._wysiwyg_dialog(bodyhtml, windowtitle, jsSavecommand))
Editor.wysiwyg_dialog = wysiwyg_dialog



def open_in_add_window(val):
    newNote = mw.col.newNote()
    newNote.fields[ceA['toAddWindow']['fdx']] = val
    tags = ceA['toAddWindow']['tags']
    newNote.tags = [t for t in tags.split(" ") if t] 
    deckname = ceA['toAddWindow']['deck']
    modelname = ceA['toAddWindow']['notetype']
    
    addCards = aqt.dialogs.open('AddCards', mw.window())
    addCards.editor.setNote(newNote, focusTo=0)
    addCards.deckChooser.setDeckName(deckname)
    addCards.modelChooser.models.setText(modelname)
    addCards.activateWindow()


def direct_create_new_note(val):
    c = ceA['createNewNote'] # createNewNote toAddWindow
    newNote = mw.col.newNote()
    newNote.mid = c['mid']    #model id
    tags = c['tags']
    newNote.tags = [t for t in tags.split(" ") if t]   # see tags.py
    newNote.fields[c['fdx']] = val
    print(dir(newNote))
    newNote.flush()
    mw.col.addNote(newNote)
#nid = newNote.id   #reinsert new nid as a reference?





wyE = {
    'tinymce4':{
        'templatefile': "template_tiny4_body.html",
        'windowtitle': 'Anki - edit current field in TinyMCE4',
        'jsSaveCommand': "tinyMCE.activeEditor.getContent();",
        'scriptpath': "/_addons/%s/tinymce492/tinymce.min.js" 
    },
    'tinymce5':{
        'templatefile': "template_tiny5_body.html",
        'windowtitle': 'Anki - edit current field in TinyMCE5',
        'jsSaveCommand': "tinyMCE.activeEditor.getContent();",
        'scriptpath': "/_addons/%s/tinymce5/js/tinymce/tinymce.min.js" 
    },
    'ckeditor5': {
        'templatefile': "template_ck5_body.html",
        'windowtitle': 'Anki - edit current field in ckEditor5',
        'jsSaveCommand': "myeditor.getData();",
        'scriptpath': "/_addons/%s/ckeditor5/ckeditor.js" 
    },
    'ckeditor4': {
        'templatefile': "template_ck4_body.html",
        'windowtitle': 'Anki - edit current field in ckEditor4',
        'jsSaveCommand': "myeditor.getData();",
        'scriptpath': "/_addons/%s/ckeditor4/ckeditor.js" 
    }
}

def readfile(file):
    filefullpath = os.path.join(addondir, file)
    with io.open(filefullpath,'r',encoding='utf-8') as f:
        return f.read()


#loading file contents only once might be faster
for k,v in wyE.items():
    wyE[k]['templatecontents'] = readfile(v['templatefile'])


def tiny4_start(self):
    templatecontent = wyE['tinymce4']['templatecontents']                  
    windowtitle = wyE['tinymce4']['windowtitle']
    jsSavecommand = wyE['tinymce4']['jsSaveCommand']
    scriptpath = wyE['tinymce4']['scriptpath']
    fc = self.note.fields[self.currentField]
    #remove StartFragment/Endfragment so that ckeditor works
    fc = fc.replace("<!--StartFragment-->","").replace("<!--EndFragment-->","")
    bodyhtml = templatecontent % (scriptpath % __name__,config['fontSize'],config['font'],fc)
    self.wysiwyg_dialog(bodyhtml, windowtitle, jsSavecommand)


def tiny5_start(self):
    templatecontent = wyE['tinymce5']['templatecontents']
    windowtitle = wyE['tinymce5']['windowtitle']
    jsSavecommand = wyE['tinymce5']['jsSaveCommand']
    scriptpath = wyE['tinymce5']['scriptpath']
    fc = self.note.fields[self.currentField]
    #remove StartFragment/Endfragment so that ckeditor works
    fc = fc.replace("<!--StartFragment-->","").replace("<!--EndFragment-->","")
    bodyhtml = templatecontent % (scriptpath % __name__,config['fontSize'],config['font'],fc)           
    self.wysiwyg_dialog(bodyhtml, windowtitle, jsSavecommand)


def ck5_start(self):
    #as far as I see the equivalent to tinymce's document_base_url in tincymce4 is baseHref,
    # https://ckeditor.com/docs/ckeditor4/latest/api/CKEDITOR_config.html#cfg-baseHref
    # baseHref is not in ckeditor5 as of 2019-01, see  https://github.com/ckeditor/ckeditor5/issues/665
    templatecontent = wyE['ckeditor5']['templatecontents']                  
    windowtitle = wyE['ckeditor5']['windowtitle']
    jsSavecommand = wyE['ckeditor5']['jsSaveCommand']
    scriptpath = wyE['ckeditor5']['scriptpath']
    fc = self.note.fields[self.currentField]
    #remove StartFragment/Endfragment so that ckeditor works
    fc = fc.replace("<!--StartFragment-->","").replace("<!--EndFragment-->","")
    bodyhtml = templatecontent % (scriptpath % __name__,fc)
    self.wysiwyg_dialog(bodyhtml, windowtitle, jsSavecommand)


def ck4_start(self):
    templatecontent = wyE['ckeditor4']['templatecontents']                  
    windowtitle = wyE['ckeditor4']['windowtitle']
    jsSavecommand = wyE['ckeditor4']['jsSaveCommand']
    scriptpath = wyE['ckeditor4']['scriptpath']
    fc = self.note.fields[self.currentField]
    #remove StartFragment/Endfragment so that ckeditor works
    fc = fc.replace("<!--StartFragment-->","").replace("<!--EndFragment-->","")
    bodyhtml = templatecontent % (scriptpath % __name__,fc)
    self.wysiwyg_dialog(bodyhtml, windowtitle, jsSavecommand)



def keystr(k):
    key = QKeySequence(k)
    return key.toString(QKeySequence.NativeText)


def setupEditorButtonsFilter(buttons, editor):
    if config['tinymce4Hotkey']:
        b = editor.addButton(
            icon=None, # os.path.join(addon_path, "icons", "tm.png"), 
            cmd="T4", 
            func=tiny4_start, 
            tip="edit current field in external window ({})".format(keystr(config['tinymce4Hotkey'])),
            keys=config['tinymce4Hotkey']) 
        buttons.append(b)
    if config['tinymce5Hotkey']:
        b = editor.addButton(
            icon=None, # os.path.join(addon_path, "icons", "tm.png"), 
            cmd="T5", 
            func=tiny5_start, 
            tip="edit current field in external window ({})".format(keystr(config['tinymce5Hotkey'])),
            keys=config['tinymce5Hotkey']) 
        buttons.append(b)
    if config['ckeditor5Hotkey']:
        b = editor.addButton(
            icon=None, # os.path.join(addon_path, "icons", "tm.png"), 
            cmd="C5", 
            func=ck5_start, 
            tip="edit current field in external window ({})".format(keystr(config['ckeditor5Hotkey'])),
            keys=config['ckeditor5Hotkey']) 
        buttons.append(b)
    if config['ckeditor4Hotkey']:
        b = editor.addButton(
            icon=None, # os.path.join(addon_path, "icons", "tm.png"), 
            cmd="C4", 
            func=ck4_start, 
            tip="edit current field in external window ({})".format(keystr(config['ckeditor4Hotkey'])),
            keys=config['ckeditor4Hotkey']) 
        buttons.append(b)
    return buttons
addHook("setupEditorButtons", setupEditorButtonsFilter)
