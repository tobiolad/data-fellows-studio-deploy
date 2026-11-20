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
