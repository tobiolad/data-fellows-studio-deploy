const api = window.STUDIO_API_URL || "http://localhost:8100";
const role = document.querySelector("#role");
const actor = document.querySelector("#actor");
const identityStatus = document.querySelector("#identity-status");
const results = document.querySelector("#workspace-results");

function token() {
  return `Bearer test:${actor.value.trim()}:${role.value}`;
}

async function request(path, options = {}) {
  const response = await fetch(`${api}${path}`, {
    ...options,
    headers: { Authorization: token(), "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
  return payload;
}

function showMessage(message, kind = "info") {
  identityStatus.textContent = message;
  identityStatus.className = `status ${kind}`;
}

function showRecords(title, records) {
  const section = document.createElement("section");
  section.className = "result-section";
  const heading = document.createElement("h3");
  heading.textContent = title;
  section.append(heading);
  if (!records.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No records are visible for this identity.";
    section.append(empty);
  } else {
    const list = document.createElement("ul");
    list.className = "record-list";
    records.forEach((record) => {
      const item = document.createElement("li");
      const name = document.createElement("strong");
      name.textContent = record.name || record.title || `Version ${record.version}`;
      const details = document.createElement("span");
      details.textContent = [record.status, record.id && `ID: ${record.id}`].filter(Boolean).join(" · ");
      item.append(name, details);
      list.append(item);
    });
    section.append(list);
  }
  results.replaceChildren(section);
}

async function refresh() {
  try {
    const [me, health] = await Promise.all([request("/api/me"), fetch(`${api}/health`).then((r) => r.json())]);
    showMessage(`${me.id} · ${me.roles.join(", ")} · API ${health.status}`, "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function createOrganization() {
  const name = document.querySelector("#organization-name").value.trim();
  if (!name) return showMessage("Enter an organization name first.", "error");
  try {
    const organization = await request("/api/organizations", { method: "POST", body: JSON.stringify({ name }) });
    document.querySelector("#engagement-organization").value = organization.id;
    showMessage(`Organization created: ${organization.id}`, "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function createEngagement() {
  const body = {
    organization_id: document.querySelector("#engagement-organization").value.trim(),
    name: document.querySelector("#engagement-name").value.trim(),
    objective: document.querySelector("#engagement-objective").value.trim(),
  };
  if (Object.values(body).some((value) => !value)) return showMessage("Complete all engagement fields first.", "error");
  try {
    const engagement = await request("/api/engagements", { method: "POST", body: JSON.stringify(body) });
    document.querySelector("#engagement-id").value = engagement.id;
    showMessage(`Engagement created: ${engagement.id}`, "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function loadProjects() {
  const id = document.querySelector("#engagement-id").value.trim();
  if (!id) return showMessage("Enter an engagement ID first.", "error");
  try {
    showRecords("Authorized projects", await request(`/api/engagements/${encodeURIComponent(id)}/projects`));
    showMessage("Projects loaded.", "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function loadDeliverables() {
  const id = document.querySelector("#package-id").value.trim();
  if (!id) return showMessage("Enter a work package ID first.", "error");
  try {
    showRecords("Visible deliverables", await request(`/api/work-packages/${encodeURIComponent(id)}/deliverables`));
    showMessage("Deliverables loaded.", "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

function syncRole() {
  actor.value = role.value === "admin" ? "admin-1" : `${role.value}-1`;
  document.querySelectorAll(".admin-only").forEach((element) => {
    element.hidden = role.value !== "admin";
  });
}

document.querySelector("#refresh").addEventListener("click", refresh);
document.querySelector("#create-organization").addEventListener("click", createOrganization);
document.querySelector("#create-engagement").addEventListener("click", createEngagement);
document.querySelector("#load-projects").addEventListener("click", loadProjects);
document.querySelector("#load-deliverables").addEventListener("click", loadDeliverables);
role.addEventListener("change", syncRole);
syncRole();
