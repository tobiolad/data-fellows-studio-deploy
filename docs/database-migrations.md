# Studio database migrations

Migrations live in `migrations/` and are applied lexically inside one transaction. The repository records applied versions and SHA-256 checksums in `studio_schema_migrations`; rerunning a completed migration is a no-op, while a changed applied file fails closed.

Production rules:

- Run migrations from a reviewed, approval-controlled job before application rollout.
- Use a dedicated Studio database; never point these migrations at BizPilot or another product database.
- Set `STUDIO_PERSISTENCE=postgres` only after migrations succeed; unsupported domain endpoints fail closed with `501` until their repository methods are implemented.
- Use a least-privilege migration identity for schema changes and a separate runtime identity for ordinary reads/writes.
- Never run migrations against a live client database from a pull request.
- Take and verify a backup before destructive or irreversible changes.
- Add immutable successor columns/rows for domain history rather than overwriting approved artifacts.
- Never edit an applied migration; add a new file so checksum verification and rollback review remain meaningful.
- Set `STUDIO_TEST_DATABASE_URL` only in a protected synthetic test environment.
## 007 professional profiles

`007_professional_profiles.sql` adds a profile draft keyed to an existing admission. JSON arrays hold bounded, structured education, experience and portfolio references; `version` and `updated_at` support optimistic edits. The admission row remains the source of vetting status and is never changed by profile writes. Apply migrations lexically with the existing checksum-verified runner.

## 008 professional admission review

`008_professional_admission_review.sql` extends admission records with the explicit
`submitted`, `under_review`, `assessment`, `approved`, `declined` and `revoked`
states, review reasons, missing-information items, assessment requests, next
actions and evidence-reference metadata. Legacy `pending` and `rejected` values
remain accepted for compatibility with older synthetic records. It also adds
metadata-only evidence references to profiles. References must use a private,
quarantine or pending storage scheme; this migration does not create a public
upload path or accept file bytes.
