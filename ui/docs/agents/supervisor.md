# Supervisor

**Code:** `agents/supervisor.py`  
**Collection:** Platform modules  
**Runtime:** Used by the REST request path; not a selectable Studio mode

## What it does

Supervisor is a request-processing component. It applies basic regular-expression substitutions to supplied text for email addresses, phone-like strings, and SSN-like strings, then routes a request based on the `network_drop` flag and client/user token values.

## FAQ

### Does it remove all personal information?

No. The implementation uses a few patterns and cannot detect every identifier, name, address, or sensitive value. Other fields, including user identifiers and tokens, are not made anonymous by those text substitutions.

### Does it provide authentication or regulatory compliance?

No. Its token comparison is a prototype routing check, not a complete identity, access-control, privacy, or compliance system.

### What is the local fallback?

The current router returns a `LOCAL_FALLBACK` route when a network-drop flag is present or the expected token fields are missing or do not match. Otherwise it returns `CLOUD_HYBRID`. This name does not guarantee cloud availability or a particular privacy posture.

## Boundaries

Do not use this component as a production PII scrubber, security boundary, consent mechanism, or proof of legal compliance. Production use requires a separate privacy and security design and verification.
