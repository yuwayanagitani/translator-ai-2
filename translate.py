from __future__ import annotations

from typing import Dict, Any

from aqt import mw

from .providers import translate_openai, translate_gemini
from .config import get_api_key

IMAGE_TAG_INSTRUCTION = (
    "Do not translate or move any <img> tags; keep them exactly as-is and in place."
)


def translate_text(text: str, config: Dict[str, Any]) -> str:
    provider = config.get("provider", "openai")
    api_key = get_api_key(provider, config)
    if not api_key:
        raise ValueError(f"Missing API key for provider: {provider}")

    base_prompt = config.get("prompt", "Translate the following text.")
    prompt = f"{base_prompt}\n\n{IMAGE_TAG_INSTRUCTION}"
    source_language = config.get("source_language", "")
    target_language = config.get("target_language", "")

    if provider == "openai":
        model = config.get("openai_model", "gpt-4o-mini")
        return translate_openai(
            text=text,
            api_key=api_key,
            model=model,
            prompt=prompt,
            source_language=source_language,
            target_language=target_language,
        )
    if provider == "gemini":
        model = config.get("gemini_model", "gemini-1.5-flash")
        return translate_gemini(
            text=text,
            api_key=api_key,
            model=model,
            prompt=prompt,
            source_language=source_language,
            target_language=target_language,
        )

    raise ValueError(f"Unsupported provider: {provider}")


def translate_note_fields(note: Any, config: Dict[str, Any]) -> bool:
    source_field = config.get("source_field", "Front")
    target_field = config.get("target_field", "Back")
    if source_field not in note:
        raise KeyError(f"Source field not found: {source_field}")
    if target_field not in note:
        raise KeyError(f"Target field not found: {target_field}")

    source_text = note[source_field].strip()
    target_text = note[target_field].strip()
    if not source_text and not target_text:
        return False

    new_note = mw.col.new_note(note.note_type())
    for field_name in note.keys():
        new_note[field_name] = note[field_name]

    if source_text:
        new_note[source_field] = translate_text(source_text, config)
    if target_text:
        new_note[target_field] = translate_text(target_text, config)

    default_deck_id = mw.col.decks.id("Default")
    mw.col.add_note(new_note, default_deck_id)
    return True
