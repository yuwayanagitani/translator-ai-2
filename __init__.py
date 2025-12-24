from __future__ import annotations

from typing import Any

from aqt import gui_hooks, mw
from aqt.qt import QAction
from aqt.utils import showInfo, showWarning

from .config import load_config, show_config_dialog
from .translate import translate_note_fields

ADDON_NAME = __name__.split(".")[0]


def _translate_selected(browser: Any) -> None:
    note_ids = browser.selectedNotes()
    if not note_ids:
        showInfo("No notes selected.")
        return

    config = load_config()

    mw.progress.start(label="Translating notes...", immediate=True)
    translated_count = 0
    try:
        for note_id in note_ids:
            note = mw.col.get_note(note_id)
            if translate_note_fields(note, config):
                note.flush()
                translated_count += 1
    except Exception as error:  # noqa: BLE001
        showWarning(f"Translation failed: {error}")
        return
    finally:
        mw.progress.finish()

    showInfo(f"Translated {translated_count} notes.")


def _add_browser_menu_action(browser: Any) -> None:
    action = QAction("AI Translate Selected Notes", browser)
    action.triggered.connect(lambda: _translate_selected(browser))
    browser.form.menuEdit.addSeparator()
    browser.form.menuEdit.addAction(action)


def _setup_config_action() -> None:
    mw.addonManager.setConfigAction(ADDON_NAME, show_config_dialog)


def _setup_hooks() -> None:
    gui_hooks.browser_menus_did_init.append(_add_browser_menu_action)


_setup_config_action()
_setup_hooks()
