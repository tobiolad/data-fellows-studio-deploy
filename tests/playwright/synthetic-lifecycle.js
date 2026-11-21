// Full synthetic browser walkthrough. Start the API and static frontend first.
// This intentionally uses the test identity adapter and never calls live services.
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

  const api = async (actor, role, path, options = {}) => {
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: { Authorization: `Bearer test:${actor}:${role}`, "Content-Type": "application/json", ...(options.headers || {}) },
    });
    return { status: response.status, body: await response.json().catch(() => ({})) };
  };
  const role = async (value) => {
    await page.goto(FRONTEND, { waitUntil: "networkidle" });
    await page.evaluate((nextRole) => {
      const select = document.querySelector("#role");
      select.value = nextRole;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      document.querySelector("#developer-tools").open = true;
    }, value);
    await page.click("#refresh");
  };
  const fillAndClick = async (fields, button) => {
    for (const [selector, value] of Object.entries(fields)) await page.locator(selector).fill(value);
    await page.click(button);
    await page.waitForTimeout(120);
  };
  const screenshot = (name) => page.screenshot({ path: `${ARTIFACTS}/${name}.png`, fullPage: true });

  try {
    await page.goto(FRONTEND, { waitUntil: "networkidle" });
    await page.locator("#developer-tools summary").click();
    await page.click("#refresh");
    await role("admin");
    await fillAndClick({ "#organization-name": "Playwright Synthetic Organization" }, "#create-organization");
    const organizationId = await page.locator("#engagement-organization").inputValue();
    await fillAndClick({ "#engagement-name": "Synthetic diagnostic", "#engagement-objective": "Validate delivery" }, "#create-engagement");
    const engagementId = await page.locator("#engagement-id").inputValue();
    await fillAndClick({ "#project-engagement": engagementId, "#project-name": "Synthetic project" }, "#create-project");
    const projectId = await page.locator("#project-id").inputValue();
    await fillAndClick({ "#project-id": projectId, "#package-title": "Bounded work package", "#package-criteria": "QA complete,Client accepted" }, "#create-package");
    const packageId = await page.locator("#package-id").inputValue();
    assert.ok(organizationId && engagementId && projectId && packageId);
    await screenshot("playwright-admin-1440");

    await role("professional");
    await page.click('[data-view="applications"]');
    await page.click("#submit-application");
    await role("admin");
    await page.fill("#professional-id", "professional-1");
    await page.click("#approve-professional");
    for (const [actorId, memberRole] of [["professional-1", "professional"], ["reviewer-1", "reviewer"], ["client-1", "client"]]) {
      const grant = await api("admin-1", "admin", `/api/organizations/${organizationId}/members`, { method: "POST", body: JSON.stringify({ actor_id: actorId, role: memberRole }) });
      assert.ok([200, 201, 409].includes(grant.status));
    }
    await fillAndClick({ "#invite-package": packageId, "#invite-professional": "professional-1" }, "#invite-professional-button");
    const assignmentResponse = await api("professional-1", "professional", "/api/professionals/professional-1/assignments");
    const assignment = assignmentResponse.body.find((item) => item.work_package_id === packageId);
    assert.ok(assignment?.id);
    await screenshot("playwright-vetting-and-assignment-1440");

    await role("professional");
    await page.click('[data-view="deliverables"]');
    await page.fill("#package-id", packageId);
    await page.fill("#assignment-id", assignment.id);
    await Promise.all([
      page.waitForResponse((response) => response.url().includes(`/api/assignments/${assignment.id}/accept`) && response.status() === 200),
      page.click("#accept-assignment"),
    ]);
    await page.fill("#package-id", packageId);
    await page.fill("#deliverable-title", "Synthetic deliverable");
    await page.fill("#deliverable-content", "Synthetic evidence-backed content");
    await Promise.all([
      page.waitForResponse((response) => response.url().endsWith("/api/deliverables") && response.status() === 201),
      page.click("#submit-deliverable"),
    ]);
    await page.waitForFunction(() => Boolean(document.querySelector("#deliverable-id")?.value), null, { timeout: 10000 });
    const deliverableId = await page.locator("#deliverable-id").inputValue();
    assert.ok(deliverableId);
    await screenshot("playwright-professional-1440");

    const unauthorized = await api("client-1", "client", `/api/deliverables/${deliverableId}/review`, { method: "POST", body: JSON.stringify({ decision: "approved", comment: "not allowed" }) });
    assert.strictEqual(unauthorized.status, 403);
    await role("reviewer");
    await page.click('[data-view="reviews"]');
    await fillAndClick({ "#review-deliverable-id": deliverableId, "#review-comment": "Independent synthetic review" }, "#review-deliverable");
    await screenshot("playwright-reviewer-1440");

    await role("client");
    await page.click('[data-view="deliverables"]');
    await page.fill("#package-id", packageId);
    await page.click("#load-deliverables");
    await page.fill("#deliverable-id", deliverableId);
    await page.click("#accept-deliverable");
    await page.setViewportSize({ width: 390, height: 844 });
    await screenshot("playwright-client-390x844");

    await page.setViewportSize({ width: 1440, height: 900 });
    await role("admin");
    await page.fill("#complete-project-id", projectId);
    await page.click("#complete-project");
    await page.waitForTimeout(120);
    const projects = await api("admin-1", "admin", `/api/engagements/${engagementId}/projects`);
    assert.strictEqual(projects.body.find((project) => project.id === projectId)?.status, "completed");
    await screenshot("playwright-admin-completed-1440");
    assert.deepStrictEqual(pageErrors, []);
    assert.deepStrictEqual(failedRequests, []);
    console.log(JSON.stringify({ status: "passed", unauthorizedClientReview: 403, project: "completed", pageErrors, failedRequests }));
  } finally {
    await context.tracing.stop({ path: `${ARTIFACTS}/playwright-trace.zip` });
    await browser.close();
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
