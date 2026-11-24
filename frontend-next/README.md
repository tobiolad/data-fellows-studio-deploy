# Data Fellows Studio — frontend (next)

React + TypeScript + Tailwind + shadcn/ui rebuild of the Studio frontend,
replacing the vanilla JS/HTML app in `../frontend/`. Talks to the same
FastAPI backend (`../backend/`) — no API changes required.

## Why a separate app instead of editing `../frontend/` in place

So the existing, working frontend keeps running undisturbed while this one
is built out screen by screen. Once this reaches parity, `../frontend/`
should be retired — that's an explicit decision for the repo owner to make,
not something to do silently.

## Running locally

```
npm install
npm run dev
```

The dev server proxies `/api/*` to `http://localhost:8100` (see
`vite.config.ts`), so run the backend with `STUDIO_PERSISTENCE=postgres`
and `STUDIO_TEST_MODE=true` on port 8100 alongside this.

Sign-in is a synthetic role/actor picker (`src/pages/SignIn.tsx`) matching
the backend's `Bearer test:<actor>:<role>` test-mode scheme — the same
mechanism the old frontend used, just not styled like a leftover debug
panel. Swapping this for real Microsoft Entra sign-in is not done yet.

## What's built vs. placeholder

Real, wired to the backend: sign-in, Admin overview, Admin referral
program, Client overview, Professional overview, Professional profile
creation wizard (`src/pages/professional/ProfileWizard.tsx`), Reviewer
submission queue.

Everything else reachable from the sidebar renders `ComingSoonPage`
(`src/pages/ComingSoon.tsx`) rather than a broken or faked screen — the
honest state is "not rebuilt yet," not silently missing.

## Structure

- `src/lib/api.ts` — fetch wrapper, synthetic-session auth header.
- `src/lib/types.ts` — API response shapes.
- `src/components/layout/` — `AppShell` (sidebar + topbar) and per-role nav config.
- `src/components/ui/` — shadcn/ui primitives (Radix-based).
- `src/pages/<role>/` — one folder per portal.
