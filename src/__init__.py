from aqt import mw
from anki.hooks import addHook, runHook, wrap

def gc(arg, fail=False):
    return mw.addonManager.getConfig(__name__).get(arg, fail)


def tinyloader():
    if gc('experimental_paste_support', False):
        from . import DragDropPaste
    else:
        from . import external_js_editor_for_field

addHook('profileLoaded', tinyloader)


