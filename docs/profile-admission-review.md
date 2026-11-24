# Professional profile and admission review

This increment builds on PR #44 without replacing its profile APIs. The profile
workspace now has a read-only summary and an explicit edit mode. Experience,
education, portfolio and evidence metadata use repeatable structured rows; skills
and specializations use bounded tag controls. Profile writes continue to use the
existing optimistic `version` field and emit `professional_profile.updated`.

Admission is a separate review record. New submissions use `submitted`, then an
authorized admin or reviewer may move the application through `under_review` and
`assessment` before a reasoned `approved`, `declined` or `revoked` decision. A
complete profile does not change admission or grant assignment access.

## Evidence boundary

The current API accepts metadata-only references with `private://`,
`quarantine://` or `pending://` schemes. Public HTTP URLs are rejected. No file
bytes are uploaded or downloaded by this increment. Real evidence remains blocked
until private storage, upload quarantine, malware scanning, retention and audit
controls are validated in staging.

## Verification

- In-memory backend suite: 32 passed.
- PostgreSQL suite: 8 passed against an isolated PostgreSQL 16 database created
  for the test run; migrations 001–008, structured profile persistence, version
  conflicts, reviewer state and audit history were exercised.
- Synthetic Playwright profile/admission walkthrough: passed with desktop and
  mobile screenshots, save/reload, structured fields, reviewer approval and a
  403 cross-role profile access check. No page errors or failed requests.
- Impeccable detector still reports legacy contrast and small-text findings across
  the larger static shell; none were suppressed. `impeccable doctor` reports only
  the non-blocking DESIGN.md size guidance.

## Remaining gates

Microsoft Entra authentication, independent real staff identities, private object
storage and scanner-backed evidence, production database credentials, and
authenticated browser testing remain external staging requirements.
