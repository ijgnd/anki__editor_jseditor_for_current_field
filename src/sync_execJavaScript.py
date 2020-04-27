"""
Copyright: 2014 - 2016 Detlev Offenbach <detlev@die-offenbachs.de>

License: GPLv3 or later, https://github.com/pycom/EricShort/blob/025a9933bdbe92f6ff1c30805077c59774fa64ab/LICENSE.GPL3

via https://riverbankcomputing.com/pipermail/pyqt/2016-May/037449.html
https://github.com/pycom/EricShort/blob/master/UI/Previewers/PreviewerHTML.py
"""


def sync_execJavaScript(self, script):
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

    self.page().runJavaScript(
        script, resultCallback)
    loop.exec_()
    return resultDict["res"]
