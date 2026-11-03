# Store and developer-program readiness

> **Status: preparation checklist, not an official Meta submission checklist.** OcuGuard is a software prototype and is not ready for public distribution, a Meta wearable integration, or patient-facing use. Confirm current program terms, APIs, review rules, categories, and supported-device lists in the target developer portal before implementation or submission.

## Choose the distribution path first

Meta's [AI glasses developer overview](https://developers.meta.com/wearables/) describes different development paths, including extending a mobile app, a standalone web app, and connecting a service to Meta AI. Those paths are not interchangeable with publishing a Quest app to the Horizon Store. OcuGuard currently implements none of the Meta paths and has no Meta SDK, device connection, partnership, or approval.

Before creating a store package, record:

- Target product family and distribution path (AI glasses, Quest/Horizon Store, companion app, web app, or service).
- Current developer-program eligibility, preview/access status, supported model and OS matrix, SDK version, permissions, and applicable agreements, each with a date and official source.
- Whether a native companion app or separate client repository is required. Do not attempt to import a mobile SDK into the Python API.
- The exact user task, product claims, non-goals, and responsible product owner.

## Draft listing metadata

The configurable draft lives in `config/app.json` under `application.listing_draft`. It is a starting point only:

| Field | Current draft | Before submission |
|---|---|---|
| Name | OcuGuard | Confirm name availability and brand rules. |
| Category | Accessibility utility (hypothesis) | Select only from the actual target-store taxonomy; do not imply medical-device approval. |
| Short description | User-controlled access to user-entered instructions and schedules | Review for platform policies, accessibility accuracy, and permitted claims. |
| Privacy policy URL | Not provided | Publish and verify the actual privacy notice before collecting any real data. |
| Support URL | Not provided | Provide an operational support and issue-reporting route. |

## Readiness gates

### Product and platform

- [ ] One target platform, device/OS range, and official SDK release are confirmed.
- [ ] Developer enrollment, account ownership, agreements, app identifiers, signing, and permitted distribution are documented.
- [ ] App listing name, category, icon, screenshots, supported-device claims, support contact, and privacy link are complete and accurate.
- [ ] Reviewers can access a deterministic synthetic demo without a real patient account or real health information.

### Permissions and privacy

- [ ] Every camera, microphone, location, Bluetooth, or other permission has a documented feature need, user-visible rationale, and denial/revocation behavior.
- [ ] Collection, processing location, external providers, retention, deletion, analytics, crash reports, and access controls are disclosed.
- [ ] Production identity and per-user authorization replace the current caller-supplied demo `user_id` and optional shared API key.
- [ ] Persistent data is protected with an approved storage and key-management design; the current local SQLite store is unencrypted and development-only.
- [ ] Data-flow, threat-model, privacy, and incident-response reviews are approved for the exact release scope.

### Safety, accessibility, and quality

- [ ] Care-related content is presented as user-supplied; the app does not generate, interpret, or change clinical instructions.
- [ ] No health, emergency, adherence, or efficacy claims are made without the necessary qualified review and evidence.
- [ ] Setup, permissions, pause/stop, failure states, text readability, audio behavior, and assistive-technology paths are tested with the intended audience.
- [ ] Automated tests cover normal operation, invalid input, limits, stale/offline states, deletion, and revocation where applicable.
- [ ] A device/OS/SDK compatibility matrix and release-specific known-limitations list are included in reviewer materials.

## Current gaps

- The device-session adapter is synthetic and process-local; it cannot connect to glasses or deliver output to them.
- Reminders are evaluated when the UI/API is used; there is no background notification service or delivery guarantee.
- Browser read-aloud uses the browser speech engine, not glasses audio, and is not a verified accessibility feature.
- The local SQLite database is unencrypted. Demo IDs are caller/session scoped and are not authenticated identities.
- A production environment intentionally fails closed. Public deployment must remain blocked until production security, privacy, operational, and product gates are satisfied.
