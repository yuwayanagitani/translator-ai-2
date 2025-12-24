# translator-ai-2
This is an Anki add-on creating translated version of original cards.

## Features
- Duplicate selected notes into the Default deck and translate both Front and Back.
- API keys can be set via environment variables or the add-on config UI.
- Custom config dialog is available from **Tools → Add-ons → Config**.

## Configuration
Environment variables (optional):
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

Config fields (via add-on config):
- Provider (`openai` or `gemini`)
- API keys
- Models
- Source/target fields
- Source/target language
- Prompt

## Usage
1. Open the browser, select notes.
2. Use **Edit → AI Translate Selected Notes** to duplicate the notes into the Default deck with translated Front/Back.
3. Configure API keys and models via **Tools → Add-ons → Translator AI 2 → Config**.
