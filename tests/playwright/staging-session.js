// Exercise the deployed browser boundary with controlled API responses and no Entra credentials.
const assert = require("node:assert/strict");
const { chromium } = require("playwright");
(async () => {
  const browser = await chromium.launch({executablePath: process.env.PLAYWRIGHT_CHROMIUM || "/usr/bin/chromium", args: ["--no-sandbox"]});
  try {
    const page = await browser.newPage();
    let signedIn = false;
    let requests = 0;
    await page.route("**/api/**", async route => {
      requests++;
      assert.equal(route.request().headers().authorization, undefined);
      const me = new URL(route.request().url()).pathname === "/api/me";
      await route.fulfill({status: signedIn ? 200 : 401, json: signedIn ? (me ? {authentication:"entra", id:"session-reviewer", roles:["reviewer"]} : {items:[]}) : {detail:"Sign in required"}});
    });
    await page.goto("http://127.0.0.1:5173/");
    await page.locator("#sign-in-status").getByText("Sign in to continue.").waitFor();
    assert.ok(await page.locator(".app-shell").isHidden());
    signedIn = true;
    await page.reload();
    await page.getByRole("link", {name:"Sign out"}).waitFor();
    assert.equal(await page.locator("#actor").inputValue(), "session-reviewer");
    assert.ok(await page.locator("#developer-tools").isHidden());
    assert.equal(await page.locator("#role").inputValue(), "reviewer");
    console.log(JSON.stringify({stagingSession:"passed", mockedApiRequests:requests}));
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode=1});
