# Pre-Op Waitlist

**Code:** `agents/preop_waitlist.py`  
**Collection:** Platform modules  
**Availability:** Code module only; not registered in the main API or selectable in Studio

## What it does

This experimental module is designed to turn supplied text into a structural description. Its local fallback recognizes simple comma-, tab-, or pipe-delimited tables and describes headers and rows; otherwise it describes a short sequence of text lines. An optional LLM path can produce a more detailed description when configured.

## FAQ

### Does it scan a document or run OCR?

No. It only receives text already supplied by a caller. The module does not capture an image or extract OCR.

### Does it speak the description?

No. The current implementation returns text, despite its “hands-free” product description. It does not synthesize speech or connect to a wearable.

### Can I select this in OcuGuard Studio?

No. The module is not included in the Studio's mode list or registered in the main REST API path.

### Is this specific to pre-surgery patients?

The name and prompt describe a pre-operative access scenario, but the code performs basic text-structure processing. It does not assess cataracts, corneal disease, wait times, or treatment needs.

## Boundaries

The module is an unintegrated experiment, not pre-operative support or medical advice. Its output is not validated for accuracy or patient use.
