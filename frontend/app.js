const api = window.STUDIO_API_URL || "http://localhost:8100";
const syntheticHarness = ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname)
  && new URLSearchParams(location.search).get("harness") === "synthetic";
const role = document.querySelector("#role");
const actor = document.querySelector("#actor");
const identityStatus = document.querySelector("#identity-status");
let assignments = [];
let opportunities = [];
let clientData = null;
let clientOperations = { projectId: "", messages: [], activity: [] };
let professionalProfile = null;
let requestedProfessionalView = location.hash.slice(1) || "overview";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
function token() { return `Bearer test:${actor.value.trim()}:${role.value}`; }
async function request(path, options = {}) {
  const identity = token();
  if (!["localhost", "127.0.0.1", "[::1]"].includes(location.hostname)) {
    throw new Error("This workspace requires a configured sign-in provider.");
  }
  const response = await fetch(`${api}${path}`, { ...options, headers: { Authorization: token(), "Content-Type": "application/json", ...(options.headers || {}) } });
  const payload = await response.json().catch(() => ({}));
  if (identity !== token()) throw new Error("Workspace identity changed.");
  if (!response.ok) throw Object.assign(new Error(payload.detail || `Request failed (${response.status})`), { status: response.status });
  return payload;
}
function showMessage(message, kind = "info") { identityStatus.textContent = message; identityStatus.dataset.kind = kind; }
function escapeHtml(value) { return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char])); }
function dateLabel(value) { if (!value) return "No deadline recorded"; const date = new Date(value); return Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }); }
function statusClass(status) { return String(status || "neutral").replaceAll("_", "-").replaceAll(" ", "-"); }
function statusLabel(status) { return String(status || "Not started").replaceAll("_", " ").replaceAll(".", " ").replaceAll("-", " ").replace(/\s+/g, " ").trim().replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function emptyState(title, text) { return `<div class="empty-panel inline-empty"><span class="empty-icon">◇</span><h2>${escapeHtml(title)}</h2><p>${escapeHtml(text)}</p></div>`; }


function renderMetrics() {
  const active = assignments.filter((item) => item.status === "accepted").length;
  const pending = assignments.filter((item) => item.status === "invited").length;

  $("#metric-grid").innerHTML = `<article class="metric-card"><div class="metric-top"><span class="metric-label">Active assignments</span><span class="metric-icon">▣</span></div><div class="metric-value">${active}</div><div class="metric-note">Scoped work packages</div></article><article class="metric-card"><div class="metric-top"><span class="metric-label">Pending invitations</span><span class="metric-icon purple">✉</span></div><div class="metric-value">${pending}</div><div class="metric-note">Action needed</div></article>`;
  $("#invitation-count").textContent = pending; $("#invitation-count").hidden = pending === 0;
}
function assignmentStatus(item) { return item.status === "accepted" ? "in-progress" : item.status === "invited" ? "invited" : "neutral"; }
function assignmentCard(item, compact = false) {
  const title = item.title || "Assigned work package";
  return `<article class="panel ${compact ? "assignment-card compact" : "assignment-card"}" data-assignment-id="${escapeHtml(item.id)}"><div class="assignment-name"><span class="assignment-mark">▣</span><div><strong>${escapeHtml(title)}</strong><small>${escapeHtml(item.project_name || "Project reference unavailable")}</small></div></div><p>${escapeHtml(item.objective || "Scoped delivery work assigned by Data Fellows.")}</p><div class="assignment-meta"><div><span>Status</span><strong><span class="status-badge ${assignmentStatus(item)}">${escapeHtml(statusLabel(item.status))}</span></strong></div><div><span>Access expires</span><strong>${escapeHtml(dateLabel(item.expires_at))}</strong></div><div><span>Access</span><strong>Assignment-scoped</strong></div></div><div class="card-footer"><small>Data Fellows delivery lead</small><button class="secondary-button open-assignment" data-package-id="${escapeHtml(item.work_package_id)}">Open workspace →</button></div></article>`;
}
function renderAssignments() {
  const accepted = assignments.filter(item => item.status === "accepted");
  const rows = accepted.slice(0, 5);
  $("#assignment-table").innerHTML = rows.length ? `<table><thead><tr><th>Project</th><th>Delivery lead</th><th>Access expires</th><th>Status</th><th>Access</th></tr></thead><tbody>${rows.map((item) => `<tr data-assignment-id="${escapeHtml(item.id)}"><td><div class="assignment-name"><span class="assignment-mark">▣</span><div><strong>${escapeHtml(item.title || "Work package")}</strong><small>${escapeHtml(item.project_name || "Project reference")}</small></div></div></td><td>Data Fellows<br /><small class="muted">Delivery lead</small></td><td>${escapeHtml(dateLabel(item.expires_at))}</td><td><span class="status-badge ${assignmentStatus(item)}">${escapeHtml(statusLabel(item.status))}</span></td><td><button class="text-button open-assignment" data-package-id="${escapeHtml(item.work_package_id)}">View task →</button></td></tr>`).join("")}</tbody></table>` : emptyState("No assignments yet", "Accepted invitations and scoped work will appear here.");
  $("#assignments-list").innerHTML = accepted.length ? accepted.map((item) => assignmentCard(item)).join("") : emptyState("No assignments yet", "Your approved, scoped work packages will appear here.");
  const picker = $("#assignment-picker");
  picker.replaceChildren(new Option("Choose an accepted assignment", ""));
  for (const item of accepted) {
    picker.add(new Option([item.project_name, item.title || "Assigned work"].filter(Boolean).join(" — "), item.work_package_id));
  }
  picker.value = accepted.some(item => item.work_package_id === $("#package-id").value)
    ? $("#package-id").value : accepted[0]?.work_package_id || "";
  $("#package-id").value = picker.value;
  $("#submit-deliverable").disabled = !picker.value;
  $$(".open-assignment").forEach(button => button.addEventListener("click", () => {
    picker.value = button.dataset.packageId;
    $("#package-id").value = picker.value;
    navigate("deliverables");
  }));
}
function renderDeadlines() { const due = assignments.filter(item => item.status === "accepted" && item.expires_at).sort((a, b) => new Date(a.expires_at) - new Date(b.expires_at)).slice(0, 3); $("#deadline-list").innerHTML = due.length ? due.map((item) => `<div class="timeline-item"><strong>${escapeHtml(item.title || "Assignment")}</strong><span>Access expires ${escapeHtml(dateLabel(item.expires_at))}</span></div>`).join("") : `<p class="muted">No deadlines recorded for your active work.</p>`; }
function renderFeedback() { $("#feedback-list").innerHTML = `<div class="feedback-item"><strong>No review feedback yet</strong><p>Independent review notes will appear here after a deliverable is reviewed.</p></div>`; }
function renderInvitationHighlight() { const item = assignments.find((assignment) => assignment.status === "invited"); $("#invitation-highlight").innerHTML = item ? `<div class="invitation-kicker">NEW INVITATION</div><div class="invitation-title">${escapeHtml(item.title || "Scoped delivery invitation")}</div><p>${escapeHtml(item.objective || "Review the scope and acceptance criteria before responding.")}</p><div class="invitation-actions"><button class="primary-button accept-invitation" data-assignment-id="${escapeHtml(item.id)}">Accept invitation</button><button class="secondary-button decline-invitation" data-assignment-id="${escapeHtml(item.id)}">Decline</button></div>` : `<div class="invitation-kicker">INVITATIONS</div><div class="invitation-title">No invitations requiring attention</div><p>New scoped opportunities from Data Fellows will appear here.</p>`; $$(".accept-invitation").forEach((button) => button.addEventListener("click", () => decideAssignment(button.dataset.assignmentId, "accept"))); $$(".decline-invitation").forEach((button) => button.addEventListener("click", () => decideAssignment(button.dataset.assignmentId, "decline"))); }
function renderInvitations() { const pending = assignments.filter((item) => item.status === "invited"); $("#invitations-list").innerHTML = pending.length ? pending.map((item) => `<article class="panel invitation-detail"><div class="eyebrow">INVITATION</div><h2>${escapeHtml(item.title || "Scoped delivery invitation")}</h2><p>${escapeHtml(item.objective || "Review the assigned scope and acceptance criteria before responding.")}</p><div class="assignment-meta"><div><span>Project</span><strong>${escapeHtml(item.project_name || "Project reference")}</strong></div><div><span>Supervisor</span><strong>Data Fellows delivery lead</strong></div><div><span>Deadline</span><strong>${escapeHtml(dateLabel(item.expires_at))}</strong></div></div><div class="card-footer"><small>Acceptance activates assignment-scoped access only.</small><div class="invitation-actions"><button class="primary-button accept-invitation" data-assignment-id="${escapeHtml(item.id)}">Accept invitation</button><button class="secondary-button decline-invitation" data-assignment-id="${escapeHtml(item.id)}">Decline</button></div></div></article>`).join("") : emptyState("No pending invitations", "New scoped invitations from Data Fellows will appear here."); $$("#invitations-list .accept-invitation").forEach((button) => button.addEventListener("click", () => decideAssignment(button.dataset.assignmentId, "accept"))); $$("#invitations-list .decline-invitation").forEach((button) => button.addEventListener("click", () => decideAssignment(button.dataset.assignmentId, "decline"))); }

async function loadAssignments() { try { assignments = await request(`/api/professionals/${encodeURIComponent(actor.value.trim())}/assignments`); renderMetrics(); renderAssignments(); renderDeadlines(); renderInvitationHighlight(); renderInvitations(); await loadSelectedDeliverables(); } catch (error) { showMessage(error.message, "error"); } }
async function loadSelectedDeliverables() { const packageId = $("#package-id")?.value.trim(); if (!packageId) { $("#deliverables-list").innerHTML = emptyState("Choose an assignment", "Open an assignment to view its versioned deliverables."); return; } try { const deliverables = await request(`/api/work-packages/${encodeURIComponent(packageId)}/deliverables`); $("#deliverables-list").innerHTML = deliverables.length ? deliverables.map((item) => `<article class="panel deliverable-card"><div class="panel-heading"><div><h2>${escapeHtml(item.title)}</h2><p>Version ${item.version} · Submitted by ${escapeHtml(item.submitted_by || "authorized delivery resource")}</p></div><span class="status-badge ${statusClass(item.status)}">${escapeHtml(statusLabel(item.status))}</span></div><p class="muted">${escapeHtml(item.content)}</p><div class="card-footer"><small>Immutable version record</small>${item.status === "approved" || item.status === "accepted" ? `<button class="text-button choose-deliverable" data-deliverable-id="${escapeHtml(item.id)}">Use this version</button>` : ""}</div></article>`).join("") : emptyState("No deliverables yet", "Submit a version when your assigned work is ready for review."); $$(".choose-deliverable").forEach((button) => { button.addEventListener("click", () => { $("#deliverable-id").value = button.dataset.deliverableId; }); }); } catch (error) { $("#deliverables-list").innerHTML = emptyState("Deliverables unavailable", error.message); } }
async function loadOpportunities() { try { opportunities = await request("/api/opportunities"); const filters = [...new Set(opportunities.map((item) => item.specialization).filter(Boolean))]; $("#opportunity-filter").innerHTML = `<option value="">All specializations</option>${filters.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("")}`; renderOpportunities(); } catch (error) { $("#opportunity-list").innerHTML = emptyState("Opportunities unavailable", error.message); } }
function renderOpportunities() { const filter = $("#opportunity-filter").value; const query = $("#opportunity-search").value.trim().toLowerCase(); const visible = opportunities.filter((item) => (!filter || item.specialization === filter) && (!query || `${item.title} ${item.summary} ${item.skills?.join(" ")}`.toLowerCase().includes(query))); $("#opportunity-list").innerHTML = visible.length ? visible.map((item) => `<article class="panel opportunity-card"><div class="eyebrow">${escapeHtml(item.specialization || "General")}</div><h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.summary)}</p><div class="chip-list">${(item.skills || []).map((skill) => `<span class="chip">${escapeHtml(skill)}</span>`).join("")}</div><div class="card-footer"><small>${item.compensation ? escapeHtml(item.compensation) : "Compensation terms shared after selection"}<br />${item.deadline ? `Response by ${escapeHtml(dateLabel(item.deadline))}` : "No response deadline recorded"}</small>${item.interest_status ? `<span class="status-badge success">${escapeHtml(statusLabel(item.interest_status))}</span>` : `<button class="primary-button interest-button" data-opportunity-id="${escapeHtml(item.id)}">Express interest</button>`}</div></article>`).join("") : emptyState("No opportunities match", "Data Fellows will publish sanitized opportunities when eligible work is available."); $$(".interest-button").forEach((button) => button.addEventListener("click", () => expressInterest(button.dataset.opportunityId))); }
async function expressInterest(opportunityId) { const approach = window.prompt("Briefly describe the relevant experience you would bring to this opportunity:", "I can contribute scoped delivery experience and independent QA."); if (!approach) return; try { await request(`/api/opportunities/${encodeURIComponent(opportunityId)}/interests`, { method: "POST", body: JSON.stringify({ approach }) }); showMessage("Interest submitted for Data Fellows review.", "success"); await loadOpportunities(); } catch (error) { showMessage(error.message, "error"); } }
async function decideAssignment(id, decision) { try { await request(`/api/assignments/${encodeURIComponent(id)}/${decision}`, { method: "POST", body: "{}" }); showMessage(`Invitation ${decision === "accept" ? "accepted" : "declined"}.`, "success"); await loadAssignments(); } catch (error) { showMessage(error.message, "error"); } }
async function submitDeliverable() { const packageId = $("#package-id").value.trim(); const title = $("#deliverable-title").value.trim(); const content = $("#deliverable-content").value.trim(); if (!packageId || !title || !content) return showMessage("Choose an assignment and complete the deliverable fields first.", "error"); try { const item = await request("/api/deliverables", { method: "POST", body: JSON.stringify({ work_package_id: packageId, title, content }) }); $("#deliverable-id").value = item.id; $("#deliverable-status").textContent = `Version ${item.version} submitted for independent review.`; showMessage("Deliverable submitted for review.", "success"); await loadSelectedDeliverables(); } catch (error) { showMessage(error.message, "error"); } }
async function acceptDeliverable() { const id = $("#deliverable-id").value.trim(); if (!id) return showMessage("Choose an approved deliverable version first.", "error"); try { await request(`/api/deliverables/${encodeURIComponent(id)}/accept`, { method: "POST", body: "{}" }); showMessage("Approved deliverable accepted.", "success"); await loadSelectedDeliverables(); } catch (error) { showMessage(error.message, "error"); } }
async function reviewDeliverable() { const id = $("#review-deliverable-id").value.trim(); const decision = $("#review-decision").value; const comment = $("#review-comment").value.trim(); if (!id || !comment) return showMessage("Complete the deliverable and review comment first.", "error"); try { await request(`/api/deliverables/${encodeURIComponent(id)}/review`, { method: "POST", body: JSON.stringify({ decision, comment }) }); showMessage(`Deliverable ${statusLabel(decision)}.`, "success"); } catch (error) { showMessage(error.message, "error"); } }

let currentApplication = null;
let profileAccessOwner = "";
let profileEditMode = false;
let profileDraftLists = { experience: [], education: [], portfolio: [], evidence_references: [] };
let profileDraftTags = { skills: [], specializations: [] };
async function submitApplication() { try { const result = await request(`/api/professionals/${encodeURIComponent(actor.value.trim())}/application`, { method: "POST", body: "{}" }); showMessage("Professional application submitted for review.", "success"); updateApplication(result); await loadProfessionalProfile(); } catch (error) { showMessage(error.message, "error"); } }
function admissionTone(status) { return status === "approved" ? "success" : ["declined", "rejected", "revoked"].includes(status) ? "warning" : status === "assessment" ? "info" : "neutral"; }
function updateApplication(record) {
  if (!record) return;
  currentApplication = record;
  profileAccessOwner = token();
  $("#edit-profile-button").disabled = false;
  $("#submit-application").disabled = true;
  const label = statusLabel(record.status);
  $("#application-status-text").textContent = `Your application is ${label.toLowerCase()}. ${record.next_action || "Data Fellows will contact you about the next step."}`;
  $("#application-status-badge").textContent = label;
  $("#application-status-badge").className = `status-badge ${admissionTone(record.status)}`;
  const reviewBadge = $("#application-review-status");
  if (reviewBadge) { reviewBadge.textContent = label; reviewBadge.className = `status-badge ${admissionTone(record.status)}`; }
  const missing = (record.missing_information || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const assessments = (record.assessment_requests || []).map((item) => `<li><strong>${escapeHtml(item.title || "Assessment request")}</strong>${item.description ? `<span>${escapeHtml(item.description)}</span>` : ""}</li>`).join("");
  const evidence = (record.evidence_references || []).map((item) => `<li>${escapeHtml(item.label || "Evidence reference")} <span class="muted">${escapeHtml(item.status || "pending review")}</span></li>`).join("");
  const content = $("#application-review-content");
  if (content) content.innerHTML = `<div><span class="detail-label">Next action</span><strong>${escapeHtml(record.next_action || "No action recorded")}</strong></div><div><span class="detail-label">Missing information</span>${missing ? `<ul class="review-list">${missing}</ul>` : `<strong>None recorded</strong>`}</div><div><span class="detail-label">Assessment requests</span>${assessments ? `<ul class="review-list">${assessments}</ul>` : `<strong>None recorded</strong>`}</div><div><span class="detail-label">Evidence references</span>${evidence ? `<ul class="review-list">${evidence}</ul>` : `<strong>None recorded</strong>`}</div>${record.decision_reason ? `<div class="review-decision"><span class="detail-label">Reviewer decision note</span><p>${escapeHtml(record.decision_reason)}</p></div>` : ""}`;
}
async function loadApplication() { try { updateApplication(await request(`/api/professionals/${encodeURIComponent(actor.value.trim())}/application`)); } catch (error) { if (!error.message.includes("404")) showMessage(error.message, "error"); } }
function profileCompleteness(profile) {
  if (!profile) return "Not started";
  const checks = [profile.display_name, profile.headline, profile.bio, profile.skills?.length, profile.specializations?.length, profile.experience?.length, profile.education?.length, profile.availability];
  return `${Math.round((checks.filter(Boolean).length / checks.length) * 100)}% complete`;
}
function renderTagEditor(type) {
  const host = $(`#profile-${type}-list`); if (!host) return;
  host.innerHTML = profileDraftTags[type].length ? profileDraftTags[type].map((item, index) => `<span class="chip">${escapeHtml(item)} <button type="button" class="chip-remove" data-tag-type="${type}" data-tag-index="${index}" aria-label="Remove ${escapeHtml(item)}">×</button></span>`).join("") : `<span class="muted">None added yet.</span>`;
  host.querySelectorAll(".chip-remove").forEach((button) => button.addEventListener("click", () => { profileDraftTags[type].splice(Number(button.dataset.tagIndex), 1); renderTagEditor(type); }));
}
const entryConfig = { experience: { title: "Role", fields: [["title", "Role or title"], ["company", "Organization"], ["start", "Start year"], ["end", "End year"]] }, education: { title: "Education", fields: [["school", "Institution"], ["degree", "Degree or credential"], ["field", "Field"]] }, portfolio: { title: "Portfolio project", fields: [["title", "Project title"], ["url", "Reference URL"]] }, evidence_references: { title: "Evidence reference", fields: [["label", "Label"], ["reference", "Private or quarantine reference"], ["classification", "Classification"]] } };
function renderEntryEditor(type) {
  const host = $(`#profile-${type === "evidence_references" ? "evidence" : type}-entries`); if (!host) return;
  const config = entryConfig[type];
  host.innerHTML = profileDraftLists[type].map((entry, index) => `<div class="repeatable-row" data-entry-type="${type}" data-entry-index="${index}">${config.fields.map(([field, placeholder]) => `<label>${escapeHtml(placeholder)}<input data-entry-field="${field}" value="${escapeHtml(entry[field] || "")}" placeholder="${escapeHtml(placeholder)}" /></label>`).join("")}<button type="button" class="text-button remove-entry" aria-label="Remove ${escapeHtml(config.title)} ${index + 1}">Remove</button></div>`).join("") || `<p class="muted">No ${type === "evidence_references" ? "references" : type} added yet.</p>`;
  host.querySelectorAll(".repeatable-row").forEach((row) => row.querySelectorAll("[data-entry-field]").forEach((input) => input.addEventListener("input", () => { profileDraftLists[type][Number(row.dataset.entryIndex)][input.dataset.entryField] = input.value; })));
  host.querySelectorAll(".remove-entry").forEach((button) => button.addEventListener("click", () => { profileDraftLists[type].splice(Number(button.closest(".repeatable-row").dataset.entryIndex), 1); renderEntryEditor(type); }));
}
function renderProfileSummary(profile) {
  if (!profile) return;
  $("#profile-summary-headline").textContent = profile.headline || "Add a professional headline";
  $("#profile-summary-bio").textContent = profile.bio || "Your biography will appear here after you save a draft.";
  $("#profile-summary-availability").textContent = profile.availability || "Not recorded";
  const tags = [...(profile.skills || []).map((item) => `Skill · ${item}`), ...(profile.specializations || []).map((item) => `Specialization · ${item}`)];
  $("#profile-summary-tags").innerHTML = tags.length ? tags.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("") : `<span class="muted">No skills recorded yet.</span>`;
  const list = (items, keys) => items?.length ? items.map((item) => `<div class="profile-list-item"><strong>${escapeHtml(item[keys[0]] || "Entry")}</strong><span>${escapeHtml(keys.slice(1).map((key) => item[key]).filter(Boolean).join(" · "))}</span></div>`).join("") : `<p class="muted">No entries recorded yet.</p>`;
  $("#profile-summary-experience").innerHTML = list(profile.experience, ["title", "company", "start", "end"]);
  $("#profile-summary-education").innerHTML = list(profile.education, ["school", "degree", "field"]);
  $("#profile-summary-portfolio").innerHTML = list(profile.portfolio, ["title", "url"]);
  $("#profile-summary-evidence").innerHTML = list(profile.evidence_references, ["label", "classification", "status"]);
}
function setProfileForm(profile) {
  if (!profile) return;
  $("#profile-name").textContent = profile.display_name || "Professional profile";
  $("#profile-display-name").value = profile.display_name || "";
  $("#profile-headline").value = profile.headline || "";
  profileDraftTags = { skills: [...(profile.skills || [])], specializations: [...(profile.specializations || [])] };
  profileDraftLists = { experience: structuredClone(profile.experience || []), education: structuredClone(profile.education || []), portfolio: structuredClone(profile.portfolio || []), evidence_references: structuredClone(profile.evidence_references || []) };
  $("#profile-availability").value = profile.availability || "";
  $("#profile-bio").value = profile.bio || "";
  $("#profile-completeness").textContent = profileCompleteness(profile);
  $("#profile-updated").textContent = profile.updated_at ? dateLabel(profile.updated_at) : "Not saved";
  $("#profile-vetting-status").textContent = statusLabel(profile.application_status || "pending");
  $("#profile-vetting-status").className = `status-badge ${admissionTone(profile.application_status)}`;
  $("#profile-application-status").textContent = `Application ${statusLabel(profile.application_status || "pending")}`;
  renderProfileSummary(profile); renderTagEditor("skills"); renderTagEditor("specializations"); Object.keys(entryConfig).forEach(renderEntryEditor);
  $("#profile-summary-view").hidden = profileEditMode; $("#profile-edit-view").hidden = !profileEditMode;
}
async function loadProfessionalProfile() {
  if (role.value !== "professional") return;
  if (profileAccessOwner !== token()) {
    professionalProfile = null;
    setProfileForm({});
    $("#profile-completeness").textContent = "Start your application to edit your profile.";
    $("#edit-profile-button").disabled = true;
    return;
  }
  const owner = token();
  try {
    const profile = await request(`/api/professionals/${encodeURIComponent(actor.value.trim())}/profile`);
    if (token() !== owner) return;
    professionalProfile = profile;
    if (!profileEditMode) setProfileForm(profile);
  } catch (error) {
    if (token() !== owner) return;
    professionalProfile = null;
    if (error.status !== 404) showMessage(error.message, "error");
    if (!profileEditMode) setProfileForm({});
  }
}
async function saveProfessionalProfile(event) {
  event.preventDefault();
  const payload = {
    display_name: $("#profile-display-name").value.trim(), headline: $("#profile-headline").value.trim(), bio: $("#profile-bio").value.trim(),
    skills: profileDraftTags.skills, specializations: profileDraftTags.specializations,
    availability: $("#profile-availability").value.trim(), portfolio: profileDraftLists.portfolio,
    experience: profileDraftLists.experience, education: profileDraftLists.education, evidence_references: profileDraftLists.evidence_references,
    expected_version: professionalProfile?.version,
  };
  if (!payload.display_name) return showMessage("Add a display name before saving your profile.", "error");
  try { professionalProfile = await request(`/api/professionals/${encodeURIComponent(actor.value.trim())}/profile`, { method: "PUT", body: JSON.stringify(payload) }); $("#profile-save-status").textContent = "Saved as a reviewable draft."; profileEditMode = false; setProfileForm(professionalProfile); showMessage("Profile draft saved; admission remains a human decision.", "success"); }
  catch (error) { $("#profile-save-status").textContent = error.message; showMessage(error.message, "error"); }
}
function enterProfileEdit() { profileEditMode = true; if (professionalProfile) setProfileForm(professionalProfile); else { profileDraftLists = { experience: [], education: [], portfolio: [], evidence_references: [] }; profileDraftTags = { skills: [], specializations: [] }; $("#profile-summary-view").hidden = true; $("#profile-edit-view").hidden = false; Object.keys(entryConfig).forEach(renderEntryEditor); renderTagEditor("skills"); renderTagEditor("specializations"); } }
function cancelProfileEdit() { profileEditMode = false; setProfileForm(professionalProfile || {}); }
function addProfileTag(type) { const input = $(`#profile-${type}`); const value = input?.value.trim(); if (!value) return; if (!profileDraftTags[type].includes(value)) profileDraftTags[type].push(value); input.value = ""; renderTagEditor(type); }
function addProfileEntry(type) { profileDraftLists[type].push({}); renderEntryEditor(type); const host = $(`#profile-${type === "evidence_references" ? "evidence" : type}-entries`); host?.querySelector(".repeatable-row:last-child input")?.focus(); }
function renderReviews() { $("#reviews-list").innerHTML = emptyState("No review feedback yet", "Independent review decisions and requested revisions will appear after a deliverable is submitted."); }

// Existing admin lifecycle controls remain available in the developer harness.
async function createOrganization() { const name = $("#organization-name").value.trim(); if (!name) return showMessage("Enter an organization name first.", "error"); try { const item = await request("/api/organizations", { method: "POST", body: JSON.stringify({ name }) }); $("#engagement-organization").value = item.id; showMessage(`Organization created: ${item.id}`, "success"); } catch (error) { showMessage(error.message, "error"); } }
async function createEngagement() { const body = { organization_id: $("#engagement-organization").value.trim(), name: $("#engagement-name").value.trim(), objective: $("#engagement-objective").value.trim() }; if (Object.values(body).some((value) => !value)) return showMessage("Complete all engagement fields first.", "error"); try { const item = await request("/api/engagements", { method: "POST", body: JSON.stringify(body) }); $("#project-engagement").value = item.id; $("#engagement-id").value = item.id; showMessage(`Engagement created: ${item.id}`, "success"); } catch (error) { showMessage(error.message, "error"); } }
async function createProject() { const body = { engagement_id: $("#project-engagement").value.trim(), name: $("#project-name").value.trim() }; if (Object.values(body).some((value) => !value)) return showMessage("Complete the engagement and project name first.", "error"); try { const item = await request("/api/projects", { method: "POST", body: JSON.stringify(body) }); $("#project-id").value = item.id; showMessage(`Project created: ${item.id}`, "success"); } catch (error) { showMessage(error.message, "error"); } }
async function createWorkPackage() { const body = { project_id: $("#project-id").value.trim(), title: $("#package-title").value.trim(), acceptance_criteria: $("#package-criteria").value.trim().split(",").map((item) => item.trim()).filter(Boolean) }; if (!body.project_id || !body.title || !body.acceptance_criteria.length) return showMessage("Complete the project, title and acceptance criteria first.", "error"); try { const item = await request("/api/work-packages", { method: "POST", body: JSON.stringify(body) }); $("#invite-package").value = item.id; $("#package-id").value = item.id; showMessage(`Work package created: ${item.id}`, "success"); } catch (error) { showMessage(error.message, "error"); } }
async function inviteProfessional() { try { const item = await request(`/api/work-packages/${encodeURIComponent($("#invite-package").value.trim())}/assignments`, { method: "POST", body: JSON.stringify({ professional_id: $("#invite-professional").value.trim() }) }); $("#assignment-id").value = item.id; showMessage(`Invitation created: ${item.id}`, "success"); } catch (error) { showMessage(error.message, "error"); } }
async function completeProject() { try { await request(`/api/projects/${encodeURIComponent($("#complete-project-id").value.trim())}/complete`, { method: "POST", body: "{}" }); showMessage("Project completed after client acceptance.", "success"); } catch (error) { showMessage(error.message, "error"); } }

document.querySelectorAll("[data-view]").forEach((link) => link.addEventListener("click", (event) => { event.preventDefault(); requestedProfessionalView = ""; const view = link.dataset.view; navigate(view); }));
document.querySelectorAll("[data-view-target]").forEach((button) => button.addEventListener("click", () => navigate(button.dataset.viewTarget)));
window.addEventListener("hashchange", () => navigate(location.hash.slice(1) || "overview"));
function setMenu(open) {
  $("#mobile-menu").setAttribute("aria-expanded", String(open));
  $(".sidebar").classList.toggle("menu-open", open);
}
$("#mobile-menu").addEventListener("click", () => setMenu($("#mobile-menu").getAttribute("aria-expanded") !== "true"));
$(".sidebar").addEventListener("keydown", event => {
  if (event.key === "Escape" && $(".sidebar").classList.contains("menu-open")) {
    setMenu(false);
    $("#mobile-menu").focus();
  }
});
$(".skip-link").addEventListener("click", event => {
  event.preventDefault();
  $("#workspace-content").focus();
});
$("#refresh").addEventListener("click", refresh); $("#load-assignments").addEventListener("click", loadAssignments); $("#role").addEventListener("change", () => { requestedProfessionalView = "overview"; syncRole(); refresh(); });
$("#assignment-picker").addEventListener("change", event => {
  $("#package-id").value = event.target.value;
  $("#submit-deliverable").disabled = !event.target.value;
  loadSelectedDeliverables();
});
$("#submit-application").addEventListener("click", submitApplication); $("#submit-deliverable").addEventListener("click", submitDeliverable); $("#load-deliverables").addEventListener("click", loadSelectedDeliverables); $("#accept-deliverable").addEventListener("click", acceptDeliverable); $("#review-deliverable").addEventListener("click", reviewDeliverable); $("#professional-profile-form").addEventListener("submit", saveProfessionalProfile);
$("#edit-profile-button")?.addEventListener("click", enterProfileEdit); $("#cancel-profile-edit")?.addEventListener("click", cancelProfileEdit);
$("#add-profile-skill")?.addEventListener("click", () => addProfileTag("skills")); $("#add-profile-specialization")?.addEventListener("click", () => addProfileTag("specializations"));
$("#add-profile-experience")?.addEventListener("click", () => addProfileEntry("experience")); $("#add-profile-education")?.addEventListener("click", () => addProfileEntry("education")); $("#add-profile-portfolio")?.addEventListener("click", () => addProfileEntry("portfolio")); $("#add-profile-evidence")?.addEventListener("click", () => addProfileEntry("evidence_references"));
$("#opportunity-filter").addEventListener("change", renderOpportunities); $("#opportunity-search").addEventListener("input", renderOpportunities);
$("#client-refresh").addEventListener("click", loadClientOverview); $("#client-project-search").addEventListener("input", renderClientProjects); $("#client-project-status").addEventListener("change", renderClientProjects);
$("#client-message-project").addEventListener("change", (event) => loadClientOperations(event.target.value)); $("#client-message-form").addEventListener("submit", sendClientMessage);
$("#create-organization").addEventListener("click", createOrganization); $("#create-engagement").addEventListener("click", createEngagement); $("#create-project").addEventListener("click", createProject); $("#create-package").addEventListener("click", createWorkPackage); $("#invite-professional-button").addEventListener("click", inviteProfessional); $("#accept-assignment").addEventListener("click", () => decideAssignment($("#assignment-id").value.trim(), "accept")); $("#decline-assignment").addEventListener("click", () => decideAssignment($("#assignment-id").value.trim(), "decline")); $("#complete-project").addEventListener("click", completeProject);


// Mission Control is an admin-only read model over the same authorized API.
let adminData = null;
const adminMetric = (label, value, tone, note, view) => `<a href="#${view}" class="metric-card"><div class="metric-top"><span class="metric-label">${escapeHtml(label)}</span><span class="metric-icon ${tone}">●</span></div><div class="metric-value">${escapeHtml(value)}</div><div class="metric-note">${escapeHtml(note)}</div></a>`;
function adminStatus(status) { return `<span class="status-badge ${statusClass(status)}">${escapeHtml(statusLabel(status))}</span>`; }
function adminEmpty(text) { return `<div class="empty-panel inline-empty"><span class="empty-icon">◇</span><h2>No records</h2><p>${escapeHtml(text)}</p></div>`; }
function renderAdminOverview() {
  if (!adminData) return;
  const m = adminData.metrics || {};
  $("#admin-metric-grid").innerHTML = [
    adminMetric("Active engagements", m.active_engagements || 0, "blue", "Authorized client work", "admin-engagements"),
    adminMetric("Awaiting review", m.awaiting_review || 0, "purple", "Deliverables under review", "admin-quality"),
    adminMetric("Approved professionals", (adminData.professionals || []).filter((item) => item.status === "approved").length, "green", "Approved admission records", "admin-professionals"),
    adminMetric("AI outputs awaiting review", m.ai_pending_approval || 0, "orange", "Human decision required", "admin-ai"),
  ].join("");
  const stages = [
    ["Planning", (adminData.projects || []).filter((item) => item.status === "active" && item.work_package_count === 0)],
    ["Active delivery", (adminData.projects || []).filter((item) => item.status === "active" && item.work_package_count > 0 && !item.awaiting_review)],
    ["Internal QA", (adminData.projects || []).filter((item) => item.awaiting_review > 0)],
    ["Completed", (adminData.projects || []).filter((item) => item.status === "completed")],
  ];
  $("#admin-pipeline").innerHTML = stages.map(([label, items]) => {
    const projects = items.slice(0, 3).map(item => `<li><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.organization_name || "Client unavailable")}</small></li>`).join("");
    const more = items.length > 3 ? `<a class="pipeline-more" href="#admin-projects">View all ${items.length} projects</a>` : "";
    return `<div class="delivery-stage"><div class="stage-label"><span>${label}</span><b>${items.length}</b></div>${projects ? `<ul>${projects}</ul>${more}` : ""}</div>`;
  }).join("");
  const attention = [];
  if (m.awaiting_review) attention.push([`${m.awaiting_review} deliverable${m.awaiting_review === 1 ? "" : "s"} awaiting review`, "Quality queue", "admin-quality"]);
  if (m.pending_applications) attention.push([`${m.pending_applications} professional application${m.pending_applications === 1 ? "" : "s"}`, "Pending vetting", "admin-applications"]);
  if (m.client_approvals_pending) attention.push([`${m.client_approvals_pending} client approval${m.client_approvals_pending === 1 ? "" : "s"}`, "Approved version presented", "admin-approvals"]);
  if (m.ai_pending_approval) attention.push([`${m.ai_pending_approval} AI output${m.ai_pending_approval === 1 ? "" : "s"} awaiting review`, "Execution review required", "admin-ai"]);
  if (m.ai_failed) attention.push([`${m.ai_failed} failed AI run${m.ai_failed === 1 ? "" : "s"}`, "Execution recovery", "admin-ai"]);
  $("#admin-attention-count").textContent = attention.length;
  $("#admin-attention").innerHTML = attention.length ? attention.map(([title, note, view]) => `<a class="attention-item" href="#${view}" data-view="${view}"><span class="attention-icon">!</span><span><strong>${escapeHtml(title)}</strong><small>${escapeHtml(note)}</small></span><span>›</span></a>`).join("") : adminEmpty("There are no pending approvals or blocked actions.");
  $("#admin-projects-table").innerHTML = adminData.projects?.length ? `<table><thead><tr><th>Project</th><th>Client</th><th>Stage</th><th>Work packages</th><th>Status</th></tr></thead><tbody>${adminData.projects.slice(0, 8).map((item) => `<tr><td><div class="assignment-name"><span class="assignment-mark">▣</span><div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.engagement_name || "Engagement")}</small></div></div></td><td>${escapeHtml(item.organization_name || "—")}</td><td>${item.awaiting_review ? "Internal QA" : item.status === "completed" ? "Completed" : item.work_package_count ? "Active delivery" : "Planning"}</td><td>${item.work_package_count}</td><td>${adminStatus(item.status)}</td></tr>`).join("")}</tbody></table>` : adminEmpty("Projects will appear after an authorized engagement is created.");
  const runs = adminData.ai_runs || [];
  $("#admin-ai-summary").innerHTML = `<div class="summary-row"><span>Queued or running</span><strong>${runs.filter((item) => ["queued", "running"].includes(item.status)).length}</strong></div><div class="summary-row"><span>Pending approval</span><strong>${m.ai_pending_approval || 0}</strong></div><div class="summary-row"><span>Failed</span><strong>${m.ai_failed || 0}</strong></div><div class="summary-row"><span>Recorded spend</span><strong>${runs.length ? `${runs.reduce((sum, item) => sum + (item.spent_cents || 0), 0)} cents` : "Not available"}</strong></div>`;
  $("#admin-audit-summary").innerHTML = (adminData.audit || []).slice(0, 5).map((item) => `<div class="summary-row"><span>${escapeHtml(item.action)}</span><small>${escapeHtml(item.actor_id)} · ${escapeHtml(item.resource_type)}</small></div>`).join("") || `<p class="muted">No audit activity recorded.</p>`;
  document.querySelectorAll("#admin-attention [data-view]").forEach((link) => link.addEventListener("click", (event) => { event.preventDefault(); navigate(link.dataset.view); }));
}
function legacyRenderAdminLists(view) {
  if (!adminData) return;
  const cards = (items, render) => items?.length ? items.map(render).join("") : adminEmpty("No authorized records are available yet.");
  if (view === "admin-clients") $("#admin-client-list").innerHTML = cards(adminData.organizations, (item) => `<article class="panel admin-card"><div class="eyebrow">CLIENT ORGANIZATION</div><h2>${escapeHtml(item.name)}</h2><p>Authorized relationship and engagement context.</p><div class="card-footer"><small>Created ${escapeHtml(dateLabel(item.created_at))}</small><span class="status-badge success">Active record</span></div></article>`);
  if (view === "admin-projects") $("#admin-project-list").innerHTML = cards(adminData.projects, (item) => `<article class="panel admin-card"><div class="eyebrow">${escapeHtml(item.organization_name || "CLIENT")}</div><h2>${escapeHtml(item.name)}</h2><p>${escapeHtml(item.engagement_name || "Engagement")}</p><div class="assignment-meta"><div><span>Stage</span><strong>${item.awaiting_review ? "Internal QA" : item.work_package_count ? "Active delivery" : "Planning"}</strong></div><div><span>Packages</span><strong>${item.work_package_count}</strong></div><div><span>Status</span><strong>${adminStatus(item.status)}</strong></div></div></article>`);
  if (view === "admin-professionals") $("#admin-professional-list").innerHTML = cards(adminData.professionals, (item) => `<article class="panel admin-card"><div class="eyebrow">PROFESSIONAL RECORD</div><h2>${escapeHtml(item.display_name || "Professional application")}</h2><p>Verified admission status and scoped delivery access.</p><div class="card-footer"><small>${item.decided_by ? `Decided by ${escapeHtml(item.decided_by)}` : "Awaiting decision"}</small>${adminStatus(item.status)}</div></article>`);
  if (view === "admin-opportunities") $("#admin-opportunity-list").innerHTML = cards(adminData.opportunities, (item) => `<article class="panel admin-card"><div class="eyebrow">${escapeHtml(item.specialization || "STAFFING")}</div><h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.summary)}</p><div class="chip-list">${(item.skills || []).map((skill) => `<span class="chip">${escapeHtml(skill)}</span>`).join("")}</div><div class="card-footer"><small>Sanitized professional-network listing</small>${adminStatus(item.status)}</div></article>`);
  if (view === "admin-ai") $("#admin-ai-list").innerHTML = cards(adminData.ai_runs, (item) => `<article class="panel admin-card"><div class="eyebrow">${escapeHtml(item.agent_version || "AGENT")}</div><h2>${escapeHtml(item.work_package_title || "Bounded execution")}</h2><p>${escapeHtml(item.project_name || item.engagement_name || "Authorized work package")}</p><div class="assignment-meta"><div><span>Policy</span><strong>${escapeHtml(item.policy_version || "—")}</strong></div><div><span>Budget</span><strong>${item.budget_cents} cents</strong></div><div><span>Status</span><strong>${adminStatus(item.status)}</strong></div></div></article>`);
  if (view === "admin-quality") { const items = (adminData.deliverables || []).filter((item) => item.status === "under_review"); $("#admin-quality-list").innerHTML = cards(items, (item) => `<article class="panel admin-card"><div class="eyebrow">INDEPENDENT REVIEW</div><h2>${escapeHtml(item.title)} · v${item.version}</h2><p>${escapeHtml(item.project_name || "Project")}</p><div class="card-footer"><small>${escapeHtml(item.organization_name || "Client")}</small>${adminStatus(item.status)}</div></article>`); }
  if (view === "admin-approvals") { const items = (adminData.deliverables || []).filter((item) => item.status === "approved"); $("#admin-approval-list").innerHTML = cards(items, (item) => `<article class="panel admin-card"><div class="eyebrow">CLIENT REVIEW</div><h2>${escapeHtml(item.title)} · v${item.version}</h2><p>${escapeHtml(item.project_name || "Project")}</p><div class="card-footer"><small>Awaiting authorized client decision</small>${adminStatus(item.status)}</div></article>`); }
}
function ensureAdminDrawer() {
  if ($("#admin-detail-drawer")) return;
  document.body.insertAdjacentHTML("beforeend", `<dialog id="admin-detail-drawer" class="admin-detail-drawer" aria-label="Admin record details" hidden><button id="admin-drawer-close" class="drawer-close" aria-label="Close details">×</button><div id="admin-drawer-content"></div></dialog>`);
  const drawer = $("#admin-detail-drawer");
  $("#admin-drawer-close").addEventListener("click", () => drawer.close());
  drawer.addEventListener("close", () => { drawer.hidden = true; });
}
function openAdminDrawer() {
  const drawer = $("#admin-detail-drawer");
  drawer.hidden = false;
  if (!drawer.open) drawer.showModal();
}
function showAdminDetail(type, id) { ensureAdminDrawer(); const source = type === "project" ? adminData.projects : type === "engagement" ? adminData.engagements : type === "ai" ? adminData.ai_runs : adminData.applications; const item = source.find((record) => record.id === id || record.professional_id === id); if (!item) return; $("#admin-drawer-content").innerHTML = `<p class="eyebrow">${escapeHtml(type.toUpperCase())} DETAIL</p><h2>${escapeHtml(item.name || item.title || item.professional_id || item.work_package_title || "Record")}</h2><p class="muted">${escapeHtml(item.objective || item.summary || item.project_name || "Authorized record from the Studio read model.")}</p><dl class="drawer-details">${Object.entries(item).filter(([key]) => !["id", "content", "metadata"].includes(key)).slice(0, 10).map(([key, value]) => `<div><dt>${escapeHtml(statusLabel(key))}</dt><dd>${escapeHtml(typeof value === "object" ? JSON.stringify(value) : value ?? "—")}</dd></div>`).join("")}</dl>`; openAdminDrawer(); }
async function openAdmissionReview(professionalId) {
  ensureAdminDrawer();
  try {
    const application = await request(`/api/professionals/${encodeURIComponent(professionalId)}/application`);
    const profile = await request(`/api/professionals/${encodeURIComponent(professionalId)}/profile`).catch((error) => error.message.toLowerCase().includes("profile has not been started") ? { display_name: professionalId, headline: "Profile draft not started", bio: "The applicant has not started a profile draft yet.", skills: [], evidence_references: [] } : Promise.reject(error));
    $("#admin-drawer-content").innerHTML = `<p class="eyebrow">ADMISSION REVIEW</p><h2>${escapeHtml(profile.display_name || professionalId)}</h2><p class="muted">${escapeHtml(profile.headline || "Professional profile")}</p><div class="review-profile-summary"><div><span class="detail-label">Current admission</span><span class="status-badge ${admissionTone(application.status)}">${escapeHtml(statusLabel(application.status))}</span></div><div><span class="detail-label">Profile completeness</span><strong>${escapeHtml(profileCompleteness(profile))}</strong></div><div><span class="detail-label">Skills</span><strong>${escapeHtml((profile.skills || []).join(", ") || "Not recorded")}</strong></div><div><span class="detail-label">Evidence</span><strong>${escapeHtml((profile.evidence_references || []).length ? `${profile.evidence_references.length} reference(s)` : "None recorded")}</strong></div></div><p>${escapeHtml(profile.bio || "No biography recorded.")}</p><form id="admission-review-form" class="review-form"><label for="admission-review-status">Review state<select id="admission-review-status"><option value="under_review">Under review</option><option value="assessment">Assessment</option><option value="approved">Approved</option><option value="declined">Declined</option><option value="revoked">Revoked</option></select></label><label for="admission-review-reason">Decision reason<textarea id="admission-review-reason" rows="3" placeholder="Record the evidence-based reason for this review."></textarea></label><label for="admission-review-next">Next action<input id="admission-review-next" placeholder="What should happen next?" /></label><label for="admission-review-missing">Missing information<textarea id="admission-review-missing" rows="2" placeholder="One item per line"></textarea></label><button class="primary-button" type="submit">Save review decision</button><span id="admission-review-status-message" class="inline-status" role="status"></span></form>`;
    const confirmation = document.createElement("label");
    confirmation.className = "qualification-check";
    confirmation.innerHTML = '<input id="confirm-qualifications" type="checkbox"> I reviewed the current profile and evidence and confirm the applicant is qualified.';
    $("#admission-review-form button[type=submit]").before(confirmation);
    const details = document.createElement("dl");
    details.className = "drawer-details";
    for (const [label, value] of [
      ["Specializations", profile.specializations?.join(", ")],
      ["Experience", profile.experience?.map(item => [item.title, item.company].filter(Boolean).join(" · ")).join("; ")],
      ["Education", profile.education?.map(item => [item.degree, item.school].filter(Boolean).join(" · ")).join("; ")],
      ["Portfolio", profile.portfolio?.map(item => item.title).join(", ")],
      ["Availability", profile.availability],
      ["Outstanding assessments", application.assessment_requests?.map(item => item.title).join(", ")],
    ]) {
      const term = document.createElement("dt");
      term.textContent = label;
      const definition = document.createElement("dd");
      definition.textContent = value || "None recorded";
      details.append(term, definition);
    }
    $("#admission-review-form").before(details);
    const evidence = document.createElement("ul");
    for (const ref of profile.evidence_references || []) {
      const entry = document.createElement("li");
      entry.textContent = [ref.label, ref.reference].filter(Boolean).join(" · ");
      evidence.append(entry);
    }
    $("#admission-review-form").before(evidence);
    openAdminDrawer();
    $("#admission-review-status").value = ["pending", "submitted", "under_review", "assessment"].includes(application.status) ? "under_review" : application.status;
    $("#admission-review-reason").value = application.decision_reason || ""; $("#admission-review-next").value = application.next_action || ""; $("#admission-review-missing").value = (application.missing_information || []).join("\n");
    $("#admission-review-form").addEventListener("submit", async (event) => { event.preventDefault(); const status = $("#admission-review-status").value; const reason = $("#admission-review-reason").value.trim(); if (["approved", "declined", "revoked"].includes(status) && !reason) { $("#admission-review-status-message").textContent = "A decision reason is required."; return; } try { await request(`/api/professionals/${encodeURIComponent(professionalId)}/review`, { method: "POST", body: JSON.stringify({ status, reason, reviewed_profile_version: status === "approved" && $("#confirm-qualifications").checked ? profile.version : null, next_action: $("#admission-review-next").value.trim(), missing_information: $("#admission-review-missing").value.split("\n").map((item) => item.trim()).filter(Boolean), assessment_requests: [] }) }); $("#admission-review-status-message").textContent = "Review decision saved and audited."; showMessage("Admission review saved.", "success"); await loadAdminOverview(); } catch (error) { $("#admission-review-status-message").textContent = error.message; } });
  } catch (error) { showMessage(error.message, "error"); }
}
async function decideAdminAI(runId, decision) { try { await request(`/api/ai-runs/${encodeURIComponent(runId)}/decision`, { method: "POST", body: JSON.stringify({ decision, comment: "Mission Control decision recorded by an authorized admin." }) }); showMessage(`AI artifact ${decision}.`, "success"); await loadAdminOverview(); } catch (error) { showMessage(error.message, "error"); } }
function renderCollection(browser) {
  const kind = browser.dataset.collection;
  const search = browser.querySelector("input");
  const sort = browser.querySelector("select");
  const host = browser.querySelector(".record-list");
  const rows = adminData[kind] || [];
  function title(row) {
    if (kind === "applications") return row.display_name || "Professional application";
    if (kind === "audit") return statusLabel(row.action);
    return row.name;
  }
  function render() {
    const query = search.value.trim().toLowerCase();
    const filtered = rows.filter(row => [title(row), row.status, row.organization_name, row.actor_id,
      row.created_at, row.resource_id, row.organization_id, row.action, row.professional_id]
      .some(value => String(value || "").toLowerCase().includes(query)));
    filtered.sort((a, b) => sort.value === "label" ? title(a).localeCompare(title(b))
      : String(b.created_at).localeCompare(String(a.created_at)));
    const pageSize = 10;
    const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
    const page = Math.max(0, Math.min(Number(browser.dataset.page || 0), pages - 1));
    browser.dataset.page = page;
    host.replaceChildren();
    for (const row of filtered.slice(page * pageSize, (page + 1) * pageSize)) {
      const record = document.createElement("article");
      record.className = "business-row";
      const summary = document.createElement("div");
      const heading = document.createElement("h2");
      heading.textContent = title(row);
      const note = document.createElement("p");
      note.textContent = [row.organization_name || row.actor_id || row.next_action, dateLabel(row.created_at)].filter(Boolean).join(" · ");
      summary.append(heading, note);
      record.append(summary);
      if (kind === "audit") {
        const details = document.createElement("details");
        const toggle = document.createElement("summary");
        toggle.textContent = "Event details";
        const data = document.createElement("pre");
        data.textContent = JSON.stringify(row, null, 2);
        details.append(toggle, data);
        record.append(details);
      } else {
        record.insertAdjacentHTML("beforeend", adminStatus(row.status));
        const action = document.createElement("button");
        action.className = "secondary-button";
        if (kind === "applications") {
          action.textContent = "Review application";
          action.classList.add("review-admission-button");
          action.dataset.professionalId = row.professional_id;
          action.onclick = () => openAdmissionReview(row.professional_id);
        } else {
          action.textContent = "View engagement";
          action.onclick = () => showAdminDetail("engagement", row.id);
        }
        record.append(action);
      }
      host.append(record);
    }
    if (!filtered.length) host.innerHTML = adminEmpty(query ? "No matches. Try a different search." : "No records available.");
    browser.querySelector("[aria-live]").textContent = filtered.length ? `${page * pageSize + 1}–${Math.min(filtered.length, (page + 1) * pageSize)} of ${filtered.length}` : "0 records";
    for (const button of browser.querySelectorAll("[data-step]")) {
      const step = Number(button.dataset.step);
      button.disabled = page + step < 0 || page + step >= pages;
      button.onclick = () => { browser.dataset.page = page + step; render(); };
    }
  }
  search.oninput = sort.onchange = () => { browser.dataset.page = 0; render(); };
  render();
}

