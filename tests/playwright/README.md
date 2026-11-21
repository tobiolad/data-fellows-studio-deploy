# Playwright smoke checks

Start the synthetic API and static frontend, then run:

```text
NODE_PATH=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules \
PLAYWRIGHT_CHROMIUM=/usr/bin/chromium \
node tests/playwright/ui-contract.js
```

The check intentionally verifies the project/package selector contract that previously caused a browser-side `TypeError`.
