# Tabular Layout Speech

**Studio mode:** `TABULAR_LAYOUT_SPEECH`  
**Code:** `agents/tabular_layout_speech.py`  
**Collection:** Studio agents

## What it does

This mode turns supplied text into a structural outline intended for later accessible presentation. The local fallback looks for simple table markers, list markers, or paragraph-like text and returns a text description of the layout. If configured, an LLM may produce a more detailed outline.

## Inputs and outputs

- User-entered synthetic text in the Studio text area.
- A `SCHEDULED_HABIT` response status and a text description of detected structure in the local fallback.
- Optional LLM-generated text when the model integration is configured.

## FAQ

### Does this run OCR?

No. The text must already be supplied. The UI does not capture an image or extract document text.

### Does it speak the result aloud?

No. Despite the agent name, the current mode returns text. It does not synthesize speech or play an audio description.

### Can I enter document text by voice?

The Studio offers optional browser speech-to-text. It transcribes the user's speech into the text field; the browser's speech service may process audio outside this app. It does not read a document from a camera or speak the agent's result aloud.

### How does the local fallback detect a table?

It uses basic text markers such as `|`, `---`, or the word “columns”; dash or bullet prefixes are used to recognize simple lists.

## Boundaries

It does not guarantee correct table structure, read numeric values for accuracy, or integrate with a screen reader or wearable audio pipeline. Treat generated descriptions as unverified.
