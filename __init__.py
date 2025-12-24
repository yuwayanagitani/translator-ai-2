from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

from aqt import mw, gui_hooks
from aqt.qt import QAction, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QCheckBox
from aqt.utils import tooltip, showInfo

try:
    from aqt.browser import Browser
except Exception:  # pragma: no cover
    Browser = None  # type: ignore


# ----------------------------
# Config
# ----------------------------

DEFAULT_CONFIG: Dict[str, Any] = {
    "question_source_field": "Front",
    "question_target_field": "Front_jp",
    "answer_source_field": "Back",
    "answer_target_field": "Back_jp",

    # Destination deck
    "copy_dest_mode": "same_deck",          # same_deck | default | specified
    "copy_dest_deck_name": "Default",       # used when copy_dest_mode == specified

    "copy_only_if_translated": True,
    "copy_skip_if_already_copied": True,

    "tag_copied": "AI_TranslatedCopy",
    "tag_copy_error": "AI_TranslateCopyError",

    # Internal marker tag to prevent duplicates
    "tag_srcnid_prefix": "srcnid_",         # internal marker tag: f"{prefix}{nid}"
}


def _addon_dir() -> str:
    return os.path.dirname(__file__)


def _config_path() -> str:
    return os.path.join(_addon_dir(), "config.json")


def load_config() -> Dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    path = _config_path()
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                cfg.update(raw)
    except Exception:
        # keep defaults
        pass
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    path = _config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        tooltip(f"設定の保存に失敗: {e}")


# ----------------------------
# Helpers
# ----------------------------

def _get_field(note, name: str) -> str:
    try:
        return (note[name] or "").strip()
    except Exception:
        return ""


def _set_field(note, name: str, value: str) -> None:
    try:
        if name in note:
            note[name] = value
    except Exception:
        return


def _resolve_dest_deck_id(src_card, cfg: Dict[str, Any]) -> int:
    mode = str(cfg.get("copy_dest_mode", "same_deck")).strip().lower()
    if mode == "same_deck":
        return int(getattr(src_card, "did", 1) or 1)

    if mode == "default":
        name = "Default"
    else:
        name = str(cfg.get("copy_dest_deck_name", "Default") or "Default").strip() or "Default"

    # Ensure deck exists and return id
    try:
        did = mw.col.decks.id(name)  # type: ignore[union-attr]
        return int(did)
    except Exception:
        try:
            # Older API fallback
            deck = mw.col.decks.get(mw.col.decks.id(name))  # type: ignore[union-attr]
            return int(deck["id"])
        except Exception:
            return 1


def _marker_tag_for_nid(nid: int, cfg: Dict[str, Any]) -> str:
    prefix = str(cfg.get("tag_srcnid_prefix", "srcnid_") or "srcnid_")
    # tag cannot contain spaces; keep it simple
    return f"{prefix}{nid}"


def _already_copied(src_nid: int, cfg: Dict[str, Any]) -> bool:
    if not bool(cfg.get("copy_skip_if_already_copied", True)):
        return False
    tag = str(cfg.get("tag_copied", "AI_TranslatedCopy") or "AI_TranslatedCopy").strip()
    marker = _marker_tag_for_nid(src_nid, cfg)
    # Search for notes that have both tags
    try:
        q = f'tag:"{tag}" tag:"{marker}"'
        nids = mw.col.find_notes(q)  # type: ignore[union-attr]
        return bool(nids)
    except Exception:
        return False


def _add_note_compat(new_note, did: int) -> None:
    """
    Anki's collection.add_note signature differs across versions.
    Try both.
    """
    try:
        mw.col.add_note(new_note)  # type: ignore[union-attr]
        return
    except TypeError:
        pass

    try:
        mw.col.add_note(new_note, did)  # type: ignore[union-attr]
        return
    except Exception:
        # Let outer handler manage
        raise


def _move_new_cards_to_deck(new_note, did: int) -> None:
    try:
        cards = list(new_note.cards())
    except Exception:
        cards = []
    for c in cards:
        try:
            c.did = did
            c.flush()
        except Exception:
            continue


