"""
anki-addon: open field contents in WYSIWYG-Editor (like TinyMCE)

Copyright (c) 2019 ignd
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



This add-on bundles "TinyMCE" in the folder web/tinymce
    "TinyMCE" was downloaded from http://download.tiny.cloud/tinymce/community/tinymce_4.9.8.zip
    "TinyMCE" contains web/tinymce/js/tinymce/license.txt
    "TinyMCE" is licensed as LPGL 2.1 (or later)

    The tinymce package does not contain any information on the copyright.
    TinyMCE is developed at https://github.com/tinymce/tinymce
    For years there's been a CLA at https://github.com/tinymce/tinymce/blob/master/modules/tinymce/readme.md
    that states that each contributor agress that the copyright is changed to Ephox Corporation.
    So likely tinymce is: copyright (c) Ephox Corporation.



This add-on bundles the file "sync_execJavaScript.py" which has this copyright and permission
notice: 

    Copyright: 2014 - 2016 Detlev Offenbach <detlev@die-offenbachs.de>
                  (taken from https://github.com/pycom/EricShort/blob/master/UI/Previewers/PreviewerHTML.py)
    License: GPLv3 or later, https://github.com/pycom/EricShort/blob/025a9933bdbe92f6ff1c30805077c59774fa64ab/LICENSE.GPL3
"""

import os
import io
import time

from anki.hooks import addHook

import aqt
from aqt import mw
from aqt.qt import *
from aqt.utils import (
     askUser,
     saveGeom,
     restoreGeom,
     showInfo
)
from aqt.editor import Editor
from aqt.webview import AnkiWebView


import warnings
import requests
import re
import json
import urllib.request, urllib.parse, urllib.error
from bs4 import BeautifulSoup

from anki.hooks import wrap
from anki.sync import AnkiRequestsClient

import aqt
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, askUser
from aqt.editor import Editor
from aqt.webview import AnkiWebView

from .config import gc
from .sync_execJavaScript import sync_execJavaScript


addon_path = os.path.dirname(__file__)
addonfoldername = os.path.basename(addon_path)
regex = r"(web.*)"
mw.addonManager.setWebExports(__name__, regex)
web_path = "/_addons/%s/web/" % addonfoldername


addon_cssfiles = ["webview_override.css",
                  ]
other_cssfiles = []
cssfiles = addon_cssfiles + other_cssfiles

addon_jsfiles = ["tinymce4/js/tinymce/tinymce.min.js",
                 "my_editor.js"]
other_jsfiles = ["jquery.js",
                 ]
jsfiles = addon_jsfiles + other_jsfiles


pics = ("jpg", "jpeg", "png", "tif", "tiff", "gif", "svg", "webp")
audio = ("wav", "mp3", "ogg", "flac", "mp4", "swf", "mov",
         "mpeg", "mkv", "m4a", "3gp", "spx", "oga", "webm")


