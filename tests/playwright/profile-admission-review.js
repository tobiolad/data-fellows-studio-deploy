// Synthetic profile and admission review walkthrough. No live identity provider or files.
const assert = require("assert");
const fs = require("fs");
const { chromium } = require("playwright");

const API = process.env.STUDIO_API_URL || "http://127.0.0.1:8100";
const FRONTEND = process.env.STUDIO_BROWSER_URL || "http://127.0.0.1:5173/index.html?harness=synthetic#profile";
const CHROMIUM = process.env.PLAYWRIGHT_CHROMIUM || "/usr/bin/chromium";
const ARTIFACTS = process.env.STUDIO_ARTIFACT_DIR || "artifacts/profile-admission";
const jsonHeaders = (actor, role) => ({ Authorization: `Bearer test:${actor}:${role}`, "Content-Type": "application/json" });
async function api(path, options = {}) { const response = await fetch(`${API}${path}`, options); const body = await response.json().catch(() => ({})); assert.ok(response.ok, `${options.method || "GET"} ${path}: ${response.status} ${JSON.stringify(body)}`); return body; }
async function main() {
  fs.mkdirSync(ARTIFACTS, { recursive: true });
  const actor = `profile-admission-${Date.now()}`;
  const professionalHeaders = jsonHeaders(actor, "professional");
  await api(`/api/professionals/${actor}/application`, { method: "POST", headers: professionalHeaders, body: "{}" });
  const browser = await chromium.launch({ headless: true, executablePath: CHROMIUM, args: ["--no-sandbox"] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await context.addInitScript(({ baseApi }) => { window.STUDIO_API_URL = baseApi; }, { baseApi: API });
  const page = await context.newPage(); const errors = []; const failures = [];
  page.on("pageerror", (error) => errors.push(error.message)); page.on("requestfailed", (request) => failures.push(`${request.method()} ${request.url()}`));
  try {
    await page.goto(FRONTEND, { waitUntil: "networkidle" });
    await page.evaluate(({ actor }) => { const tools = document.querySelector("#developer-tools"); document.querySelector("#role").value = "professional"; document.querySelector("#role").dispatchEvent(new Event("change", { bubbles: true })); document.querySelector("#actor").value = actor; tools.open = true; }, { actor });
    await page.click("#refresh"); await page.click('[data-view="profile"]');
    await page.click("#edit-profile-button");
    await page.locator("#profile-display-name").fill("Synthetic profile reviewer"); await page.locator("#profile-headline").fill("Operations automation specialist"); await page.locator("#profile-skills").fill("Python"); await page.click("#add-profile-skill"); await page.locator("#profile-specializations").fill("Operations analytics"); await page.click("#add-profile-specialization"); await page.locator("#profile-availability").fill("Available for scoped work"); await page.locator("#profile-bio").fill("I help teams turn reliable process evidence into maintainable automation.");
    await page.click("#add-profile-experience"); const experience = page.locator("#profile-experience-entries .repeatable-row").last(); await experience.locator('input[data-entry-field="title"]').fill("Automation lead"); await experience.locator('input[data-entry-field="company"]').fill("Synthetic Co"); await experience.locator('input[data-entry-field="start"]').fill("2022"); await experience.locator('input[data-entry-field="end"]').fill("Present");
    await page.click("#add-profile-evidence");
    const evidence = page.locator("#profile-evidence-entries .repeatable-row").last();
    await evidence.locator('input[data-entry-field="label"]').fill("Work sample");
    await evidence.locator('input[data-entry-field="reference"]').fill("private://synthetic/work-sample");
    await page.click("#add-profile-education"); const education = page.locator("#profile-education-entries .repeatable-row").last(); await education.locator('input[data-entry-field="school"]').fill("Synthetic University"); await education.locator('input[data-entry-field="degree"]').fill("BSc"); await education.locator('input[data-entry-field="field"]').fill("Systems");
    await page.click("#add-profile-portfolio"); const portfolio = page.locator("#profile-portfolio-entries .repeatable-row").last(); await portfolio.locator('input[data-entry-field="title"]').fill("Inventory workflow"); await portfolio.locator('input[data-entry-field="url"]').fill("private://synthetic/inventory");
    await page.setViewportSize({ width: 390, height: 844 }); assert.ok(await page.locator("#profile-experience-entries .repeatable-row").count() > 0); await page.screenshot({ path: `${ARTIFACTS}/profile-edit-390x844.png`, fullPage: true }); await page.setViewportSize({ width: 1440, height: 900 });
    await page.click('#professional-profile-form button[type="submit"]'); await page.waitForFunction(() => document.querySelector("#profile-save-status")?.textContent.includes("Saved"));
    assert.match(await page.locator("#profile-completeness").innerText(), /complete/); await page.reload({ waitUntil: "networkidle" }); await page.evaluate(({ actor }) => { document.querySelector("#role").value = "professional"; document.querySelector("#role").dispatchEvent(new Event("change", { bubbles: true })); document.querySelector("#actor").value = actor; document.querySelector("#developer-tools").open = true; }, { actor }); await page.click("#refresh"); await page.click('[data-view="profile"]'); await page.waitForFunction(() => document.querySelector("#profile-summary-headline")?.textContent.includes("Operations automation"));
    await page.screenshot({ path: `${ARTIFACTS}/profile-view-1440.png`, fullPage: true }); await page.setViewportSize({ width: 390, height: 844 }); assert.ok(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth <= 1)); await page.screenshot({ path: `${ARTIFACTS}/profile-view-390x844.png`, fullPage: true });
    const unauthorized = await fetch(`${API}/api/professionals/${actor}/profile`, { headers: jsonHeaders("client-outsider", "client") }); assert.strictEqual(unauthorized.status, 403);
    await api(`/api/professionals/${actor}/review`, { method: "POST", headers: jsonHeaders("reviewer-1", "reviewer"), body: JSON.stringify({ status: "under_review", next_action: "Complete independent assessment" }) });
    await api(`/api/professionals/${actor}/review`, { method: "POST", headers: jsonHeaders("reviewer-1", "reviewer"), body: JSON.stringify({ status: "assessment", assessment_requests: [{ title: "Synthetic assessment", description: "Provide a short example" }], next_action: "Submit assessment" }) });
    await api(`/api/professionals/${actor}/review`, { method: "POST", headers: jsonHeaders("reviewer-1", "reviewer"), body: JSON.stringify({ status: "under_review", reason: "Assessment completed" }) });
    await page.setViewportSize({ width: 1440, height: 900 }); await page.evaluate(() => { document.querySelector("#role").value = "admin"; document.querySelector("#role").dispatchEvent(new Event("change", { bubbles: true })); document.querySelector("#developer-tools").open = true; }); await page.click("#refresh"); await page.click('[data-view="admin-applications"]'); await page.waitForSelector(".review-admission-button"); await page.locator(`.review-admission-button[data-professional-id="${actor}"]`).click(); await page.waitForSelector("#admission-review-status"); await page.check("#confirm-qualifications"); await page.locator('input[name="verified-evidence"]').first().check(); await page.selectOption("#admission-review-status", "approved"); await page.locator("#admission-review-reason").fill("Synthetic evidence reviewed independently."); await page.click('#admission-review-form button[type="submit"]'); await page.waitForFunction(() => document.querySelector("#admission-review-status-message")?.textContent.includes("saved")); await page.screenshot({ path: `${ARTIFACTS}/admin-admission-review-1440.png`, fullPage: true });
    console.log(JSON.stringify({ status: "passed", actor, profile: "saved_and_reloaded", review: "approved", unauthorized_profile_status: unauthorized.status, errors, failures }));
    assert.deepStrictEqual(errors, []); assert.deepStrictEqual(failures, []);
  } finally { await browser.close(); }
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
