from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict


def _post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def translate_openai(
    text: str,
    api_key: str,
    model: str,
    prompt: str,
    source_language: str,
    target_language: str,
) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    system_prompt = (
        f"{prompt}\n\nSource language: {source_language}\n"
        f"Target language: {target_language}"
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = _post_json(url, payload, headers)
    return data["choices"][0]["message"]["content"].strip()


def translate_gemini(
    text: str,
    api_key: str,
    model: str,
    prompt: str,
    source_language: str,
    target_language: str,
) -> str:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    full_prompt = (
        f"{prompt}\n\nSource language: {source_language}\n"
        f"Target language: {target_language}\n\n{text}"
    )
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }
    headers = {"Content-Type": "application/json"}
    data = _post_json(url, payload, headers)
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