class Edit():
    def __init__(self, parent, mw):
        self.parentWindow = parent
        self.mw = mw
        self.setupWeb()

    def urlToLink(self, url):
        fname = self.urlToFile(url)
        if not fname:
            return None
        return self.fnameToLink(fname)

    def fnameToLink(self, fname):
        ext = fname.split(".")[-1].lower()
        if ext in pics:
            name = urllib.parse.quote(fname.encode("utf8"))
            return '<img src="%s">' % name
        else:
            anki.sound.clearAudioQueue()
            anki.sound.play(fname)
            return '[sound:%s]' % fname

    def urlToFile(self, url):
        l = url.lower()
        for suffix in pics+audio:
            if l.endswith("." + suffix):
                return self._retrieveURL(url)
        # not a supported type
        return

    def isURL(self, s):
        s = s.lower()
        return (s.startswith("http://")
                or s.startswith("https://")
                or s.startswith("ftp://")
                or s.startswith("file://"))

    def inlinedImageToFilename(self, txt):
        prefix = "data:image/"
        suffix = ";base64,"
        for ext in ("jpg", "jpeg", "png", "gif"):
            fullPrefix = prefix + ext + suffix
            if txt.startswith(fullPrefix):
                b64data = txt[len(fullPrefix):].strip()
                data = base64.b64decode(b64data, validate=True)
                if ext == "jpeg":
                    ext = "jpg"
                return self._addPastedImage(data, "."+ext)

        return ""

    def inlinedImageToLink(self, src):
        fname = self.inlinedImageToFilename(src)
        if fname:
            return self.fnameToLink(fname)

        return ""

    # ext should include dot
    def _addPastedImage(self, data, ext):
        # hash and write
        csum = checksum(data)
        fname = "{}-{}{}".format("paste", csum, ext)
        return self._addMediaFromData(fname, data)

    def _retrieveURL(self, url):
        "Download file into media folder and return local filename or None."
        # urllib doesn't understand percent-escaped utf8, but requires things like
        # '#' to be escaped.
        url = urllib.parse.unquote(url)
        if url.lower().startswith("file://"):
            url = url.replace("%", "%25")
            url = url.replace("#", "%23")
            local = True
        else:
            local = False
        # fetch it into a temporary folder
        self.mw.progress.start(
            immediate=not local, parent=self.parentWindow)
        ct = None
        try:
            if local:
                req = urllib.request.Request(url, None, {
                    'User-Agent': 'Mozilla/5.0 (compatible; Anki)'})
                filecontents = urllib.request.urlopen(req).read()
            else:
                reqs = AnkiRequestsClient()
                reqs.timeout = 30
                r = reqs.get(url)
                if r.status_code != 200:
                    showWarning(_("Unexpected response code: %s") %
                                r.status_code)
                    return
                filecontents = r.content
                ct = r.headers.get("content-type")
        except urllib.error.URLError as e:
            showWarning(_("An error occurred while opening %s") % e)
            return
        except requests.exceptions.RequestException as e:
            showWarning(_("An error occurred while opening %s") % e)
            return
        finally:
            self.mw.progress.finish()
        # strip off any query string
        url = re.sub(r"\?.*?$", "", url)
        path = urllib.parse.unquote(url)
        return self.mw.col.media.writeData(path, filecontents, typeHint=ct)

    # Paste/drag&drop
    ######################################################################

    removeTags = ["script", "iframe", "object", "style"]

    def _pastePreFilter(self, html, internal):
        with warnings.catch_warnings() as w:
            warnings.simplefilter('ignore', UserWarning)
            doc = BeautifulSoup(html, "html.parser")

        if not internal:
            for tag in self.removeTags:
                for node in doc(tag):
                    node.decompose()

            # convert p tags to divs
            for node in doc("p"):
                node.name = "div"

        for tag in doc("img"):
            try:
                src = tag['src']
            except KeyError:
                # for some bizarre reason, mnemosyne removes src elements
                # from missing media
                continue

            # in internal pastes, rewrite mediasrv references to relative
            if internal:
                m = re.match(r"http://127.0.0.1:\d+/(.*)$", src)
                if m:
                    tag['src'] = m.group(1)
            else:
                # in external pastes, download remote media
                if self.isURL(src):
                    fname = self._retrieveURL(src)
                    if fname:
                        tag['src'] = fname
                elif src.startswith("data:image/"):
                    # and convert inlined data
                    tag['src'] = self.inlinedImageToFilename(src)

        html = str(doc)
        return html

    def doPaste(self, html, internal, extended=False):
        html = self._pastePreFilter(html, internal)
        if extended:
            extended = "true"
        else:
            extended = "false"
        # self.web.eval("pasteHTML(%s, %s, %s);" % (
        #    json.dumps(html), json.dumps(internal), extended))
        jscmd = """pasteHTML(`%s`);""" % html
        # self.web.sync_execJavaScript(jscmd) # anki freezes
        self.web.eval(jscmd)

    def doDrop(self, html, internal):
        self.web.evalWithCallback("makeDropTargetCurrent();",
                                  lambda _: self.doPaste(html, internal))

    def onPaste(self):
        self.web.onPaste()

    def onCutOrCopy(self):
        self.web.flagAnkiText()

    def setupWeb(self):
        self.web = MyWebView(self.parentWindow, self)
        self.web.onBridgeCmd = self.onBridgeCmd

    def onBridgeCmd(self, cmd):
        if cmd == "paste":
            self.onPaste()
        elif cmd == "cutOrCopy":
            onCutOrCopy()


