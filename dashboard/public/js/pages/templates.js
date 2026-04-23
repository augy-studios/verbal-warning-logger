import { templates as api } from "../api.js";
import { toast, openModal, closeModal, confirmModal } from "../app.js";

let _filter = "active";

export function render() {
  return `
    <div class="toolbar">
      <div class="toolbar-left">
        <button class="btn ${_filter==="active"?"btn-primary":"btn-secondary"} btn-sm" data-filter="active">Active</button>
        <button class="btn ${_filter==="all"?"btn-primary":"btn-secondary"} btn-sm" data-filter="all">Include Deleted</button>
      </div>
      <div class="toolbar-right">
        <button class="btn btn-primary btn-sm" id="create-tpl-btn">+ Create Template</button>
        <button class="btn btn-secondary btn-sm" id="from-poll-btn">From Poll ID</button>
      </div>
    </div>
    <div id="tpl-grid"><div class="loader-wrap"><div class="loader"></div></div></div>`;
}

export async function init() {
  document.querySelectorAll("[data-filter]").forEach((btn) => {
    btn.addEventListener("click", () => {
      _filter = btn.dataset.filter;
      document.querySelectorAll("[data-filter]").forEach((b) => {
        b.className = `btn ${b===btn?"btn-primary":"btn-secondary"} btn-sm`;
      });
      loadTemplates();
    });
  });

  document.getElementById("create-tpl-btn")?.addEventListener("click", openCreateModal);
  document.getElementById("from-poll-btn")?.addEventListener("click", openFromPollModal);
  loadTemplates();
}

async function loadTemplates() {
  const grid = document.getElementById("tpl-grid");
  if (!grid) return;
  grid.innerHTML = '<div class="loader-wrap"><div class="loader"></div></div>';
  try {
    const items = await api.list({ filter: _filter });
    if (!items.length) {
      grid.innerHTML = `<div class="empty-state"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><p>No templates found.</p></div>`;
      return;
    }
    grid.innerHTML = `<div class="poll-grid">${items.map(cardHtml).join("")}</div>`;
    bindActions(grid);
  } catch (e) {
    grid.innerHTML = `<div class="card"><p class="text-muted">Error: ${e.message}</p></div>`;
  }
}

function cardHtml(t) {
  const deleted = t.is_deleted;
  return `
    <div class="poll-card ${deleted?"opacity:0.6":""}" data-id="${t.id}">
      <div class="poll-card-header">
        <div class="poll-card-title">${escHtml(t.name)}${deleted?' <span class="badge badge-red" style="font-size:.7rem">Deleted</span>':""}</div>
        <div class="poll-card-actions">
          <button class="icon-btn preview-btn" data-id="${t.id}" title="Preview">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
          ${!deleted ? `
            <button class="icon-btn edit-btn" data-id="${t.id}" title="Edit">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
            <button class="icon-btn use-btn" data-id="${t.id}" title="Use (create poll)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            </button>
            <button class="icon-btn del-btn" data-id="${t.id}" title="Delete">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>
            </button>
          ` : `
            <button class="icon-btn restore-btn" data-id="${t.id}" title="Restore">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
            </button>
          `}
        </div>
      </div>
      ${t.description ? `<p class="text-muted" style="font-size:.82rem">${escHtml(truncate(t.description,80))}</p>` : ""}
      <div class="poll-card-meta">ID #${t.id} · ${fmtDate(t.created_at)}${t.is_anonymous?" · Anonymous":""}</div>
    </div>`;
}

function bindActions(container) {
  container.querySelectorAll(".preview-btn").forEach((btn) => {
    btn.addEventListener("click", () => openPreviewModal(btn.dataset.id));
  });
  container.querySelectorAll(".edit-btn").forEach((btn) => {
    btn.addEventListener("click", () => openEditModal(btn.dataset.id));
  });
  container.querySelectorAll(".use-btn").forEach((btn) => {
    btn.addEventListener("click", () => openUseModal(btn.dataset.id));
  });
  container.querySelectorAll(".del-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const ok = await confirmModal("Delete this template?", "Delete Template");
      if (!ok) return;
      try { await api.delete(btn.dataset.id); toast("Template deleted.", "success"); loadTemplates(); }
      catch (e) { toast(e.message, "error"); }
    });
  });
  container.querySelectorAll(".restore-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try { await api.restore(btn.dataset.id); toast("Template restored.", "success"); loadTemplates(); }
      catch (e) { toast(e.message, "error"); }
    });
  });
}

