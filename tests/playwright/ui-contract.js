// Run with a Playwright-enabled Node runtime while the local Studio UI is running.
// Example: node tests/playwright/ui-contract.js
const assert = require("assert");
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.PLAYWRIGHT_CHROMIUM || undefined,
    args: ["--no-sandbox"],
  });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await page.goto(process.env.STUDIO_BROWSER_URL || "http://127.0.0.1:5173/index.html");
  assert.strictEqual(await page.locator("#project-id").count(), 1, "project id control must exist");
  assert.strictEqual(await page.locator("#package-project").count(), 0, "obsolete package-project control must not exist");
  await context.close();
  await browser.close();
  console.log("Studio UI contract passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
