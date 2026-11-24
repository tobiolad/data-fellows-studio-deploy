// Project collaboration across three separate browser sessions and a disposable synthetic data set.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { chromium } = require("playwright");
const { admitProfessional } = require("./admission-fixture");
const apiUrl = process.env.STUDIO_API_URL || "http://127.0.0.1:8100";
const base = process.env.STUDIO_BROWSER_URL || "http://127.0.0.1:5173/index.html?harness=synthetic";
const artifacts = process.env.STUDIO_ARTIFACT_DIR || "artifacts";
async function api(actor, role, path, options = {}) {
  const response = await fetch(apiUrl + path, {...options, headers: {"Content-Type":"application/json", Authorization:`Bearer test:${actor}:${role}`}});
  return {status:response.status, body:await response.json()};
}
async function post(actor, role, path, body) {
  const result = await api(actor, role, path, {method:"POST",body:JSON.stringify(body)});
  assert.ok(result.status < 300, path + " " + result.status);
  return result.body;
}
async function main() {
  const suffix = Date.now();
  const client = "coord-client-" + suffix, professional = "coord-professional-" + suffix;
  const staff = (path, body) => post("admin-1","admin",path,body);
  const org = await staff("/api/organizations",{name:"Synthetic coordination"});
  await admitProfessional(api, professional);
  for (const [id, role] of [[client,"client"],[professional,"professional"]]) {
    await staff(`/api/organizations/${org.id}/members`,{actor_id:id,role});
  }
  const engagement = await staff("/api/engagements",{organization_id:org.id,name:"Reporting service",objective:"Agree the reporting period"});
  const project = await staff("/api/projects",{engagement_id:engagement.id,name:"Reporting schedule"});
  const pack = await staff("/api/work-packages",{project_id:project.id,title:"Weekly reporting schedule",acceptance_criteria:["Record the period"]});
  const invitation = await staff(`/api/work-packages/${pack.id}/assignments`,{professional_id:professional});
  await post(professional,"professional",`/api/assignments/${invitation.id}/accept`,{});
  const browser = await chromium.launch({executablePath:process.env.PLAYWRIGHT_CHROMIUM || "/usr/bin/chromium",args:["--no-sandbox"]});
  const errors = [], checks = [];
  fs.mkdirSync(artifacts,{recursive:true});
  async function workspace(actor, role, view, width) {
    const page = await browser.newPage({viewport:{width,height:900}});
    page.on("pageerror", error => errors.push(error.message));
    await page.addInitScript(url => window.STUDIO_API_URL=url,apiUrl);
    await page.goto(base);
    await page.evaluate(({actor, role}) => {
      const select = document.querySelector("#role");
      select.value = role;
      select.dispatchEvent(new Event("change"));
      document.querySelector("#actor").value=actor;
      document.querySelector("#refresh").click();
    },{actor,role});
    const link = page.locator(`a[data-view="${view}"]`);
    if (width < 768) await page.locator("#mobile-menu").click();
    await link.click();
    return page;
  }
  async function capture(page, name) {
    await page.screenshot({path:`${artifacts}/${name}.png`,fullPage:true});
    if (process.env.STUDIO_AXE_PATH) {
      await page.addScriptTag({path:process.env.STUDIO_AXE_PATH});
      const result = await page.evaluate(async () => {
        const scan = await window.axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}});
        return scan.violations.map(f => ({id:f.id,impact:f.impact,nodes:f.nodes.map(n=>n.target)}));
      });
      checks.push({view:name,violations:result});
    }
  }
  try {
    const cp = await workspace(client,"client","client-communications",390);
    await cp.getByLabel("Request for Data Fellows").fill("Confirm quarter-end reporting");
    await cp.getByRole("button",{name:"Submit request"}).click();
    await cp.getByText("Confirm quarter-end reporting",{exact:true}).waitFor();
    const pp = await workspace(professional,"professional","messages",1024);
    const work = pp.locator("#work-project-channel");
    await work.getByLabel("Message",{exact:true}).fill("Supervisor, the schedule is ready to review.");
    await work.getByRole("button",{name:"Send message"}).click();
    await work.getByText("Supervisor, the schedule is ready to review.",{exact:true}).waitFor();
    const ap = await workspace("admin-1","admin","admin-communications",1440);
    const desk = ap.locator("#staff-project-channel");
    await desk.getByRole("combobox",{name:"Project",exact:true}).selectOption(project.id);
    await desk.getByText("Supervisor, the schedule is ready to review.",{exact:true}).waitFor();
    await desk.getByLabel("Reason",{exact:true}).fill("Quarter-end is within scope.");
    await desk.getByRole("button",{name:"Record decision"}).click();
    await desk.getByText("Quarter-end is within scope.",{exact:true}).waitFor();
    await desk.getByText("Add a document reference").click();
    await desk.getByLabel("Document title").fill("Approved reporting brief");
    await desk.getByLabel("Private storage reference").fill("private://synthetic/reporting-brief");
    await desk.getByRole("button",{name:"Add reference"}).click();
    await desk.getByText("Approved reporting brief",{exact:true}).waitFor();
    await desk.getByRole("combobox",{name:"Audience",exact:true}).selectOption("professional");
    await desk.getByLabel("Message",{exact:true}).fill("Use the approved weekly schedule.");
    await desk.getByRole("button",{name:"Send message"}).click();
    await desk.getByText("Use the approved weekly schedule.",{exact:true}).waitFor();
    await work.getByRole("combobox",{name:"Project",exact:true}).dispatchEvent("change");
    await work.getByText("Use the approved weekly schedule.",{exact:true}).waitFor();
    await cp.locator("#client-message-project").dispatchEvent("change");
    await cp.getByText("Approved reporting brief",{exact:true}).waitFor();
    await cp.getByText("Quarter-end is within scope.",{exact:true}).waitFor();
    assert.doesNotMatch(await cp.locator("#client-message-list").innerText(), /weekly schedule|Supervisor/);
    for (const [page,name] of [[cp,"client-coordination-390"],[ap,"staff-coordination-1440"],[pp,"professional-channel-1024"]]) await capture(page,name);
    assert.deepEqual(errors,[]);
    fs.writeFileSync(`${artifacts}/collaboration-checks.json`,JSON.stringify({errors,checks},null,2));
    assert.ok(checks.every(view => view.violations.length === 0), "Accessibility findings are recorded in collaboration-checks.json");
    console.log(JSON.stringify({workflow:"passed",pageErrors:errors,axeViews:checks.length,axeViolations:checks.map(x=>x.violations.length)}));
  } finally { await browser.close(); }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