function openCreateModal() {
  const html = `
    <form id="tpl-form">
      <div class="form-group"><label>Name *</label><input name="name" required placeholder="Template name…" /></div>
      <div class="form-group"><label>Description</label><textarea name="description" placeholder="Optional description…"></textarea></div>
      <div class="form-group">
        <label>Options (min 2, max 24)</label>
        <div class="option-list" id="option-list">
          <div class="option-row"><input class="opt-input" placeholder="Option 1" required /><button type="button" class="btn-icon-danger rm-opt"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
          <div class="option-row"><input class="opt-input" placeholder="Option 2" required /><button type="button" class="btn-icon-danger rm-opt"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div>
        </div>
        <button type="button" class="btn btn-ghost btn-sm" id="add-opt-btn" style="margin-top:.4rem">+ Add Option</button>
      </div>
      <div class="form-row">
        <div class="form-group form-check"><input type="checkbox" name="is_anonymous" id="anon-chk" /><label for="anon-chk">Anonymous votes</label></div>
        <div class="form-group"><label>Max votes (0 = unlimited)</label><input type="number" name="max_votes" value="0" min="0" /></div>
      </div>
      <div style="display:flex;gap:.5rem;justify-content:flex-end;margin-top:.75rem">
        <button type="button" class="btn btn-secondary" id="tpl-cancel">Cancel</button>
        <button type="submit" class="btn btn-primary">Create Template</button>
      </div>
    </form>`;
  openModal("Create Poll Template", html, { wide: true });
  initOptionButtons("option-list");
  document.getElementById("tpl-cancel")?.addEventListener("click", () => closeModal(null));
  document.getElementById("tpl-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const options = [...document.querySelectorAll(".opt-input")].map((i) => i.value.trim()).filter(Boolean);
    if (options.length < 2) { toast("Minimum 2 options required.", "error"); return; }
    try {
      await api.create({ name: fd.get("name"), description: fd.get("description")||"", options, is_anonymous: fd.get("is_anonymous")==="on", max_votes: parseInt(fd.get("max_votes")||"0") });
      toast("Template created.", "success"); closeModal(null); loadTemplates();
    } catch (err) { toast(err.message, "error"); }
  });
}

async function openEditModal(id) {
  let tpl;
  try { tpl = await api.get(id); } catch (e) { toast(e.message, "error"); return; }
  const html = `
    <form id="edit-tpl-form">
      <div class="form-group"><label>Name *</label><input name="name" value="${escHtml(tpl.name)}" required /></div>
      <div class="form-group"><label>Description</label><textarea name="description">${escHtml(tpl.description)}</textarea></div>
      <div class="form-group"><label>Options (count locked)</label>
        <div class="option-list">${tpl.options.map((o) => `<input class="opt-input" value="${escHtml(o.label)}" required />`).join("")}</div>
      </div>
      <div style="display:flex;gap:.5rem;justify-content:flex-end;margin-top:.75rem">
        <button type="button" class="btn btn-secondary" id="edit-tpl-cancel">Cancel</button>
        <button type="submit" class="btn btn-primary">Save</button>
      </div>
    </form>`;
  openModal(`Edit Template #${id}`, html);
  document.getElementById("edit-tpl-cancel")?.addEventListener("click", () => closeModal(null));
  document.getElementById("edit-tpl-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const labels = [...document.querySelectorAll(".opt-input")].map((i) => i.value.trim());
    try {
      await api.update(id, { name: fd.get("name"), description: fd.get("description")||"", option_labels: labels });
      toast("Template updated.", "success"); closeModal(null); loadTemplates();
    } catch (err) { toast(err.message, "error"); }
  });
}