function renderAdminLists(view) {
  legacyRenderAdminLists(view);
  const browser = document.getElementById(view + "-view")?.querySelector(".record-browser");
  if (browser) renderCollection(browser);
  if (view === "admin-projects") {
    const host = $("#admin-project-list");
    if (!$("#admin-project-toolbar")) host.insertAdjacentHTML("beforebegin", `<div id="admin-project-toolbar" class="admin-toolbar"><input id="admin-project-search" placeholder="Search projects or clients" aria-label="Search projects or clients" /><select id="admin-project-status" aria-label="Filter project status"><option value="">All statuses</option><option value="active">Active</option><option value="completed">Completed</option></select><select id="admin-project-sort" aria-label="Sort projects"><option value="newest">Newest</option><option value="name">Name</option><option value="client">Client</option></select><button id="admin-project-prev" class="secondary-button">Previous</button><button id="admin-project-next" class="secondary-button">Next</button><span id="admin-project-page" class="muted"></span></div>`);
    let page = 0; const pageSize = 9; const renderPage = () => { const query = $("#admin-project-search").value.trim().toLowerCase(); const status = $("#admin-project-status").value; const sort = $("#admin-project-sort").value; const filtered = (adminData.projects || []).filter((item) => (!status || item.status === status) && (!query || `${item.name} ${item.organization_name} ${item.engagement_name}`.toLowerCase().includes(query))); const ordered = [...filtered].sort((a, b) => sort === "name" ? String(a.name || "").localeCompare(String(b.name || "")) : sort === "client" ? String(a.organization_name || "").localeCompare(String(b.organization_name || "")) : String(b.created_at || "").localeCompare(String(a.created_at || ""))); const pages = Math.max(1, Math.ceil(ordered.length / pageSize)); page = Math.min(page, pages - 1); host.innerHTML = ordered.slice(page * pageSize, page * pageSize + pageSize).map((item) => `<article class="panel admin-card"><div class="eyebrow">${escapeHtml(item.organization_name || "CLIENT")}</div><h2>${escapeHtml(item.name)}</h2><p>${escapeHtml(item.engagement_name || "Engagement")}</p><div class="assignment-meta"><div><span>Stage</span><strong>${item.status === "completed" ? "Completed" : item.awaiting_review ? "Internal QA" : item.work_package_count ? "Active delivery" : "Planning"}</strong></div><div><span>Packages</span><strong>${item.work_package_count}</strong></div><div><span>Status</span><strong>${adminStatus(item.status)}</strong></div></div><div class="card-footer"><small>Human-readable project record</small><button class="secondary-button admin-detail-button" data-admin-detail="project" data-record-id="${escapeHtml(item.id)}">Open details</button></div></article>`).join("") || adminEmpty("No projects match the current filters."); $("#admin-project-page").textContent = `${ordered.length ? page + 1 : 0} / ${pages}`; $("#admin-project-prev").disabled = page === 0; $("#admin-project-next").disabled = page >= pages - 1; $$(".admin-detail-button").forEach((button) => button.addEventListener("click", () => showAdminDetail(button.dataset.adminDetail, button.dataset.recordId))); }; $("#admin-project-search").oninput = () => { page = 0; renderPage(); }; $("#admin-project-status").onchange = () => { page = 0; renderPage(); }; $("#admin-project-sort").onchange = () => { page = 0; renderPage(); }; $("#admin-project-prev").onclick = () => { page -= 1; renderPage(); }; $("#admin-project-next").onclick = () => { page += 1; renderPage(); }; renderPage();
  }
  if (view === "admin-ai") { const host = $("#admin-ai-list"); host.querySelectorAll(".admin-card").forEach((card, index) => { const item = adminData.ai_runs[index]; if (!item) return; if (item.artifact_status === "pending_review") card.insertAdjacentHTML("beforeend", `<div class="card-footer"><button class="primary-button ai-approve-button" data-run-id="${escapeHtml(item.id)}">Approve artifact</button><button class="secondary-button ai-reject-button" data-run-id="${escapeHtml(item.id)}">Reject</button></div>`); else card.insertAdjacentHTML("beforeend", `<div class="card-footer"><small>Artifact ${escapeHtml(item.artifact_status || "not available")}</small><button class="secondary-button admin-detail-button" data-admin-detail="ai" data-record-id="${escapeHtml(item.id)}">Open run</button></div>`); }); $$(".ai-approve-button").forEach((button) => button.addEventListener("click", () => decideAdminAI(button.dataset.runId, "approved"))); $$(".ai-reject-button").forEach((button) => button.addEventListener("click", () => decideAdminAI(button.dataset.runId, "rejected"))); }
}
async function loadAdminOverview() { try { adminData = await request("/api/admin/overview"); renderAdminOverview(); renderAdminLists(location.hash.slice(1) || "admin-overview"); } catch (error) { showMessage(error.message, "error"); } }

