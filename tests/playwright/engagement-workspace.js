const assert = require("node:assert/strict");
const { chromium } = require("playwright");
const frontend = process.env.STUDIO_BROWSER_URL || "http://127.0.0.1:5173/index.html?harness=synthetic";
const api = process.env.STUDIO_API_URL || "http://127.0.0.1:8100";

async function main() {
  const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM || "/usr/bin/chromium", args: ["--no-sandbox"] });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.addInitScript(url => window.STUDIO_API_URL = url, api);
    await page.goto(frontend.split("?")[0]);
    assert.equal(await page.locator("#developer-tools").isVisible(), false);
    await page.goto(frontend);
    await page.locator("#developer-tools summary").click();
    await page.selectOption("#role", "admin");
    const name = "Reporting scope " + Date.now();
    const dialog = page.getByRole("dialog", {name: "New engagement"});
    await page.click("#admin-new-engagement");
    await dialog.locator('select option:not([value=""])').first().waitFor({state: "attached"});
    await dialog.getByLabel("Client organization").selectOption({index: 1});
    await dialog.getByLabel("Engagement name").fill(name);
    await dialog.getByLabel("Agreed objective").fill("Shorten the weekly reporting cycle");
    await dialog.getByRole("button", {name: "Create engagement"}).click();
    const view = page.locator("#admin-engagements-view");
    await view.getByRole("searchbox").fill(name);
    await view.getByRole("button", {name: "View engagement"}).click();
    assert.equal(await page.locator("#admin-drawer-content h2").textContent(), name);
    assert.deepEqual(errors, []);
    console.log("Passed harness isolation, engagement creation, search and details");
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
