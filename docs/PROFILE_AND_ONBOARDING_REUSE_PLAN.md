# Profile and onboarding reuse plan

## Decision

Adapt the verified legacy eight-step information architecture, but implement it with Studio persistence, Entra-ready identity and explicit admission decisions. A completed profile is evidence for review; it is never an approval signal.

## Target lifecycle

1. Apply to join Data Fellows (creates `professional_admissions` with `pending`).
2. Complete profile draft (identity/headline, bio, skills and specializations).
3. Add evidence (education, work history, portfolio references; future private uploads are quarantined).
4. Submit profile for review (audit event; no privilege change).
5. Authorized admin records vetting decision: under review, assessment, approved, declined, or revoked.
6. Approved professionals see only sanitized eligible opportunities.
7. Selection creates an invitation with terms and expiry.
8. Accepted invitation activates scoped assignment access.

## Safe reuse mapping

| Legacy step | Studio adaptation | Reason |
|---|---|---|
| Intro | Keep concise progress orientation and “save and finish later” language | Good onboarding affordance; remove marketplace promises |
| Role/speciality | Store controlled specializations, with free-text notes bounded | Preserves verified vocabulary without fabricated matching |
| Skills | Multi-select with search and explicit “self-reported” label | Skills do not grant access |
| Work experience | Structured repeatable entries | Reproducible and reviewable; no external CV call |
| Education | Structured repeatable entries | Reviewable evidence |
| Bio | Editable narrative with length and content checks | Human-authored context |
| Personal details | Minimize to contact/availability required for delivery | Avoid unnecessary sensitive data |
| Completion | Show profile completeness and pending review separately | Prevents auto-approval |

## First implementation increment

The focused branch adds a `professional_profiles` table and own/admin API. It stores bounded JSON arrays for education, experience and portfolio references, uses optimistic `updated_at` timestamps, emits audit events, and intentionally does not alter admission status. The existing synthetic identity adapter and PostgreSQL repository remain separate.

## Deferred evidence upload

Legacy `ImportCVForm.tsx` posts a file directly to Affinda with a browser-exposed key and the backend uploads public S3 URLs. That is not reused. A future evidence slice must use private storage, quarantine, MIME/size/hash checks, scanner status and reviewer approval before exposing metadata.
