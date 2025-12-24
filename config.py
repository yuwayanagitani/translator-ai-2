from __future__ import annotations

import os
from typing import Any, Dict

from aqt import mw
from aqt.qt import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QWidget,
)

ADDON_NAME = __name__.split(".")[0]


def load_config() -> Dict[str, Any]:
    return mw.addonManager.getConfig(ADDON_NAME)


def save_config(config: Dict[str, Any]) -> None:
    mw.addonManager.writeConfig(ADDON_NAME, config)


def get_api_key(provider: str, config: Dict[str, Any]) -> str | None:
    if provider == "openai":
        return config.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
    if provider == "gemini":
        return config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
    return None


class ConfigDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Translator AI Settings")

        self.config = load_config()

        layout = QFormLayout(self)

        self.provider_combo = QComboBox(self)
        self.provider_combo.addItems(["openai", "gemini"])
        self.provider_combo.setCurrentText(self.config.get("provider", "openai"))
        layout.addRow("Provider", self.provider_combo)

        self.openai_key_input = QLineEdit(self)
        self.openai_key_input.setText(self.config.get("openai_api_key", ""))
        self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("OpenAI API Key", self.openai_key_input)

        self.gemini_key_input = QLineEdit(self)
        self.gemini_key_input.setText(self.config.get("gemini_api_key", ""))
        self.gemini_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Gemini API Key", self.gemini_key_input)

        self.openai_model_input = QLineEdit(self)
        self.openai_model_input.setText(self.config.get("openai_model", "gpt-4o-mini"))
        layout.addRow("OpenAI Model", self.openai_model_input)

        self.gemini_model_input = QLineEdit(self)
        self.gemini_model_input.setText(
            self.config.get("gemini_model", "gemini-1.5-flash")
        )
        layout.addRow("Gemini Model", self.gemini_model_input)

        self.source_field_input = QLineEdit(self)
        self.source_field_input.setText(self.config.get("source_field", "Front"))
        layout.addRow("Question Field", self.source_field_input)

        self.target_field_input = QLineEdit(self)
        self.target_field_input.setText(self.config.get("target_field", "Back"))
        layout.addRow("Answer Field", self.target_field_input)

        self.source_language_input = QLineEdit(self)
        self.source_language_input.setText(
            self.config.get("source_language", "Japanese")
        )
        layout.addRow("Source Language", self.source_language_input)

        self.target_language_input = QLineEdit(self)
        self.target_language_input.setText(
            self.config.get("target_language", "English")
        )
        layout.addRow("Target Language", self.target_language_input)

        self.prompt_input = QTextEdit(self)
        self.prompt_input.setPlainText(
            self.config.get(
                "prompt", "Translate the following text. Return only the translated text."
            )
        )
        layout.addRow("Prompt", self.prompt_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept(self) -> None:
        self.config["provider"] = self.provider_combo.currentText()
        self.config["openai_api_key"] = self.openai_key_input.text().strip()
        self.config["gemini_api_key"] = self.gemini_key_input.text().strip()
        self.config["openai_model"] = self.openai_model_input.text().strip()
        self.config["gemini_model"] = self.gemini_model_input.text().strip()
        self.config["source_field"] = self.source_field_input.text().strip()
        self.config["target_field"] = self.target_field_input.text().strip()
        self.config["source_language"] = self.source_language_input.text().strip()
        self.config["target_language"] = self.target_language_input.text().strip()
        self.config["prompt"] = self.prompt_input.toPlainText().strip()

        save_config(self.config)
        super().accept()


def show_config_dialog(parent: QWidget | None = None) -> None:
    dialog = ConfigDialog(parent)
    dialog.exec()
