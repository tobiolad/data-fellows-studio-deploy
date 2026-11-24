# Reuse versus rebuild matrix

| Component | Source | Decision | Integration method | Gate |
|---|---|---|---|---|
| Onboarding progress language | `data-fellow-frontend` user onboarding steps | Adapt | Re-express in Studio HTML/CSS; keep backend contracts | UI/a11y tests |
| Skills/specialization selectors | `data-fellow-frontend` step-two/step-three | Adapt | New bounded profile API, no legacy IDs | Validate server-side |
| Education and experience forms | `data-fellow-frontend` step-four/step-five | Adapt | Structured entries in `professional_profiles` | PostgreSQL constraints/tests |
| Profile sections/tables | `data-fellow-frontend` profile components | Adapt | Current Studio design tokens and human-readable records | Playwright mobile |
| Company form fields | core web `company-form.tsx`, onboarding step-two | Adapt | Map to Studio organization fields; HubSpot reference remains external | Client authorization |
| CV parser/dropzone | core web `ImportCVForm.tsx`, `FileDropZone.tsx`, backend `cv-parser.ts` | Reject for now | Rebuild as quarantined evidence workflow later | scanner/private storage |
| Legacy auth/session | both legacy stacks | Reject | Entra validator already in Studio | tenant configuration |
| Match/messaging | core backend `message.ts`, Match model | Reject | Use project-scoped Studio messages | authorization tests |
| Milestones/payments | core backend `Milestone`, `Payment`, `Payout` | Reference concept | Studio project/milestone and verified financial contracts | Stripe/HubSpot approval |
| Active website CMS/layouts | `data-fellows-web-app` | Reference only | Preserve repository boundary; consume approved brand guidance | separate authorization |
| BizPilot handoff | BizPilot docs and versioned delivery intent | Adapt contract | authenticated, minimal handoff projection | receiver identity |

## Backlog

1. **This branch:** persistent editable professional profile and application linkage.
2. Admin profile/evidence review detail with reviewer notes and status history.
3. Client organization onboarding mapped to authorized Studio membership.
4. Private evidence upload/quarantine and scanner integration point.
5. Portal-level Entra test-tenant walkthrough with separate identities.
6. Profile completeness analytics and opportunity eligibility rules from verified records.

## Screenshot comparison status

Current Studio screenshots are stored in `artifacts/` (for example `professional-clean-dashboard-1440.png`). No legacy app screenshot is claimed: the archived apps were not safely bootstrapped in this audit environment. The first implementation PR will add current before/after profile screenshots from the real Studio server; a legacy visual capture can be added later when an isolated, dependency-complete legacy preview is approved.
