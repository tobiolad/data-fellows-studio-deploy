// Render only records returned for the selected project and current identity.
export function projectChannel({ request, escapeHtml: esc, dateLabel, actor, role }) {
  let generation = 0;
  const sections = new Map();
  const list = (rows, format, empty) => rows.length ? rows.map(format).join("") : `<p class="muted">${empty}</p>`;
  const panel = (heading, content) => `<section class="panel"><h2>${heading}</h2>${content}</section>`;

  async function open(host, projects, selected = "") {
    const generationAtOpen = ++generation;
    const identity = role.value;
    const project = projects.find(item => item.id === selected) || projects[0];
    host.replaceChildren();
    if (!project) {
      host.textContent = "Project communication becomes available when you have access to a project.";
      return;
    }
    const path = `/api/projects/${encodeURIComponent(project.id)}`;
    if (identity !== "client") {
      const label = document.createElement("label");
      label.textContent = "Project";
      const select = document.createElement("select");
      for (const item of projects) select.add(new Option(item.name, item.id));
      select.value = project.id;
      select.onchange = () => open(host, projects, select.value);
      label.append(select);
      host.append(label);
    }
    sections.set(host, project.id);
    const content = document.createElement("div");
    content.className = "stack-list";
    content.setAttribute("aria-live", "polite");
    content.textContent = "Loading project records…";
    host.append(content);
    const current = () => generationAtOpen === generation && sections.get(host) === project.id && role.value === identity;
    try {
      const [docs, notices, coordination, messages] = await Promise.all([
        request(path + "/documents"), request("/api/notifications"),
        identity === "professional" ? null : request(path + "/coordination"),
        identity === "client" ? [] : request(path + "/messages"),
      ]);
      if (!current()) return;
      const target = identity === "admin" ? '<label>Audience<select name="recipient_group"><option value="client">Client team</option><option value="professional">Assigned professionals</option><option value="internal">Internal team</option></select></label>' : "";
      const composer = `<form data-task="messages" class="message-composer">${target}<label>Message<textarea name="body" required minlength="2" maxlength="4000"></textarea></label><button class="primary-button">Send message</button></form>`;
      const conversation = list(messages, item => `<article class="message-row"><strong>${item.sender_id === actor.value ? "You" : identity === "admin" ? "Project participant" : "Data Fellows"}</strong> · ${esc(dateLabel(item.created_at))}<p>${esc(item.body)}</p></article>`, "No messages in this project.");
      const documentForm = identity === "admin" ? '<details><summary>Add a document reference</summary><form data-task="documents" class="message-composer"><label>Document title<input name="name" required minlength="2" maxlength="200"></label><label>Private storage reference<input name="storage_reference" required maxlength="512" placeholder="private://project/brief"></label><button class="primary-button">Add reference</button></form></details>' : "";
      const requestForm = identity === "client" ? '<form data-task="requests" class="message-composer"><label>Request for Data Fellows<textarea name="subject" required minlength="2" maxlength="500"></textarea></label><button class="primary-button">Submit request</button></form>' : "";
      function requestRow(item) {
        const decision = identity === "admin" && !item.decision ? `<form data-task="requests/${esc(item.id)}/decision" class="message-composer"><label>Decision<select name="decision"><option value="approved">Approve</option><option value="declined">Decline</option></select></label><label>Reason<textarea name="rationale" required minlength="2" maxlength="1000"></textarea></label><button class="primary-button">Record decision</button></form>` : "";
        return `<article class="message-row"><strong>${esc(item.subject)}</strong><p>${esc(item.decision || "Awaiting decision")} · ${esc(dateLabel(item.created_at))}</p>${item.rationale ? `<p>${esc(item.rationale)}</p>` : ""}${decision}</article>`;
      }
      content.innerHTML = (identity === "client" ? "" : panel("Project conversation", conversation + composer))
        + panel("Documents", list(docs, item => `<p><strong>${esc(item.name)}</strong> · ${esc(item.classification)}</p>`, "No document references have been shared.") + documentForm)
        + (coordination ? panel("Client requests", list(coordination.requests, requestRow, "No requests recorded.") + requestForm)
          + panel("Handover", coordination.handover ? list(coordination.handover.versions, item => `<p>${esc(item.title)} · Version ${esc(item.version)}</p>`, "") : '<p class="muted">No handover recorded.</p>') : "")
        + panel("Notifications", list(notices.filter(item => item.project_id === project.id), item => `<p>${esc(item.title)} · ${esc(dateLabel(item.created_at))}</p>`, "No project notifications."));
      content.onsubmit = async event => {
        event.preventDefault();
        if (!current()) return;
        const form = event.target;
        const button = form.querySelector("button");
        const body = Object.fromEntries(new FormData(form));
        if (form.dataset.task === "messages" && !body.recipient_group) body.recipient_group = "internal";
        button.disabled = true;
        try {
          await request(path + "/" + form.dataset.task, { method: "POST", body: JSON.stringify(body) });
          if (current()) await open(host, projects, project.id);
        } catch (error) {
          if (current()) {
            const feedback = form.querySelector("[role=alert]") || form.appendChild(document.createElement("p"));
            feedback.setAttribute("role", "alert");
            feedback.textContent = error.message;
            button.disabled = false;
          }
        }
      };
    } catch (error) {
      if (current()) content.textContent = error.message;
    }
  }
  return { open, clear() { generation++; for (const host of sections.keys()) host.replaceChildren(); sections.clear(); } };
}