def create_translated_copy_from_note(src_note, src_card, cfg: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Returns (ok, message)
    """
    src_nid = int(getattr(src_note, "id", 0) or 0)
    if src_nid <= 0:
        return False, "元ノートIDが取得できませんでした。"

    if _already_copied(src_nid, cfg):
        return False, "既にコピー済み（重複防止）"

    q_t = _get_field(src_note, str(cfg.get("question_target_field", "Front_jp")))
    a_t = _get_field(src_note, str(cfg.get("answer_target_field", "Back_jp")))

    if bool(cfg.get("copy_only_if_translated", True)) and not (q_t or a_t):
        return False, "翻訳フィールドが空のためスキップ"

    # New note: same model as src
    try:
        model = src_note.note_type()
        new_note = mw.col.new_note(model)  # type: ignore[union-attr]
    except Exception as e:
        return False, f"新規ノート作成に失敗: {e}"

    # Put translation into source fields (e.g., Front/Back)
    _set_field(new_note, str(cfg.get("question_source_field", "Front")), q_t)
    _set_field(new_note, str(cfg.get("answer_source_field", "Back")), a_t)

    # Tags
    tag_copied = str(cfg.get("tag_copied", "AI_TranslatedCopy") or "").strip()
    marker = _marker_tag_for_nid(src_nid, cfg)
    if tag_copied:
        try:
            new_note.add_tag(tag_copied)
        except Exception:
            pass
    try:
        new_note.add_tag(marker)
    except Exception:
        # fallback
        try:
            if marker not in new_note.tags:
                new_note.tags.append(marker)
        except Exception:
            pass

    did = _resolve_dest_deck_id(src_card, cfg)

    try:
        _add_note_compat(new_note, did)
        # Ensure cards are in desired deck
        _move_new_cards_to_deck(new_note, did)
        try:
            new_note.flush()
        except Exception:
            pass
        return True, "コピー作成完了"
    except Exception as e:
        # Tag the source note as error (optional) – we avoid touching src note to keep this add-on isolated.
        return False, f"追加に失敗: {e}"


# ----------------------------
# UI: Settings dialog (small)
# ----------------------------

class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Translation Copy Builder 設定")

        self.cfg = load_config()

        lay = QFormLayout(self)

        self.dest_mode = QComboBox()
        self.dest_mode.addItems(["same_deck", "default", "specified"])
        self.dest_mode.setCurrentText(str(self.cfg.get("copy_dest_mode", "same_deck")))

        self.dest_deck = QLineEdit()
        self.dest_deck.setText(str(self.cfg.get("copy_dest_deck_name", "Default")))

        self.only_if_translated = QCheckBox("翻訳がある場合のみコピーを作成する")
        self.only_if_translated.setChecked(bool(self.cfg.get("copy_only_if_translated", True)))

        self.skip_dup = QCheckBox("既にコピー済みならスキップする（重複防止）")
        self.skip_dup.setChecked(bool(self.cfg.get("copy_skip_if_already_copied", True)))

        lay.addRow(QLabel("保存先モード"), self.dest_mode)
        lay.addRow(QLabel("指定デッキ名（specified の時のみ）"), self.dest_deck)
        lay.addRow(self.only_if_translated)
        lay.addRow(self.skip_dup)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        lay.addRow(buttons)

        self.dest_mode.currentTextChanged.connect(self._sync_enabled)
        self._sync_enabled()

    def _sync_enabled(self) -> None:
        self.dest_deck.setEnabled(self.dest_mode.currentText().strip().lower() == "specified")

    def _on_save(self) -> None:
        self.cfg["copy_dest_mode"] = self.dest_mode.currentText().strip()
        self.cfg["copy_dest_deck_name"] = self.dest_deck.text().strip() or "Default"
        self.cfg["copy_only_if_translated"] = bool(self.only_if_translated.isChecked())
        self.cfg["copy_skip_if_already_copied"] = bool(self.skip_dup.isChecked())
        save_config(self.cfg)
        self.accept()


# ----------------------------
# Actions
# ----------------------------

def _copy_current_reviewer_card() -> None:
    cfg = load_config()
    r = getattr(mw, "reviewer", None)
    if not r or not getattr(r, "card", None):
        tooltip("Reviewer でカードを表示中に実行してください。")
        return

    card = r.card
    try:
        note = card.note()
    except Exception:
        tooltip("ノートを取得できませんでした。")
        return

    ok, msg = create_translated_copy_from_note(note, card, cfg)
    if ok:
        tooltip(msg)
    else:
        tooltip(msg)


def _copy_selected_browser_notes(browser: Browser) -> None:
    cfg = load_config()
    nids = []
    try:
        nids = list(browser.selectedNotes())
    except Exception:
        pass

    if not nids:
        tooltip("ノートが選択されていません。")
        return

    ok_cnt = 0
    skip_cnt = 0
    err_cnt = 0

    for nid in nids:
        try:
            note = mw.col.get_note(nid)  # type: ignore[union-attr]
            # pick a representative card for deck selection:
            cards = note.cards()
            card = cards[0] if cards else None
            if card is None:
                skip_cnt += 1
                continue
            ok, msg = create_translated_copy_from_note(note, card, cfg)
            if ok:
                ok_cnt += 1
            else:
                # treat "skip" messages as skip
                if "スキップ" in msg or "既にコピー済み" in msg:
                    skip_cnt += 1
                else:
                    err_cnt += 1
        except Exception:
            err_cnt += 1

    showInfo(f"Translation Copy Builder\n\n作成: {ok_cnt}\nスキップ: {skip_cnt}\n失敗: {err_cnt}")


# ----------------------------
# Hook registration
# ----------------------------

def _setup_menus() -> None:
    # Tools menu (Reviewer-friendly)
    act = QAction("翻訳コピーカードを作成（現在のカード）", mw)
    act.triggered.connect(_copy_current_reviewer_card)
    mw.form.menuTools.addAction(act)

    # Settings
    act2 = QAction("Translation Copy Builder 設定…", mw)
    act2.triggered.connect(lambda: SettingsDialog(mw).exec())
    mw.form.menuTools.addAction(act2)


def _setup_browser_menu(browser: Browser) -> None:
    if not browser:
        return
    a = QAction("翻訳コピーカードを作成（選択ノート）", browser)
    a.triggered.connect(lambda: _copy_selected_browser_notes(browser))
    try:
        browser.form.menuEdit.addAction(a)
    except Exception:
        try:
            browser.form.menuTools.addAction(a)
        except Exception:
            pass


def _on_browser_menus_did_init(browser: Browser) -> None:
    _setup_browser_menu(browser)


def init() -> None:
    _setup_menus()
    gui_hooks.browser_menus_did_init.append(_on_browser_menus_did_init)


init()
