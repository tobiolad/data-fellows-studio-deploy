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

    for (const [view, artifact] of [["admin-engagements", "admin-engagements-1440"], ["admin-projects", "admin-projects-1440"], ["admin-applications", "admin-vetting-1440"], ["admin-ai", "admin-ai-operations-1440"], ["admin-quality", "admin-quality-review-1440"], ["admin-audit", "admin-audit-1440"]]) {
      await page.click(`[data-view="${view}"]`);
      await page.waitForSelector(`#${view}-view.active-view`);
      await page.screenshot({ path: `${ARTIFACTS}/${artifact}.png`, fullPage: true });
    }

    await page.click('[data-view="admin-overview"]');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForSelector("#admin-overview-view.active-view");
    await page.screenshot({ path: `${ARTIFACTS}/admin-mission-control-390x844.png`, fullPage: true });

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
