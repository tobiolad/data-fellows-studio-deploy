# Studio design system

[DESIGN.md](../../DESIGN.md) establishes the visual direction. The shell uses the system sans stack, a deep navy rail, the existing royal-blue action token and white business surfaces. Operational counts use tabular figures. An unavailable amount is written as unavailable. A zero requires a successful read.

## Navigation and task surfaces

- Use a single current-page link per active rail and include the workspace and page in the header. Use a real destination for a metric or a queue item. Derive the professional route set from the authenticated admission read.
- On narrow screens, place the Menu disclosure in the brand header. Expanded links have 44px minimum height and can wrap. Escape closes the disclosure and restores focus. A skip link moves focus into the main landmark.
- Use group labels in the admin rail. Keep form labels visible. Use one primary action per task and secondary buttons for cancellation and pagination.
- Use the 4px spacing scale. Collection rows use 16px padding, a 16px heading and 13px supporting text. Adjacent records share a dividing rule. On mobile, the title can occupy the full row.
- Collections retain search and sort during pagination. Show the visible record range. Empty-search results invite a different query. An empty collection explains what recorded work belongs there.
- Use native dialogs for focused creation and record inspection, with a visible close action, keyboard dismissal and focus restoration. Render user-supplied details as text.
- Distinguish submitted, under review, assessment, approved and revoked in words. Display verified payment states only from financial records. Keep internal IDs in details or underlying control values.

## Dashboard metric dictionary

| Workspace | Metric | Source and definition | Destination |
|---|---|---|---|
| Admin | Active engagements | Admin overview engagements in authorized or active state | CRM and engagements |
| Admin | Awaiting review | Deliverable versions under internal review | Quality review |
| Admin | Approved professionals | Professional admission records in approved state | Professional network |
| Admin | AI outputs awaiting review | Execution artifacts pending human review | AI operations |
| Professional | Active assignments / pending invitations | Own assignments filtered to accepted / invited | My assignments / Invitations |
| Client | Active / completed projects | Client overview projects by recorded status | Projects and engagements |
| Client | Deliverables to review / accepted | Client overview versions awaiting acceptance / accepted | Deliverables |

The recent admin audit snapshot is bounded by its read model. Its pagination and search cover returned events. A project deadline cannot be inferred from assignment access expiration.
