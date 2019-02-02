# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import pathlib, os, shutil, io, time

from aqt import mw
from aqt.qt import *
from anki.hooks import addHook, wrap
from aqt.utils import showInfo
from aqt.editor import Editor

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QShortcut
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

tinymce
- the codemirror source code view plugin (https://github.com/christiaan/tinymce-codemirror) 
didn't work immediatly. I gave up because a separate view without the need to start tinymce might
be better.
- styling the editor with css doesn't work
"""


class MyDialog(QDialog):
    def __init__(self, parent, instance, field, temphtmlfile, windowtitle, jsSavecommand):
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

        self.web.loadFinished.connect(self.load_finished)
        self.web.load(QUrl(temphtmlfileUrl))     


    def load_finished(self, ok):
        self.show() 
        self.web.setFocus()
        

    def onAccept(self):
        global tinyfieldcontent
        tinyfieldcontent = self.__execJavaScript("tinyMCE.activeEditor.getContent();")
        self.accept() 


    #via https://riverbankcomputing.com/pipermail/pyqt/2016-May/037449.html
    #https://github.com/pycom/EricShort/blob/master/UI/Previewers/PreviewerHTML.py   #gplv3
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



def _onUpdateField(self):
    try:   
        note = mw.col.getNote(self.nid)
    except:   # new note
        self.note.fields[self.myfield] = tinyfieldcontent
        self.note.flush()
    else:
        note.fields[self.myfield] = tinyfieldcontent
        note.flush()
        mw.requireReset()
        mw.reset()
    self.loadNote(focusTo=self.myfield)
Editor._onUpdateField = _onUpdateField


def on_dialog_finished(self,status):
    if status:
        self.saveNow(lambda: self._onUpdateField())
Editor.on_dialog_finished = on_dialog_finished


addondir = os.path.join(os.path.dirname(__file__))
temphtmlfile = os.path.join(addondir,'temp.html')
temphtmlfileUrl = pathlib.Path(temphtmlfile).as_uri()

def _start_dialog(self,field,templatecontent, windowtitle, jsSavecommand):
    self.fieldcontents = self.note.fields[field]
    ##remove StartFragment/Endfragment so that ckeditor works
    self.fieldcontents = self.fieldcontents.replace("<!--StartFragment-->","")
    self.fieldcontents = self.fieldcontents.replace("<!--EndFragment-->","")
    temporary = templatecontent % (self.fieldcontents)
    with io.open(temphtmlfile,'w',encoding='utf-8') as f:
         f.write(temporary)
    d = MyDialog(None, self, field, temphtmlfile, windowtitle, jsSavecommand)
    #exec_() doesn't work - tinymce isn't loaded = blocked
    #finished.connect via https://stackoverflow.com/questions/39638749/pyqt4-why-does-qdialog-returns-from-exec-when-setvisiblefalse
    d.finished.connect(self.on_dialog_finished)
    d.setModal(True)
    d.show()
Editor._start_dialog = _start_dialog


def start_dialog(self,templatecontent, windowtitle, jsSavecommand):
    self.myfield = self.currentField
    self.saveNow(lambda: self._start_dialog(self.myfield, templatecontent, windowtitle, jsSavecommand))
Editor.start_dialog = start_dialog


wyE = {
    'tinymce':{
        'templatefile': "template_tiny.html",
        'windowtitle': 'Anki - edit current field in TinyMCE',
        'jsSaveCommand': "tinyMCE.activeEditor.getContent();"
    },
    'ckeditor5': {
        'templatefile': "template_ck5.html",
        'windowtitle': 'Anki - edit current field in ckEditor5',
        'jsSaveCommand': "myeditor.getData();"
    },
    'ckeditor4': {
        'templatefile': "template_ck4.html",
        'windowtitle': 'Anki - edit current field in ckEditor4',
        'jsSaveCommand': "myeditor.getData();"
    }
}

def readfile(file):
    filefullpath = os.path.join(addondir, file)
    with io.open(filefullpath,'r',encoding='utf-8') as f:
        return f.read()


#loading file contents only once might be faster
for k,v in wyE.items():
    wyE[k]['templatecontents'] = readfile(v['templatefile'])


def tiny_start(self):
    profilename = mw.pm.name
    replacement = """document_base_url: '../../../{}/collection.media/', """.format(profilename)
    templatecontent = wyE['tinymce']['templatecontents'].replace("""document_base_url: '',""", replacement)                    
    windowtitle = wyE['tinymce']['windowtitle']
    jsSavecommand = wyE['tinymce']['jsSaveCommand']
    self.start_dialog(templatecontent, windowtitle, jsSavecommand)



def ck5_start(self):
    #as far as I see the equivalent to tinymce's document_base_url in tincymce4 is baseHref,
    # https://ckeditor.com/docs/ckeditor4/latest/api/CKEDITOR_config.html#cfg-baseHref
    # baseHref is not in ckeditor5 as of 2019-01, see  https://github.com/ckeditor/ckeditor5/issues/665
    pass


def ck4_start(self):
    pass


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