// Synthetic Mission Control walkthrough. Requires the local API and static frontend.
const assert = require("assert");
const fs = require("fs");
const { chromium } = require("playwright");

const API = process.env.STUDIO_API_URL || "http://127.0.0.1:8100";
const FRONTEND = process.env.STUDIO_BROWSER_URL || "http://127.0.0.1:5173/index.html";
const CHROMIUM = process.env.PLAYWRIGHT_CHROMIUM || "/usr/bin/chromium";
const ARTIFACTS = process.env.STUDIO_ARTIFACT_DIR || "artifacts";

async function main() {
  fs.mkdirSync(ARTIFACTS, { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: CHROMIUM, args: ["--no-sandbox"] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await context.addInitScript((api) => { window.STUDIO_API_URL = api; }, API);
  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });
  const page = await context.newPage();
  const pageErrors = [];
  const failedRequests = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => failedRequests.push(`${request.method()} ${request.url()}`));

  try {
    await page.goto(FRONTEND, { waitUntil: "networkidle" });
    await page.evaluate(() => { const select = document.querySelector("#role"); select.value = "admin"; select.dispatchEvent(new Event("change", { bubbles: true })); });
    await page.waitForSelector("#admin-overview-view.active-view");
    await page.waitForSelector("#admin-metric-grid .metric-card");
    await page.evaluate(() => { document.querySelector("#developer-tools").open = false; });
    await page.screenshot({ path: `${ARTIFACTS}/admin-mission-control-1440.png`, fullPage: true });
    for (const width of [1024, 768]) {
      await page.setViewportSize({ width, height: 900 });
      await page.screenshot({ path: `${ARTIFACTS}/admin-mission-control-${width}.png`, fullPage: true });
    }
    await page.setViewportSize({ width: 1440, height: 900 });

    for (const [view, artifact] of [["admin-engagements", "admin-engagements-1440"], ["admin-projects", "admin-projects-1440"], ["admin-applications", "admin-vetting-1440"], ["admin-ai", "admin-ai-operations-1440"], ["admin-quality", "admin-quality-review-1440"], ["admin-audit", "admin-audit-1440"]]) {
      await page.click(`[data-view="${view}"]`);
      await page.waitForSelector(`#${view}-view.active-view`);
      await page.screenshot({ path: `${ARTIFACTS}/${artifact}.png`, fullPage: true });
    }

    await page.click('[data-view="admin-projects"]');
    await page.fill("#admin-project-search", "Synthetic");
    await page.selectOption("#admin-project-status", "completed");
    await page.selectOption("#admin-project-sort", "name");
    assert.ok((await page.locator("#admin-project-list .admin-card").count()) > 0);
    await page.locator("#admin-project-list .admin-detail-button").first().click();
    await page.waitForSelector("#admin-detail-drawer:not([hidden])");
    assert.match(await page.locator("#admin-drawer-content").innerText(), /PROJECT DETAIL/);
    await page.click("#admin-drawer-close");

    await page.click('[data-view="admin-overview"]');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForSelector("#admin-overview-view.active-view");
    await page.screenshot({ path: `${ARTIFACTS}/admin-mission-control-390x844.png`, fullPage: true });
    await page.evaluate(() => document.querySelector("#admin-new-engagement").focus({ focusVisible: true }));
    const focusStyle = await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle);
    const horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    assert.notStrictEqual(focusStyle, "none");
    assert.ok(horizontalOverflow <= 1, `unexpected document overflow: ${horizontalOverflow}px`);

    const unauthorized = await page.evaluate(async (api) => {
      const response = await fetch(`${api}/api/admin/overview`, { headers: { Authorization: "Bearer test:professional-1:professional" } });
      return response.status;
    }, API);
    assert.strictEqual(unauthorized, 403);
    assert.deepStrictEqual(pageErrors, []);
    assert.deepStrictEqual(failedRequests, []);
    console.log(JSON.stringify({ status: "passed", unauthorizedAdminOverview: unauthorized, pageErrors, failedRequests }));
  } finally {
    await context.tracing.stop({ path: `${ARTIFACTS}/admin-mission-control-trace.zip` });
    await browser.close();
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
