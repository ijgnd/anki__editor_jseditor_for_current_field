from aqt import mw
from anki.hooks import addHook, runHook, wrap

from .config import gc


def tinyloader():
    if False: # gc('experimental_paste_support', False):
        from . import DragDropPaste
    else:
        from . import external_js_editor_for_field

addHook('profileLoaded', tinyloader)