function clientStatus(status) {
  const tone = status === "completed" || status === "accepted" ? "success" : status === "approved" ? "info" : status === "revision_requested" ? "warning" : "neutral";
  return `<span class="status-badge ${tone}">${escapeHtml(statusLabel(status))}</span>`;
}
function clientUnavailable(title, text) { return `<div class="client-unavailable"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(text)}</span></div>`; }
function clientProjectCard(project) {
  const packages = project.work_packages || [];
  const versions = packages.flatMap((item) => item.deliverables || []);
  const latest = versions.length ? versions[versions.length - 1] : null;
  const progress = project.status === "completed" ? 100 : null;
  const progressLabel = progress === 100 ? "Complete" : packages.length ? `${packages.length} work package${packages.length === 1 ? "" : "s"} recorded` : "Progress not recorded";
  return `<article class="panel client-project-card"><div class="client-project-heading"><div><p class="eyebrow">${escapeHtml(project.organization_name || "CLIENT ORGANIZATION")}</p><h2>${escapeHtml(project.name)}</h2><p>${escapeHtml(project.engagement_name || "Authorized engagement")}</p></div>${clientStatus(project.status)}</div><div class="client-progress"><div class="client-progress-label"><span>Delivery progress</span><strong>${escapeHtml(progressLabel)}</strong></div>${progress === 100 ? `<div class="progress-track" aria-label="Project complete"><span style="width:100%"></span></div>` : `<p class="muted progress-unavailable">No percentage is published until a verified milestone record exists.</p>`}</div><div class="client-package-list">${packages.length ? packages.map((item) => `<div class="client-package"><div><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml((item.acceptance_criteria || []).join(" · ") || "Acceptance criteria recorded")}</small></div><span>${item.deliverables?.length ? clientStatus(item.deliverables[item.deliverables.length - 1].status) : "<span class=\"status-badge neutral\">In progress</span>"}</span></div>`).join("") : `<p class="muted">No work packages have been published for this project.</p>`}</div><div class="card-footer"><small>${latest ? `Latest deliverable v${latest.version}` : "No deliverable submitted"}</small><button class="secondary-button client-project-open" data-project-id="${escapeHtml(project.id)}">View project</button></div></article>`;
}
function renderClientMetrics() {
  const m = clientData?.metrics || {};
  $("#client-metric-grid").innerHTML = [
    adminMetric("Active projects", m.active_projects || 0, "blue", "Authorized delivery work", "client-projects"),
    adminMetric("Completed projects", m.completed_projects || 0, "green", "Client-accepted outcomes", "client-projects"),
    adminMetric("Deliverables to review", m.deliverables_for_review || 0, "orange", "Approved by Data Fellows", "client-deliverables"),
    adminMetric("Accepted deliverables", m.accepted_deliverables || 0, "purple", "Your recorded decisions", "client-deliverables"),
  ].join("");
}
function renderClientOverview() {
  if (!clientData) return;
  renderClientMetrics();
  const projects = clientData.projects || [];
  $("#client-project-list").innerHTML = projects.length ? projects.slice(0, 4).map(clientProjectCard).join("") : emptyState("No projects yet", "Authorized engagements will appear here when Data Fellows starts delivery.");
  const pending = (clientData.deliverables || []).filter((item) => item.status === "approved");
  $("#client-attention-list").innerHTML = pending.length ? pending.slice(0, 4).map((item) => `<div class="summary-row"><span><strong>${escapeHtml(item.title)}</strong><small>Version ${item.version} ready for your review</small></span><button class="text-button client-review-link" data-deliverable-id="${escapeHtml(item.id)}">Review →</button></div>`).join("") : `<p class="muted">No approved deliverables need your attention.</p>`;
  $("#client-outcomes-summary").innerHTML = [clientUnavailable("Project documents", "No document records are linked to this workspace yet."), clientUnavailable("Billing", "Verified invoice and payment events are not available."), clientUnavailable("Operational outcomes", "Outcome measures appear after approved records are connected.")].join("");
  $$(".client-project-open").forEach((button) => button.addEventListener("click", () => { navigate("client-projects"); const target = $("#client-projects-list").querySelector(`[data-project-id=\"${CSS.escape(button.dataset.projectId)}\"]`); target?.scrollIntoView({ behavior: "smooth", block: "center" }); }));
  $$(".client-review-link").forEach((button) => button.addEventListener("click", () => { navigate("client-deliverables"); document.querySelector(`[data-deliverable-id=\"${CSS.escape(button.dataset.deliverableId)}\"]`)?.scrollIntoView({ behavior: "smooth", block: "center" }); }));
}
function renderClientProjects() {
  const query = $("#client-project-search").value.trim().toLowerCase();
  const status = $("#client-project-status").value;
  const visible = (clientData?.projects || []).filter((item) => (!status || item.status === status) && (!query || `${item.name} ${item.organization_name} ${item.engagement_name}`.toLowerCase().includes(query)));
  $("#client-projects-list").innerHTML = visible.length ? visible.map(clientProjectCard).join("") : emptyState("No projects match", "Try a different search or status filter.");
  $$(".client-project-open").forEach((button) => button.addEventListener("click", () => showMessage("Project details are shown in the delivery card. Scoped documents will appear when available.", "info")));
}
function renderClientDeliverables() {
  const items = clientData?.deliverables || [];
  $("#client-deliverables-list").innerHTML = items.length ? items.map((item) => `<article class="panel client-deliverable-card" data-deliverable-id="${escapeHtml(item.id)}"><div class="panel-heading"><div><p class="eyebrow">VERSIONED WORK PRODUCT</p><h2>${escapeHtml(item.title)}</h2><p>Version ${item.version} · Approved by Data Fellows</p></div>${clientStatus(item.status)}</div><div class="client-deliverable-content">${escapeHtml(item.content)}</div><div class="card-footer"><small>Immutable version record · decision remains auditable</small><div class="client-action-row">${item.status === "approved" ? `<button class="secondary-button client-revision-button" data-deliverable-id="${escapeHtml(item.id)}">Request revision</button><button class="primary-button client-accept-button" data-deliverable-id="${escapeHtml(item.id)}">Accept deliverable</button>` : `<span class="muted">Accepted on record</span>`}</div></div><div class="client-revision-form" data-revision-for="${escapeHtml(item.id)}" hidden><label>Revision request<textarea rows="2" placeholder="Tell Data Fellows what needs changing"></textarea></label><button class="primary-button submit-client-revision" data-deliverable-id="${escapeHtml(item.id)}">Send request</button></div></article>`).join("") : emptyState("No deliverables ready for review", "Internally approved versions will appear here before client acceptance.");
  $$(".client-accept-button").forEach((button) => button.addEventListener("click", () => acceptClientDeliverable(button.dataset.deliverableId)));
  $$(".client-revision-button").forEach((button) => button.addEventListener("click", () => { const form = document.querySelector(`[data-revision-for=\"${CSS.escape(button.dataset.deliverableId)}\"]`); if (form) form.hidden = false; }));
  $$(".submit-client-revision").forEach((button) => button.addEventListener("click", () => { const form = document.querySelector(`[data-revision-for=\"${CSS.escape(button.dataset.deliverableId)}\"]`); requestClientRevision(button.dataset.deliverableId, form?.querySelector("textarea")?.value || ""); }));
}
function renderClientOperations() {
  const projects = clientData?.projects || [];
  const select = $("#client-message-project");
  if (!select) return;
  const selected = projects.some((item) => item.id === clientOperations.projectId) ? clientOperations.projectId : projects[0]?.id || "";
  select.innerHTML = projects.length ? projects.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join("") : `<option value="">No authorized projects</option>`;
  select.value = selected;
  $("#client-message-list").innerHTML = clientOperations.messages.length ? clientOperations.messages.map((item) => `<article class="message-row"><div class="message-meta"><strong>${escapeHtml(item.sender_id === actor.value.trim() ? "You" : "Data Fellows")}</strong><time>${escapeHtml(dateLabel(item.created_at))}</time></div><p>${escapeHtml(item.body)}</p></article>`).join("") : emptyState("No messages yet", "Start a scoped conversation with your Data Fellows delivery team.");
  $("#client-activity-list").innerHTML = clientOperations.activity.length ? clientOperations.activity.slice(0, 8).map((item) => `<div class="activity-row"><span class="activity-dot" aria-hidden="true"></span><div><strong>${escapeHtml(statusLabel(item.action))}</strong><small>${escapeHtml(dateLabel(item.created_at))}</small></div></div>`).join("") : `<p class="muted">No visible activity has been recorded for this project.</p>`;
}
async function loadClientOperations(projectId = "") {
  const projects = clientData?.projects || [];
  const selected = projectId || (projects.some((item) => item.id === clientOperations.projectId) ? clientOperations.projectId : projects[0]?.id) || "";
  clientOperations = { projectId: selected, messages: [], activity: [] };
  if (!selected) return renderClientOperations();
  try {
    const [messages, activity] = await Promise.all([
      request(`/api/projects/${encodeURIComponent(selected)}/messages`),
      request(`/api/projects/${encodeURIComponent(selected)}/activity`),
    ]);
    clientOperations = { projectId: selected, messages, activity };
  } catch (error) { showMessage(error.message, "error"); }
  renderClientOperations();
}
async function sendClientMessage(event) {
  event.preventDefault();
  const projectId = $("#client-message-project")?.value;
  const body = $("#client-message-body")?.value.trim();
  if (!projectId || !body) return showMessage("Choose a project and enter a message first.", "error");
  try {
    await request(`/api/projects/${encodeURIComponent(projectId)}/messages`, { method: "POST", body: JSON.stringify({ body, recipient_group: "internal" }) });
    $("#client-message-body").value = "";
    showMessage("Message sent to Data Fellows.", "success");
    await loadClientOperations(projectId);
  } catch (error) { showMessage(error.message, "error"); }
}
async function loadClientOverview() { try { clientData = await request("/api/client/overview"); renderClientOverview(); renderClientProjects(); renderClientDeliverables(); await loadClientOperations(); } catch (error) { showMessage(error.message, "error"); ["#client-project-list", "#client-projects-list", "#client-deliverables-list"].forEach((selector) => { if ($(selector)) $(selector).innerHTML = emptyState("Client workspace unavailable", error.message); }); } }
async function acceptClientDeliverable(id) { try { await request(`/api/deliverables/${encodeURIComponent(id)}/accept`, { method: "POST", body: "{}" }); showMessage("Your acceptance was recorded.", "success"); await loadClientOverview(); } catch (error) { showMessage(error.message, "error"); } }
async function requestClientRevision(id, comment) { if (!comment.trim()) return showMessage("Add a revision request before sending.", "error"); try { await request(`/api/deliverables/${encodeURIComponent(id)}/client-revision`, { method: "POST", body: JSON.stringify({ comment }) }); showMessage("Revision request sent to Data Fellows.", "success"); await loadClientOverview(); } catch (error) { showMessage(error.message, "error"); } }
function navigate(viewName) {
  const links = $$(".nav-list:not([hidden]) a:not([hidden])");
  const active = links.find(link => link.dataset.view === viewName) || links[0];
  const view = active.dataset.view;
  if (location.hash !== `#${view}`) history.pushState(null, "", `#${view}`);
  $$(".nav-list a").forEach(link => link.removeAttribute("aria-current"));
  active.setAttribute("aria-current", "page");
  $("#trail-page").textContent = active.firstChild.textContent.trim();
  $("#trail-portal").textContent = $("#portal-label").textContent;
  document.title = `${$("#trail-page").textContent} · Data Fellows Studio`;
  if ($(".sidebar").classList.contains("menu-open")) {
    setMenu(false);
    $("#workspace-content").focus();
  }
  $$(".view").forEach((item) => item.classList.toggle("active-view", item.id === `${view}-view`));
  $$('[data-view]').forEach((link) => link.classList.toggle("active", link.dataset.view === view));
  if (view.startsWith("admin-") && role.value === "admin") { loadAdminOverview(); }
  if (view.startsWith("client-") && role.value === "client") { if (!clientData) loadClientOverview(); else { renderClientOverview(); renderClientProjects(); renderClientDeliverables(); if (view === "client-communications") loadClientOperations(); } }
  if (view === "opportunities") loadOpportunities();
  if (view === "deliverables") loadSelectedDeliverables();
  if (view === "reviews") renderReviews();
  if (view === "profile") loadProfessionalProfile();

}
function setProfessionalNavigation(approved) {
  const applicantViews = ["applications", "profile", "help"];
  for (const link of $$("#primary-nav a")) {
    link.hidden = role.value === "reviewer" ? link.dataset.view !== "reviews"
      : !approved && !applicantViews.includes(link.dataset.view);
  }
}

