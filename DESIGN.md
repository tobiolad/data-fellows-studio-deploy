# Data Fellows Studio Design System

## Surface

Studio is an internal managed-delivery application. The Admin Mission Control surface is an
Operate interface: scanability, trustworthy status, keyboard access and low cognitive load take
priority over decorative effects. Professional and Client portals share the same tokens and
interaction vocabulary.

## Direction

- **Product:** Data Fellows coordinates accountable client delivery across people, software and
  bounded AI execution.
- **Character:** exact, calm, accountable.
- **World:** an operations room: ink, paper, quiet blue signal lights and clear audit trails.
- **Moments:** delivery-stage movement and the one action that needs a decision now.
- **Signature:** a blue status signal that always names the responsible queue or owner.

## Tokens and rules

- Use the CSS variables in `frontend/styles.css`; do not introduce one-off colours or shadows.
- Use the 4px spacing grid. Page gutters are 24–32px; panels use 16–20px; compact controls use
  8–12px.
- Keep one neutral surface ramp, one royal-blue action accent and toned semantic status colours.
- Body and functional text must remain at least 12px unless it is visually hidden. Secondary text
  must meet WCAG AA contrast on its actual surface.
- Every interactive control has hover, focus-visible, active, disabled and error states.
- Tables are scrollable on narrow screens; card grids collapse to one column below 680px.
- Status counts must be computed from the same records shown in the queue. Never invent business
  metrics or placeholder financial values.
- Admin detail actions are progressive disclosure: show a concise list first, then a human-readable
  drawer or detail route. UUIDs stay in API payloads, not in navigation controls.
- Motion is limited to 150–250ms state feedback and respects `prefers-reduced-motion`.

## Colors

- `--df-bg` is the cool application background; `--df-surface` is the raised panel; `--df-line`
  is the quiet border.
- `--df-ink` is primary text, `--df-ink-secondary` is readable supporting text and
  `--df-ink-muted` is reserved for non-essential metadata.
- `--df-blue` and `--df-blue-strong` are the only action/selection accents. Green, amber and red
  are semantic state colors only.
- Text on every status surface must meet WCAG AA. Do not use blue or gray text on a tinted surface
  unless the contrast is checked at the actual rendered size.

## Typography

- Use the existing system sans stack for the product UI; typography should feel familiar and
  quiet in dense operational screens.
- Headings use a compact stepped scale: page title, section title, card title, body, metadata.
- Body and functional text are at least 12px. Labels are sentence case, never decorative tracked
  capitals. Numeric metrics use tabular alignment where available.
- Keep line length readable in explanations and use `overflow-wrap: break-word` for user-provided
  names, project titles and evidence labels.

## Components

- **Navigation:** persistent desktop sidebar and a keyboard-operable mobile Menu disclosure. Active
  links expose the current page. See [shared workspace rules](docs/quality/STUDIO_DESIGN_SYSTEM.md).
- **Panels and cards:** one surface per information group, 12px radius, quiet border, no nested
  decorative cards. Cards expose a concise summary and progressive detail action.
- **Buttons:** royal blue for the one primary action, outlined secondary actions, and disabled
  states that remain legible. Every action reports success or failure in the live status region.
- **Tables:** readable headings, sortable/filterable controls, human labels, and horizontal
  scrolling on narrow screens with no data loss.
- **Status indicators:** text plus color; status words remain visible to color-blind users.
- **Empty/loading/error states:** explain what is unavailable, why, and the next authorized action.
- **Dialogs/drawers:** keyboard closable, focus-visible, and used only for progressive detail or
  consequential confirmation.

## Review workflow

1. Use `$impeccable critique` or `$impeccable audit` on one surface at a time.
2. Apply `$unslop` only for a targeted refinement after the direction is explicit.
3. Run the local Playwright visual gate at 1440×900, 1024×768, 768×900 and 390×844.
4. Run the pinned Impeccable detector on changed markup and the rendered route.
5. Record any intentional exception in the PR, never by disabling the detector globally.
