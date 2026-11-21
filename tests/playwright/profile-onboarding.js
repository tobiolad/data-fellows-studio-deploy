// Synthetic profile/onboarding verification. It never contacts a live identity provider.
const assert = require("assert");
const fs = require("fs");
const { chromium } = require("playwright");

const API = process.env.STUDIO_API_URL || "http://127.0.0.1:8100";
const FRONTEND = process.env.STUDIO_BROWSER_URL || "http://127.0.0.1:5173/index.html";
const CHROMIUM = process.env.PLAYWRIGHT_CHROMIUM || "/usr/bin/chromium";
const ARTIFACTS = process.env.STUDIO_ARTIFACT_DIR || "artifacts";

async function main() {
  fs.mkdirSync(ARTIFACTS, { recursive: true });
  const actor = `profile-browser-${Date.now()}`;
  const headers = { Authorization: `Bearer test:${actor}:professional`, "Content-Type": "application/json" };
  const application = await fetch(`${API}/api/professionals/${actor}/application`, { method: "POST", headers, body: "{}" });
  assert.strictEqual(application.status, 201, await application.text());
  const browser = await chromium.launch({ headless: true, executablePath: CHROMIUM, args: ["--no-sandbox"] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await context.addInitScript(({ baseApi, actor }) => { window.STUDIO_API_URL = baseApi; }, { baseApi: API, actor });
  const page = await context.newPage();
  const errors = []; const failures = [];
  page.on("response", async (response) => { if (response.url().includes("/profile") && response.request().method() === "PUT") console.log(`profile response ${response.status()} ${await response.text()}`); });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("requestfailed", (request) => failures.push(`${request.method()} ${request.url()}`));
  try {
    await page.goto(FRONTEND, { waitUntil: "networkidle" });
    await page.evaluate(({ actor }) => { const tools = document.querySelector("#developer-tools"); const select = document.querySelector("#role"); select.value = "professional"; select.dispatchEvent(new Event("change", { bubbles: true })); document.querySelector("#actor").value = actor; tools.open = true; }, { actor });
    await page.click("#refresh");
    await page.click('[data-view="profile"]');
    await page.waitForSelector("#professional-profile-form");
    await page.locator("#profile-display-name").fill("Synthetic profile reviewer");
    await page.locator("#profile-headline").fill("Operations automation specialist");
    await page.locator("#profile-skills").fill("Python, Data quality");
    await page.locator("#profile-specializations").fill("Operations analytics");
    await page.locator("#profile-availability").fill("Available for scoped work");
    await page.locator("#profile-bio").fill("I help teams turn reliable process evidence into maintainable automation.");
    await page.locator("#profile-experience").fill("Automation lead | Synthetic Co | 2022 | Present");
    await page.locator("#profile-education").fill("Synthetic University | BSc | Systems");
    await page.locator("#professional-profile-form button[type=submit]").click();
    await page.waitForFunction(() => document.querySelector("#profile-save-status")?.textContent.includes("Saved"));
    assert.match(await page.locator("#profile-completeness").innerText(), /complete/);
    assert.match(await page.locator("#profile-vetting-status").innerText(), /Pending/);
    await page.screenshot({ path: `${ARTIFACTS}/professional-profile-1440.png`, fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth <= 1));
    await page.screenshot({ path: `${ARTIFACTS}/professional-profile-390x844.png`, fullPage: true });
    assert.deepStrictEqual(errors, []); assert.deepStrictEqual(failures, []);
    console.log(JSON.stringify({ status: "passed", actor, profile: "saved_pending_review", errors, failures }));
  } finally { await browser.close(); }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