function syncRole() {
  professionalProfile = null;
  profileEditMode = false;
  profileAccessOwner = "";
  $("#submit-application").disabled = false;
  clientData = null;
  adminData = null;
  $("#admin-detail-drawer")?.close();
  const isAdmin = role.value === "admin";
  const isClient = role.value === "client";
  actor.value = isAdmin ? "admin-1" : `${role.value}-1`;
  $("#legacy-admin-controls").hidden = !isAdmin;
  $("#review-action").hidden = role.value !== "reviewer";
  $("#client-acceptance").hidden = role.value !== "client";
  setProfessionalNavigation(false);
  $("#admin-nav").hidden = !isAdmin;
  $("#client-nav").hidden = !isClient;
  $("#primary-nav").hidden = isAdmin || isClient;
  $("#portal-label").textContent = isAdmin ? "Mission Control" : isClient ? "Client portal" : role.value === "reviewer" ? "Review workspace" : "Professional portal";
  $("#user-name").textContent = isAdmin ? "Data Fellows Admin" : role.value === "professional" ? "Professional workspace" : isClient ? "Client workspace" : statusLabel(role.value);
  $("#user-role").textContent = isAdmin ? "Internal admin" : role.value === "professional" ? "Professional applicant" : isClient ? "Authorized client" : statusLabel(role.value);
  setMenu(false);
  $("#developer-tools").open = false;
  navigate(location.hash.slice(1));

}
async function refresh() {
  const current = token();
  try {
    const me = await request("/api/me");
    if (current !== token()) return;
    showMessage("", "info");
    if (role.value === "admin") return await loadAdminOverview();
    if (role.value === "client") return await loadClientOverview();
    if (role.value !== "professional") return;
    profileAccessOwner = me.admission_status ? current : "";
    $("#edit-profile-button").disabled = !me.admission_status;
    $("#submit-application").disabled = Boolean(me.admission_status);
    const approved = me.admission_status === "approved";
    setProfessionalNavigation(approved);
    $("#user-role").textContent = approved ? "Approved professional" : "Professional applicant";
    if (requestedProfessionalView) {
      const destination = requestedProfessionalView;
      requestedProfessionalView = "";
      navigate(destination);
    } else if (!document.querySelector('.nav-list:not([hidden]) a[aria-current]:not([hidden])')) navigate();
    if (me.admission_status) {
      await loadApplication();
      if (location.hash === "#profile") await loadProfessionalProfile();
    }
    if (approved) await loadAssignments();
  } catch (error) {
    if (current === token()) showMessage(error.message, "error");
  }
}

