// Set STUDIO_BROWSER_URL to the served parent frontend and STUDIO_BASELINE=1 for comparison.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

async function main() {
  const base = process.env.STUDIO_BROWSER_URL || "http://127.0.0.1:5173/index.html?harness=synthetic";
  const api = process.env.STUDIO_API_URL || "http://127.0.0.1:8100";
  const baseline = process.env.STUDIO_BASELINE === "1";
  const artifacts = process.env.STUDIO_ARTIFACT_DIR || "artifacts/navigation";
  fs.mkdirSync(artifacts, { recursive: true });
  const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM || "/usr/bin/chromium", args: ["--no-sandbox"] });
  let layouts = 0;
  const issues = [];
  const responses = new Map();
  const consoleErrors = new Set();
  try {
    for (const identity of ["professional", "applicant", "admin", "client", "reviewer"]) {
      const page = await browser.newPage();
      page.on("console", message => {
        if (message.type() === "error") consoleErrors.add(message.text());
      });
      page.on("response", response => {
        if (response.status() < 400) return;
        const key = response.status() + " " + new URL(response.url()).pathname;
        responses.set(key, (responses.get(key) || 0) + 1);
      });
      page.on("pageerror", error => issues.push(error.message));
      page.on("requestfailed", req => issues.push(req.url()));
      await page.addInitScript(api => window.STUDIO_API_URL = api, api);
      await page.goto(base, {waitUntil: "networkidle"});
      await page.evaluate(identity => {
        const role = document.querySelector("#role");
        role.value = identity === "applicant" ? "professional" : identity;
        role.dispatchEvent(new Event("change"));
        if (identity === "applicant") document.querySelector("#actor").value = "navigation-applicant";
        document.querySelector("#refresh").click();
        document.querySelector("#developer-tools").open = false;
      }, identity);
      await page.waitForLoadState("networkidle");
      let views = await page.locator(".nav-list:not([hidden]) a:not([hidden])").evaluateAll(links => links.map(link => link.dataset.view));
      if (baseline && identity === "reviewer") views = ["reviews"];
      if (baseline && identity === "applicant") views = ["applications", "profile", "help"];
      if (!baseline && identity === "applicant") assert.deepEqual(views, ["applications", "profile", "help"]);
      if (!baseline && identity === "reviewer") assert.deepEqual(views, ["reviews"]);
      for (const width of [1440, 1024, 768, 390, 320]) {
        await page.setViewportSize({width, height: width < 400 ? 844 : 900});
        for (const view of views) {
          if (!baseline && width < 400) {
            await page.click("#mobile-menu");
            assert.equal(await page.locator("#mobile-menu").getAttribute("aria-expanded"), "true");
            await page.locator('.nav-list:not([hidden]) a[data-view="' + view + '"]').click();
          } else {
            await page.evaluate(view => location.hash = view, view);
          }
          await page.waitForSelector("#" + view + "-view.active-view");
          await page.waitForLoadState("networkidle");
          if (!baseline) {
            assert.equal(await page.locator('.nav-list a[aria-current="page"]').getAttribute("data-view"), view);
            assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true, identity + " " + view + " at " + width);
          }
          await page.evaluate(() => window.scrollTo(0, 0));
          if (width === 1440 || (width !== 320 && (view === views[0] || (width === 390 && ["profile", "admin-applications", "admin-engagements", "admin-audit"].includes(view))))) {
            await page.screenshot({path: path.join(artifacts, identity + "-" + view + "-" + width + ".png")});
          }
          layouts++;
        }
      }
      if (!baseline) {
        await page.click("#mobile-menu");
        await page.keyboard.press("Escape");
        assert.equal(await page.locator("#mobile-menu").getAttribute("aria-expanded"), "false");
        assert.equal(await page.evaluate(() => document.activeElement.id), "mobile-menu");
      }
      await page.close();
    }
    assert.deepEqual(issues, []);
    console.log(JSON.stringify({layouts, pageErrorsAndFailedRequests: issues, httpErrors: Object.fromEntries(responses), consoleErrors: [...consoleErrors], baseline: Boolean(baseline)}));
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
