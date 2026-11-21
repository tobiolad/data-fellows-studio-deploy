# Playwright smoke checks

Start the synthetic API and static frontend, then run:

```text
NODE_PATH=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules \
PLAYWRIGHT_CHROMIUM=/usr/bin/chromium \
node tests/playwright/ui-contract.js
```

The check intentionally verifies the project/package selector contract that previously caused a browser-side `TypeError`.

For the complete synthetic lifecycle with screenshots and a trace:

```text
NODE_PATH=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules \
PLAYWRIGHT_CHROMIUM=/usr/bin/chromium \
node tests/playwright/synthetic-lifecycle.js
```

The lifecycle creates synthetic organization, project, package, assignment and deliverable records, then exercises professional submission, independent review, client acceptance and project completion. It asserts that an unauthorized client review is rejected with HTTP 403 and that the browser reports no page errors or failed requests.

## Workspace and admission gates

The role controls require a loopback hostname and `?harness=synthetic`.
The walkthroughs include that query by default. Admission fixtures submit a
profile and use independent version-bound review before exercising staffing.
The complete local verification sequence and adapter-specific results are in
[the browser report](../../docs/quality/PLAYWRIGHT_RESULTS/README.md).