class MyWebView(AnkiWebView):
    def __init__(self, parent, editor):
        AnkiWebView.__init__(self, parent)
        self.mw = aqt.mw
        self.parentWindow = self
        self.editor = editor
        self.allowDrops = True

    def sync_execJavaScript(self, script):
        return sync_execJavaScript(self, script)

    def bundledScript(self, fname):
        if fname in addon_jsfiles:
            return '<script src="%s"></script>' % (web_path + fname)
        else:
            return '<script src="%s"></script>' % self.webBundlePath(fname)

    def bundledCSS(self, fname):
        if fname in addon_cssfiles:
            return '<link rel="stylesheet" type="text/css" href="%s">' % (web_path + fname)
        else:
            return '<link rel="stylesheet" type="text/css" href="%s">' % self.webBundlePath(fname)


    def onCut(self):
        self.triggerPageAction(QWebEnginePage.Cut)

    def onCopy(self):
        self.triggerPageAction(QWebEnginePage.Copy)

    def _onPaste(self, mode):
        extended = True
        mime = self.editor.mw.app.clipboard().mimeData(mode=mode)
        html, internal = self._processMime(mime)
        if not html:
            return
        self.editor.doPaste(html, internal, extended)

    def onPaste(self):
        self._onPaste(QClipboard.Clipboard)

    def onMiddleClickPaste(self):
        self._onPaste(QClipboard.Selection)

    def dropEvent(self, evt):
        mime = evt.mimeData()

        if evt.source() and mime.hasHtml():
            # don't filter html from other fields
            html, internal = mime.html(), True
        else:
            html, internal = self._processMime(mime)

        if not html:
            return

        self.editor.doDrop(html, internal)

    # returns (html, isInternal)
    def _processMime(self, mime):
        # print("html=%s image=%s urls=%s txt=%s" % (
        #     mime.hasHtml(), mime.hasImage(), mime.hasUrls(), mime.hasText()))
        # print("html", mime.html())
        # print("urls", mime.urls())
        # print("text", mime.text())

        # try various content types in turn
        html, internal = self._processHtml(mime)
        if html:
            return html, internal

        # favour url if it's a local link
        if mime.hasUrls() and mime.urls()[0].toString().startswith("file://"):
            types = (self._processUrls, self._processImage, self._processText)
        else:
            types = (self._processImage, self._processUrls, self._processText)

        for fn in types:
            html = fn(mime)
            if html:
                return html, False
        return "", False

    def _processUrls(self, mime):
        if not mime.hasUrls():
            return

        url = mime.urls()[0].toString()
        # chrome likes to give us the URL twice with a \n
        url = url.splitlines()[0]
        return self.editor.urlToLink(url)

    def _processText(self, mime):
        if not mime.hasText():
            return

        txt = mime.text()

        # inlined data in base64?
        if txt.startswith("data:image/"):
            return self.editor.inlinedImageToLink(txt)

        # if the user is pasting an image or sound link, convert it to local
        if self.editor.isURL(txt):
            url = txt.split("\r\n")[0]
            link = self.editor.urlToLink(url)
            if link:
                return link

            # not media; add it as a normal link if pasting with shift
            link = '<a href="{}">{}</a>'.format(
                url, html.escape(txt)
            )
            return link

        # normal text; convert it to HTML
        txt = html.escape(txt)
        txt = txt.replace("\n", "<br>")\
            .replace("\t", " "*4)

        # if there's more than one consecutive space,
        # use non-breaking spaces for the second one on
        def repl(match):
            return " " + match.group(1).replace(" ", "&nbsp;")
        txt = re.sub(" ( +)", repl, txt)

        return txt

    def _processHtml(self, mime):
        if not mime.hasHtml():
            return None, False
        html = mime.html()

        # no filtering required for internal pastes
        if html.startswith("<!--anki-->"):
            return html[11:], True

        return html, False

    def _processImage(self, mime):
        if not mime.hasImage():
            return
        im = QImage(mime.imageData())
        uname = namedtmp("paste")
        if self.editor.mw.pm.profile.get("pastePNG", False):
            ext = ".png"
            im.save(uname+ext, None, 50)
        else:
            ext = ".jpg"
            im.save(uname+ext, None, 80)

        # invalid image?
        path = uname+ext
        if not os.path.exists(path):
            return

        data = open(path, "rb").read()
        fname = self.editor._addPastedImage(data, ext)
        if fname:
            return self.editor.fnameToLink(fname)

    def flagAnkiText(self):
        # be ready to adjust when clipboard event fires
        self._markInternal = True

    def _flagAnkiText(self):
        # add a comment in the clipboard html so we can tell text is copied
        # from us and doesn't need to be stripped
        clip = self.editor.mw.app.clipboard()
        if not isMac and not clip.ownsClipboard():
            return
        mime = clip.mimeData()
        if not mime.hasHtml():
            return
        html = mime.html()
        mime.setHtml("<!--anki-->" + html)
        clip.setMimeData(mime)

    def contextMenuEvent(self, evt):
        m = QMenu(self)
        a = m.addAction(_("Cut"))
        a.triggered.connect(self.onCut)
        a = m.addAction(_("Copy"))
        a.triggered.connect(self.onCopy)
        a = m.addAction(_("Paste"))
        a.triggered.connect(self.onPaste)
        runHook("EditorWebView.contextMenuEvent", self, m)
        m.popup(QCursor.pos())













