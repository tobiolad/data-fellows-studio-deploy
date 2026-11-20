# Studio identity and access matrix

| Actor | Organization | Project | AI execution | Deliverables | Acceptance |
|---|---|---|---|---|---|
| Internal admin | Create/manage | Create/manage | Request and approve independently | Review/manage | Govern completion |
| Internal reviewer | Assigned organization | Review only | Approve independent artifacts | Approve/revision request | No client acceptance |
| Client | Own organization | Read progress | None | Read approved versions | Accept approved versions |
| Approved professional | Admitted organization | Assignment scope | No arbitrary runs | Submit assigned work | None |
| Applicant | None | None | None | None | None |
| AI service identity | Explicit work package only | Bounded policy | Execute allowed tool | Produce artifact | Never approve itself |

Every API route re-derives organization/project scope from the stored relationship. Caller-supplied organization IDs never grant access.

Organization owners can revoke a membership role through the server-side endpoint. Revocation removes the role before subsequent authorization checks and is audited; the final organization owner cannot be removed.

Professional admission is a separate administrative decision. A professional may submit or resubmit their own application, but only an internal administrator can approve or reject it. The compatibility approval endpoint enforces the same server-side rule, and application/decision events are written to the audit stream without granting project access. Admission approval alone is insufficient: the professional must also hold an active organization membership and accept a project-specific assignment before delivery data is accessible.

Audit reads are organization-scoped for reviewers. Only administrators can view the complete internal audit stream.
