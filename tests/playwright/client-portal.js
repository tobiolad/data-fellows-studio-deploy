const { admitProfessional } = require("./admission-fixture");
// Client-safe portal walkthrough against synthetic PostgreSQL records.
const assert = require("assert");
const fs = require("fs");
const { chromium } = require("playwright");

const API = process.env.STUDIO_API_URL || "http://127.0.0.1:8100";
const FRONTEND = process.env.STUDIO_BROWSER_URL || "http://127.0.0.1:5173/index.html?harness=synthetic";
const CHROMIUM = process.env.PLAYWRIGHT_CHROMIUM || "/usr/bin/chromium";
const ARTIFACTS = process.env.STUDIO_ARTIFACT_DIR || "artifacts";

async function main() {
  fs.mkdirSync(ARTIFACTS, { recursive: true });
  const api = async (actor, role, path, options = {}) => {
    const response = await fetch(`${API}${path}`, { ...options, headers: { Authorization: `Bearer test:${actor}:${role}`, "Content-Type": "application/json", ...(options.headers || {}) } });
    return { status: response.status, body: await response.json().catch(() => ({})) };
  };
  const post = async (actor, role, path, body) => {
    const response = await api(actor, role, path, { method: "POST", body: JSON.stringify(body) });
    assert.ok(response.status >= 200 && response.status < 300, `${path}: ${response.status} ${JSON.stringify(response.body)}`);
    return response.body;
  };
  const suffix = Date.now().toString();
  const clientId = `client-portal-${suffix}`;
  const professionalId = `professional-portal-${suffix}`;
  const reviewerId = `reviewer-portal-${suffix}`;
  const organization = await post("admin-1", "admin", "/api/organizations", { name: `Client Portal ${suffix}` });
  for (const [actor, role] of [[clientId, "client"], [professionalId, "professional"], [reviewerId, "reviewer"]]) await post("admin-1", "admin", `/api/organizations/${organization.id}/members`, { actor_id: actor, role });
  await admitProfessional(api, professionalId);
  const engagement = await post("admin-1", "admin", "/api/engagements", { organization_id: organization.id, name: "Authorized client engagement", objective: "Validate a client-safe delivery workspace" });
  const project = await post("admin-1", "admin", "/api/projects", { engagement_id: engagement.id, name: "Client delivery project" });
  const pack = await post("admin-1", "admin", "/api/work-packages", { project_id: project.id, title: "Verified handoff", acceptance_criteria: ["Evidence is reviewed", "Client decision is recorded"] });
  const invitation = await post("admin-1", "admin", `/api/work-packages/${pack.id}/assignments`, { professional_id: professionalId });
  await post(professionalId, "professional", `/api/assignments/${invitation.id}/accept`, {});
  const deliverable = await post(professionalId, "professional", "/api/deliverables", { work_package_id: pack.id, title: "Client-ready outcome", content: "Synthetic evidence-backed outcome for browser verification." });
  await post(reviewerId, "reviewer", `/api/deliverables/${deliverable.id}/review`, { decision: "approved", comment: "Independent synthetic QA complete." });

  const browser = await chromium.launch({ headless: true, executablePath: CHROMIUM, args: ["--no-sandbox"] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await context.addInitScript(({ baseApi, actor, role }) => { window.STUDIO_API_URL = baseApi; localStorage.setItem("studio.synthetic.client", JSON.stringify({ actor, role })); }, { baseApi: API, actor: clientId, role: "client" });
  await context.tracing.start({ screenshots: true, snapshots: true, sources: true });
  const page = await context.newPage();
  const pageErrors = [];
  const failedRequests = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => failedRequests.push(`${request.method()} ${request.url()}`));
  try {
    await page.goto(FRONTEND, { waitUntil: "networkidle" });
    await page.evaluate(({ actor }) => {
      const tools = document.querySelector("#developer-tools");
      tools.open = true;
      const select = document.querySelector("#role");
      select.value = "client";
      select.dispatchEvent(new Event("change", { bubbles: true }));
      document.querySelector("#actor").value = actor;
      tools.open = true;
    }, { actor: clientId });
    await page.click("#refresh");
    await page.waitForSelector("#client-overview-view.active-view");
    await page.waitForSelector("#client-project-list .client-project-card");
    assert.match(await page.locator("#client-project-list").innerText(), /Client delivery project/);
    await page.screenshot({ path: `${ARTIFACTS}/client-portal-1440.png`, fullPage: true });
    await page.click('[data-view="client-communications"]');
    await page.waitForSelector("#client-message-project");
    await page.waitForTimeout(180);
    await page.locator("#client-message-body").fill("Please confirm the synthetic delivery window.");
    await page.click("#client-message-form button[type=submit]");
    await page.waitForTimeout(120);
    assert.match(await page.locator("#client-message-list").innerText(), /Please confirm the synthetic delivery window/);
    assert.match(await page.locator("#client-activity-list").innerText(), /Project Message Sent/);
    await page.screenshot({ path: `${ARTIFACTS}/client-portal-communications-1440.png`, fullPage: true });
    await page.click('[data-view="client-deliverables"]');
    await page.waitForSelector("#client-deliverables-list .client-deliverable-card");
    assert.match(await page.locator("#client-deliverables-list").innerText(), /Client-ready outcome/);
    await page.click(".client-revision-button");
    await page.locator(".client-revision-form textarea").fill("Please clarify the measurement period.");
    await page.click(".submit-client-revision");
    await page.waitForTimeout(120);
    const revised = await post(professionalId, "professional", "/api/deliverables", { work_package_id: pack.id, title: "Client-ready outcome v2", content: "Synthetic revised outcome with the requested measurement period." });
    await post(reviewerId, "reviewer", `/api/deliverables/${revised.id}/review`, { decision: "approved", comment: "Independent QA complete for the revised version." });
    await page.click('[data-view="client-overview"]');
    await page.click("#client-refresh");
    await page.click('[data-view="client-deliverables"]');
    await page.waitForSelector(".client-accept-button");
    await page.click(".client-accept-button");
    await page.waitForTimeout(160);
    assert.match(await page.locator("#client-deliverables-list").innerText(), /Accepted on record/);
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth <= 1));
    await page.screenshot({ path: `${ARTIFACTS}/client-portal-390x844.png`, fullPage: true });
    const unauthorized = await api("professional-outsider", "professional", "/api/client/overview");
    assert.strictEqual(unauthorized.status, 403);
    const completed = await post("admin-1", "admin", `/api/projects/${project.id}/complete`, {});
    assert.strictEqual(completed.status, "completed");
    assert.deepStrictEqual(pageErrors, []);
    assert.deepStrictEqual(failedRequests, []);
    console.log(JSON.stringify({ status: "passed", clientProject: project.id, clientAcceptance: "accepted", project: "completed", pageErrors, failedRequests }));
  } finally {
    await context.tracing.stop({ path: `${ARTIFACTS}/client-portal-trace.zip` });
    await browser.close();
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
