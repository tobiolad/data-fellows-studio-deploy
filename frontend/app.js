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
      name.textContent = record.name || record.title || record.actor_id || record.work_package_id || record.id || `Version ${record.version}`;
      const details = document.createElement("span");
      const membershipState = record.actor_id && (record.revoked_at ? "revoked" : "active");
      details.textContent = [record.role, record.status, membershipState, record.id && `ID: ${record.id}`].filter(Boolean).join(" · ");
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

async function createProject() {
  const body = {
    engagement_id: document.querySelector("#project-engagement").value.trim(),
    name: document.querySelector("#project-name").value.trim(),
  };
  if (Object.values(body).some((value) => !value)) return showMessage("Complete the engagement and project name first.", "error");
  try {
    const project = await request("/api/projects", { method: "POST", body: JSON.stringify(body) });
    document.querySelector("#project-id").value = project.id;
    showMessage(`Project created: ${project.id}`, "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function createWorkPackage() {
  const title = document.querySelector("#package-title").value.trim();
  const projectId = document.querySelector("#package-project").value.trim();
  const criteria = document.querySelector("#package-criteria").value.trim();
  if (!projectId || !title || !criteria) return showMessage("Complete the project, title and acceptance criteria first.", "error");
  try {
    const workPackage = await request("/api/work-packages", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, title, acceptance_criteria: criteria.split(",").map((item) => item.trim()).filter(Boolean) }),
    });
    document.querySelector("#package-id").value = workPackage.id;
    showMessage(`Work package created: ${workPackage.id}`, "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function inviteProfessional() {
  const packageId = document.querySelector("#invite-package").value.trim();
  const professionalId = document.querySelector("#invite-professional").value.trim();
  if (!packageId || !professionalId) return showMessage("Complete the work package and professional ID first.", "error");
  try {
    const assignment = await request(`/api/work-packages/${encodeURIComponent(packageId)}/assignments`, {
      method: "POST",
      body: JSON.stringify({ professional_id: professionalId }),
    });
    showMessage(`Invitation created: ${assignment.id}`, "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function loadMembers() {
  const id = document.querySelector("#members-organization").value.trim();
  if (!id) return showMessage("Enter an organization ID first.", "error");
  try {
    showRecords("Authorized membership roster", await request(`/api/organizations/${encodeURIComponent(id)}/members`));
    showMessage("Membership roster loaded.", "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function revokeMembership() {
  const organizationId = document.querySelector("#revoke-organization").value.trim();
  const memberId = document.querySelector("#revoke-member").value.trim();
  const role = document.querySelector("#revoke-role").value;
  if (!organizationId || !memberId) return showMessage("Complete the organization and member IDs first.", "error");
  try {
    await request(`/api/organizations/${encodeURIComponent(organizationId)}/members/${encodeURIComponent(memberId)}/${encodeURIComponent(role)}`, { method: "DELETE" });
    showMessage(`Membership revoked for ${memberId}.`, "success");
    document.querySelector("#members-organization").value = organizationId;
    await loadMembers();
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

async function loadAssignments() {
  try {
    showRecords("My scoped assignments", await request(`/api/professionals/${encodeURIComponent(actor.value.trim())}/assignments`));
    showMessage("Assignments loaded.", "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function submitApplication() {
  try {
    await request(`/api/professionals/${encodeURIComponent(actor.value.trim())}/application`, { method: "POST", body: "{}" });
    showMessage("Professional application submitted for review.", "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function decideProfessional(decision) {
  const id = document.querySelector("#professional-id").value.trim();
  if (!id) return showMessage("Enter a professional ID first.", "error");
  try {
    await request(`/api/professionals/${encodeURIComponent(id)}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision }),
    });
    showMessage(`Professional ${decision}.`, "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function loadAdmissions() {
  try {
    showRecords("Professional admission queue", await request("/api/professionals/admissions?status_filter=pending"));
    showMessage("Pending professional applications loaded.", "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function decideAssignment(decision) {
  const id = document.querySelector("#assignment-id").value.trim();
  if (!id) return showMessage("Enter an assignment ID first.", "error");
  try {
    await request(`/api/assignments/${encodeURIComponent(id)}/${decision}`, { method: "POST", body: "{}" });
    showMessage(`Assignment ${decision === "accept" ? "accepted" : "declined"}.`, "success");
    await loadAssignments();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function submitDeliverable() {
  const body = {
    work_package_id: document.querySelector("#package-id").value.trim(),
    title: document.querySelector("#deliverable-title").value.trim(),
    content: document.querySelector("#deliverable-content").value.trim(),
  };
  if (Object.values(body).some((value) => !value)) return showMessage("Complete the work package, title and content first.", "error");
  try {
    const deliverable = await request("/api/deliverables", { method: "POST", body: JSON.stringify(body) });
    document.querySelector("#deliverable-id").value = deliverable.id;
    showMessage(`Deliverable version ${deliverable.version} submitted for review.`, "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function acceptDeliverable() {
  const id = document.querySelector("#deliverable-id").value.trim();
  if (!id) return showMessage("Enter a deliverable ID first.", "error");
  try {
    await request(`/api/deliverables/${encodeURIComponent(id)}/accept`, { method: "POST", body: "{}" });
    showMessage("Approved deliverable accepted by the client.", "success");
    await loadDeliverables();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function reviewDeliverable() {
  const id = document.querySelector("#review-deliverable-id").value.trim();
  const decision = document.querySelector("#review-decision").value;
  const comment = document.querySelector("#review-comment").value.trim();
  if (!id || !comment) return showMessage("Complete the deliverable ID and review comment first.", "error");
  try {
    await request(`/api/deliverables/${encodeURIComponent(id)}/review`, {
      method: "POST",
      body: JSON.stringify({ decision, comment }),
    });
    showMessage(`Deliverable ${decision === "approved" ? "approved" : "returned for revision"}.`, "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function completeProject() {
  const id = document.querySelector("#complete-project-id").value.trim();
  if (!id) return showMessage("Enter a project ID first.", "error");
  try {
    await request(`/api/projects/${encodeURIComponent(id)}/complete`, { method: "POST", body: "{}" });
    showMessage("Project completed after client acceptance.", "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

function syncRole() {
  actor.value = role.value === "admin" ? "admin-1" : `${role.value}-1`;
  document.querySelectorAll(".admin-only").forEach((element) => {
    element.hidden = role.value !== "admin";
  });
  document.querySelectorAll(".professional-only").forEach((element) => {
    element.hidden = role.value !== "professional";
  });
  document.querySelectorAll(".client-only").forEach((element) => {
    element.hidden = role.value !== "client";
  });
}

document.querySelector("#refresh").addEventListener("click", refresh);
document.querySelector("#create-organization").addEventListener("click", createOrganization);
document.querySelector("#create-engagement").addEventListener("click", createEngagement);
document.querySelector("#create-project").addEventListener("click", createProject);
document.querySelector("#create-package").addEventListener("click", createWorkPackage);
document.querySelector("#invite-professional-button").addEventListener("click", inviteProfessional);
document.querySelector("#load-members").addEventListener("click", loadMembers);
document.querySelector("#revoke-membership").addEventListener("click", revokeMembership);
document.querySelector("#load-projects").addEventListener("click", loadProjects);
document.querySelector("#load-deliverables").addEventListener("click", loadDeliverables);
document.querySelector("#load-assignments").addEventListener("click", loadAssignments);
document.querySelector("#accept-assignment").addEventListener("click", () => decideAssignment("accept"));
document.querySelector("#decline-assignment").addEventListener("click", () => decideAssignment("decline"));
document.querySelector("#submit-application").addEventListener("click", submitApplication);
document.querySelector("#approve-professional").addEventListener("click", () => decideProfessional("approved"));
document.querySelector("#reject-professional").addEventListener("click", () => decideProfessional("rejected"));
document.querySelector("#load-admissions").addEventListener("click", loadAdmissions);
document.querySelector("#submit-deliverable").addEventListener("click", submitDeliverable);
document.querySelector("#accept-deliverable").addEventListener("click", acceptDeliverable);
document.querySelector("#review-deliverable").addEventListener("click", reviewDeliverable);
document.querySelector("#complete-project").addEventListener("click", completeProject);
role.addEventListener("change", syncRole);
syncRole();
