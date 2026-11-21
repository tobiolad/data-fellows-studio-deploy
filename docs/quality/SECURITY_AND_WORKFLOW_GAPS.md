# Security and workflow gaps

| Finding | Disposition | Evidence and residual risk |
|---|---|---|
| Legacy approval and decision handlers could create approval without an application or rationale | Implemented and tested | Both routes now return 410 for authorized admins and 403 for unauthorized callers. Removed direct approval writers. Both storage adapters test denied writes and unchanged application state. |
| Canonical approval accepted an unevidenced reviewed profile | Implemented and tested for synthetic admission | Require review or assessment state, no outstanding requests, independent reviewer, a skill, a labeled private reference, matching profile version and written rationale. PostgreSQL checks with row locks inside the decision transaction. |
| Real credential and document authenticity | Blocked | A private reference is metadata. Role-specific qualification criteria, credential verification, private storage, quarantine, scanning and retention require owner-approved controls. |
| Synthetic credentials in staging | Implemented and tested | Staging and production reject the synthetic adapter on protected requests, including when configured accidentally. |
| Role and organization isolation | Implemented but not fully validated | API and lifecycle tests exercise cross-organization reads, revoked memberships, denied professional access, independent review and client acceptance. Real identity revocation and directory assignment still require live validation. |
| Profile identity switching and stale optimistic versions | Implemented and tested for the profile walkthrough | Empty profiles clear prior version state. The reviewer attestation identifies the version examined. Browser identity switching is confined to a loopback harness. |
| Application can be submitted again | In development | Submission currently restarts review state. A production transition policy must preserve decision history, enforce resubmission eligibility and bind assessments to their resolution. |
| Qualification history and specialized roles | In development | An admission decision records a reviewer and reason. Formal policy versions, enrollment in specialized review queues, immutable evidence attestation and historical profile snapshots are outstanding. |
| Scope-specific access after general professional revocation | Implemented but not fully validated | Admission and organization membership are distinct. A complete revocation matrix for existing assignments, in-flight runs and cached browser states remains a release gate. |
| Audit history and finance | In development | Search covers recent admin events. Database-level audit tamper resistance, retention, monitored exports, verified invoice and compensation ingestion need operational validation. |