const engagementDialog = $("#new-engagement-dialog");
const engagementForm = $("#new-engagement-form");
$("#admin-new-engagement").addEventListener("click", async () => {
  engagementForm.reset();
  const picker = engagementForm.elements.organization_id;
  picker.replaceChildren(new Option("Choose a client organization", ""));
  const submit = engagementForm.querySelector("[type=submit]");
  const status = engagementForm.querySelector("[role=status]");
  submit.disabled = true;
  status.textContent = "Loading client organizations…";
  engagementDialog.showModal();
  try {
    const organizations = await request("/api/organizations");
    for (const org of organizations) picker.add(new Option(org.name, org.id));
    submit.disabled = !organizations.length;
    status.textContent = organizations.length ? "" : "An authorized client organization is needed to create an engagement.";
  } catch (error) { status.textContent = error.message; }
});
engagementForm.querySelector("[type=button]").addEventListener("click", () => engagementDialog.close());
engagementForm.addEventListener("submit", async event => {
  event.preventDefault();
  const submit = engagementForm.querySelector("[type=submit]");
  submit.disabled = true;
  try {
    await request("/api/engagements", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(engagementForm))) });
    engagementDialog.close();
    navigate("admin-engagements");
    showMessage("Engagement created.", "success");
  } catch (error) {
    engagementForm.querySelector("[role=status]").textContent = error.message;
  } finally { submit.disabled = false; }
});

$("#developer-tools").hidden = !syntheticHarness;
syncRole();
refresh();