async function openPreviewModal(id) {
  openModal("Template Preview", '<div class="loader-wrap"><div class="loader"></div></div>');
  try {
    const tpl = await api.get(id);
    const html = `
      <div style="margin-bottom:.75rem">
        <div style="font-weight:600;color:var(--brand-text);margin-bottom:.25rem">${escHtml(tpl.name)}</div>
        ${tpl.description ? `<p class="text-muted" style="font-size:.85rem">${escHtml(tpl.description)}</p>` : ""}
        ${tpl.is_anonymous ? '<span class="badge badge-blue" style="margin-top:.35rem">Anonymous</span>' : ""}
        ${tpl.max_votes > 0 ? `<span class="badge badge-yellow" style="margin-left:.35rem">Max ${tpl.max_votes} votes</span>` : ""}
      </div>
      <div>
        ${tpl.options.map((o, i) => `
          <div style="display:flex;align-items:center;gap:.75rem;padding:.5rem .75rem;background:rgba(255,255,255,0.45);border:1px solid rgba(255,255,255,0.6);border-radius:8px;margin-bottom:.35rem">
            <span style="color:#888;font-size:.85rem;min-width:1.5rem">${i+1}.</span>
            <span>${escHtml(o.label)}</span>
          </div>`).join("")}
      </div>
      <div class="notice notice-info" style="margin-top:1rem">This is a preview only. Use "Use" to create a live poll.</div>`;
    document.getElementById("modal-body").innerHTML = html;
  } catch (e) {
    document.getElementById("modal-body").innerHTML = `<p class="text-muted">Error: ${e.message}</p>`;
  }
}

async function openUseModal(id) {
  const html = `
    <form id="use-tpl-form">
      <p class="text-muted" style="margin-bottom:.75rem">Creates a new poll from this template in the database. Note: posting to a Discord channel requires the bot.</p>
      <div class="form-row">
        <div class="form-group form-check"><input type="checkbox" name="is_anonymous" id="use-anon-chk" /><label for="use-anon-chk">Override: Anonymous</label></div>
        <div class="form-group"><label>Override Max Votes (0 = template default)</label><input type="number" name="max_votes" value="0" min="0" /></div>
      </div>
      <div style="display:flex;gap:.5rem;justify-content:flex-end;margin-top:.75rem">
        <button type="button" class="btn btn-secondary" id="use-cancel">Cancel</button>
        <button type="submit" class="btn btn-primary">Create Poll</button>
      </div>
    </form>`;
  openModal("Use Template", html);
  document.getElementById("use-cancel")?.addEventListener("click", () => closeModal(null));
  document.getElementById("use-tpl-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const poll = await api.use(id, { is_anonymous: fd.get("is_anonymous")==="on", max_votes: parseInt(fd.get("max_votes")||"0") });
      toast(`Poll #${poll.id} created from template.`, "success"); closeModal(null);
    } catch (err) { toast(err.message, "error"); }
  });
}

function openFromPollModal() {
  const html = `
    <form id="from-poll-form">
      <div class="form-group"><label>Poll ID</label><input type="number" name="poll_id" required placeholder="Poll ID…" min="1" /></div>
      <div style="display:flex;gap:.5rem;justify-content:flex-end;margin-top:.75rem">
        <button type="button" class="btn btn-secondary" id="fp-cancel">Cancel</button>
        <button type="submit" class="btn btn-primary">Create Template</button>
      </div>
    </form>`;
  openModal("Create Template from Poll", html);
  document.getElementById("fp-cancel")?.addEventListener("click", () => closeModal(null));
  document.getElementById("from-poll-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const tpl = await api.fromPoll(fd.get("poll_id"));
      toast(`Template #${tpl.id} created.`, "success"); closeModal(null); loadTemplates();
    } catch (err) { toast(err.message, "error"); }
  });
}

function initOptionButtons(listId = "option-list") {
  document.getElementById("add-opt-btn")?.addEventListener("click", () => {
    const list = document.getElementById(listId);
    if (!list || list.children.length >= 24) return;
    const row = document.createElement("div");
    row.className = "option-row";
    row.innerHTML = `<input class="opt-input" placeholder="Option ${list.children.length+1}" required /><button type="button" class="btn-icon-danger rm-opt"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>`;
    list.appendChild(row);
    row.querySelector(".opt-input")?.focus();
    bindRemoveOpts();
  });
  bindRemoveOpts();
}

function bindRemoveOpts() {
  document.querySelectorAll(".rm-opt").forEach((btn) => {
    btn.onclick = () => {
      const list = btn.closest(".option-list");
      if (list && list.children.length > 2) btn.closest(".option-row")?.remove();
    };
  });
}

function fmtDate(str) {
  if (!str) return "";
  return new Date(str.replace(" ","T")+"Z").toLocaleDateString(undefined,{year:"numeric",month:"short",day:"numeric"});
}
function escHtml(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function truncate(s, n) { return s && s.length>n ? s.slice(0,n)+"…" : s; }
