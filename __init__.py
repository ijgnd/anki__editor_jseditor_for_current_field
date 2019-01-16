# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pathlib, os, shutil, io, time

from aqt import mw
from aqt.qt import *
from anki.hooks import addHook, wrap
from aqt.utils import showInfo

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox
from PyQt5.QtCore import Qt, QMetaObject

config = mw.addonManager.getConfig(__name__)

"""
ckeditor5 doesn't offer anything over tinymce at the moment. But it might change?

ckeditor5 is sensitive: ckeditor doesn't load properly if the html
in the editor area contains "<!--StartFragment--><!--EndFragment-->"
so I need to remove them first.
ckeditor modifies the content more than tinymce: it removes some 
formatting.
a workaround to set the contents of ckeditor after loading with something like
self.web.page().runJavaScript('myeditor.setData( ' + '`' + self.contents + '`' + ');')
doesn't work.

ckeditor4 doesn't work:  I wanted to see what it offers but the edtior doesn't load. So
I didn't even come to implementing a save command. 

for tinymce the codemirror source code view plugin (https://github.com/christiaan/tinymce-codemirror) 
didn't work immediatly. I gave up because a separate view without the need to start tinymce might
be better.
"""


editorfolders = ["ckeditor5-build-decoupled-document__v11.2.0","tinymce492","ckeditor4_11_1_full"]

def copy_editorfolders_to_media_folder():
    addondir = os.path.join(os.path.dirname(__file__))
    media_dir = mw.col.media.dir()
    for f in editorfolders:
        src = os.path.join(addondir,f)
        dest = os.path.join(media_dir,f)
        if not os.path.exists(dest):
            shutil.copytree(src, dest)

addHook('profileLoaded', copy_editorfolders_to_media_folder)



class MyDialog(QDialog):
    def __init__(self, parent, instance, html, field, windowtitle, jsSavecommand):
        super(MyDialog, self).__init__(parent)
        self.instance = instance
        self.field = field
        self.nid = instance.note.id
        self.jsSavecommand = jsSavecommand

        self.setWindowTitle(windowtitle)
        self.resize(790,1100)

        mainLayout = QVBoxLayout()
        mainLayout.setContentsMargins(0,0,0,0)
        mainLayout.setSpacing(0)
        self.setLayout(mainLayout)
        self.web = QWebEngineView(self)
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

        #self.web.setHtml(html)
        #workaround so that media files from collection.media are shown
        #addondir = os.path.join(os.path.dirname(__file__))
        #tfile = os.path.join(addondir,'_temp_tiny.html')
        media_dir = mw.col.media.dir()
        tfile = os.path.join(media_dir,'_temp_external_editor.html')
        #io.open is necessary for windows 10 1809/Anki 2.1.8 - otherwise umlaute don't work
        with io.open(tfile,'w',encoding='utf-8') as f:
            f.write(html)
        url = pathlib.Path(tfile).as_uri()
       
        self.web.loadFinished.connect(self.load_finished)
        self.web.load(QUrl(url))


    def load_finished(self, ok):
        self.show() 
        self.web.setFocus()


    def onAccept(self):
        self.web.page().runJavaScript(self.jsSavecommand, self.store_value)
        #time.sleep(0.2)
        self.accept() 


    def store_value(self, param):
        #make sure that if in the browser another note is
        #opened while the js-edit window is open the correct
        #note gets updated upon closing
        #showInfo(param)   # works
        try:   
            note = mw.col.getNote(self.nid)
        except:   # new note
            self.instance.note.fields[self.field] = param
            #time.sleep(0.1)
            self.instance.note.flush()
            #time.sleep(0.1)
        else:
            note.fields[self.field] = param
            note.flush()
            mw.requireReset()
            mw.reset()
        self.instance.loadNote(focusTo=self.field)


def start_dialog(self,shellfilename,windowtitle,jsSavecommand):
    field = self.currentField
    contents = self.note.fields[field]
    ##remove StartFragment/Endfragment so that ckeditor works
    contents = contents.replace("<!--StartFragment-->","")
    contents = contents.replace("<!--EndFragment-->","")
    ##leftover from initial try when tinymce was in bin/web
    #js = ""
    #for l in ["tinymce/tinymce.min.js", "jquery.js"]:
    #    js += mw.web.bundledScript(l) + '\n'
    path = os.path.dirname(os.path.realpath(__file__))
    htmlfile = os.path.join(path,shellfilename)
    with io.open(htmlfile,'r',encoding='utf-8') as f:
        h = f.read()
    # html = h % (js, contents)
    html = h % (contents)
    d = MyDialog(None, self, html, field,windowtitle,jsSavecommand)
    d.show() 


def tiny_start(self):
    htmlfile = "shell_tiny.html"
    windowtitle = 'Anki - edit current field in TinyMCE'
    jsSavecommand = "tinyMCE.activeEditor.getContent();"
    start_dialog(self,htmlfile,windowtitle,jsSavecommand)


def ck5_start(self):
    htmlfile = "shell_ck5.html"
    windowtitle = 'Anki - edit current field in ckEditor5'
    jsSavecommand = "myeditor.getData();"
    start_dialog(self,htmlfile,windowtitle,jsSavecommand)


def ck4_start(self):
    htmlfile = "shell_ck4.html"
    windowtitle = 'Anki - edit current field in ckEditor4'
    jsSavecommand = "myeditor.getData();"
    start_dialog(self,htmlfile,windowtitle,jsSavecommand)


def keystr(k):
    key = QKeySequence(k)
    return key.toString(QKeySequence.NativeText)


def setupEditorButtonsFilter(buttons, editor):
    if config['tinymceHotkey']:
        b = editor.addButton(
            icon=None, # os.path.join(addon_path, "icons", "tm.png"), 
            cmd="TM", 
            func=tiny_start, 
            tip="edit current field in external window ({})".format(keystr(config['tinymceHotkey'])),
            keys=config['tinymceHotkey']) 
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