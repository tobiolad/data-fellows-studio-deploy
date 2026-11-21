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

## Review workflow

1. Use `$impeccable critique` or `$impeccable audit` on one surface at a time.
2. Apply `$unslop` only for a targeted refinement after the direction is explicit.
3. Run the local Playwright visual gate at 1440×900, 1024×768, 768×900 and 390×844.
4. Run the pinned Impeccable detector on changed markup and the rendered route.
5. Record any intentional exception in the PR, never by disabling the detector globally.