class MyDialog(QDialog):
    def __init__(self, parent, bodyhtml):
        super(MyDialog, self).__init__(parent)

        self.jsSavecommand = "tinyMCE.activeEditor.getContent();"
        self.setWindowTitle('Anki - edit current field in TinyMCE4')
        self.resize(810, 1100)
        restoreGeom(self, "805891399_winsize")

        mainLayout = QVBoxLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        self.setLayout(mainLayout)
        self.edit = Edit(self, aqt.mw)
        self.edit.web.allowDrops = False   # default in webview/AnkiWebView is False
        self.edit.web.title = "tinymce4"
        self.edit.web.contextMenuEvent = self.contextMenuEvent
        mainLayout.addWidget(self.edit.web)

        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        mainLayout.addWidget(self.buttonBox)

        self.buttonBox.accepted.connect(self.onAccept)
        self.buttonBox.rejected.connect(self.onReject)
        QMetaObject.connectSlotsByName(self)
        acceptShortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        acceptShortcut.activated.connect(self.onAccept)

        self.edit.web.stdHtml(bodyhtml, cssfiles, jsfiles)

    def onAccept(self):
        global editedfieldcontent
        editedfieldcontent = self.edit.web.sync_execJavaScript(self.jsSavecommand)
        self.edit.web = None  # doesn't remove?
        # self.edit.web._page.windowCloseRequested()  # native qt signal not callable
        # self.edit.web._page.windowCloseRequested.connect(self.edit.web._page.window_close_requested)
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


def on_WYSIWYGdialog_finished(self, status):
    if status:
        self.saveNow(lambda: self._onWYSIWYGUpdateField())
Editor.on_WYSIWYGdialog_finished = on_WYSIWYGdialog_finished


def wysiwyg_dialog(self, field):
    bodyhtml = templatecontent % (
        gc('fontSize'),
        gc('font'),
        self.note.fields[field]
        )
    d = MyDialog(None, bodyhtml)
    # exec_() doesn't work, see  https://stackoverflow.com/questions/39638749/
    d.finished.connect(self.on_WYSIWYGdialog_finished)
    d.setModal(True)
    d.show()
    d.edit.web.setFocus()
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
    c = ceA['createNewNote']  # createNewNote toAddWindow
    newNote = mw.col.newNote()
    newNote.mid = c['mid']    # model id
    tags = c['tags']
    newNote.tags = [t for t in tags.split(" ") if t]   # see tags.py
    newNote.fields[c['fdx']] = val
    newNote.flush()
    mw.col.addNote(newNote)
# nid = newNote.id   #reinsert new nid as a reference?


def readfile():
    addondir = os.path.join(os.path.dirname(__file__))
    filefullpath = os.path.join(addondir, "template_tiny4_body_paste.html")
    with io.open(filefullpath, 'r', encoding='utf-8') as f:
        return f.read()
templatecontent = readfile()


def tiny4_start(self):
    self.myfield = self.currentField
    self.saveNow(lambda: self.wysiwyg_dialog(self.myfield))


def keystr(k):
    key = QKeySequence(k)
    return key.toString(QKeySequence.NativeText)


def setupEditorButtonsFilter(buttons, editor):
    if gc('tinymce4Hotkey'):
        b = editor.addButton(
            icon=None,  # os.path.join(addon_path, "icons", "tm.png"),
            cmd="T4",
            func=tiny4_start,
            tip="edit current field in external window ({})".format(keystr(gc('tinymce4Hotkey'))),
            keys=gc('tinymce4Hotkey'))
        buttons.append(b)
    return buttons
addHook("setupEditorButtons", setupEditorButtonsFilter)
