import { polls as api } from "../api.js";
import { toast, openModal, closeModal, confirmModal } from "../app.js";

let _filter = "active";

export function render() {
  return `
    <div class="toolbar">
      <div class="toolbar-left">
        <button class="btn ${_filter === "active" ? "btn-primary" : "btn-secondary"} btn-sm" data-filter="active">Active</button>
        <button class="btn ${_filter === "all" ? "btn-primary" : "btn-secondary"} btn-sm" data-filter="all">All</button>
      </div>
      <div class="toolbar-right">
        <button class="btn btn-primary btn-sm" id="create-poll-btn">+ Create Poll</button>
      </div>
    </div>
    <div id="polls-grid"><div class="loader-wrap"><div class="loader"></div></div></div>`;
}

export async function init() {
  document.querySelectorAll("[data-filter]").forEach((btn) => {
    btn.addEventListener("click", () => {
      _filter = btn.dataset.filter;
      document.querySelectorAll("[data-filter]").forEach((b) => {
        b.className = `btn ${b === btn ? "btn-primary" : "btn-secondary"} btn-sm`;
      });
      loadPolls();
    });
  });

  document.getElementById("create-poll-btn")?.addEventListener("click", openCreateModal);
  loadPolls();
}

async function loadPolls() {
  const grid = document.getElementById("polls-grid");
  if (!grid) return;
  grid.innerHTML = '<div class="loader-wrap"><div class="loader"></div></div>';
  try {
    const data = await api.list({ filter: _filter, per_page: 50 });
    if (!data.items.length) {
      grid.innerHTML = `<div class="empty-state"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg><p>No polls found.</p></div>`;
      return;
    }
    grid.innerHTML = `<div class="poll-grid">${data.items.map(pollCardHtml).join("")}</div>`;
    bindCardActions(grid);
  } catch (e) {
    grid.innerHTML = `<div class="card"><p class="text-muted">Error: ${e.message}</p></div>`;
  }
}

function pollCardHtml(p) {
  const status = p.is_active
    ? `<span class="badge badge-green">Active</span>`
    : `<span class="badge badge-gray">Closed</span>`;
  const anon = p.is_anonymous ? `<span class="badge badge-blue">Anonymous</span>` : "";
  const max  = p.max_votes > 0 ? `<span class="badge badge-yellow">Max ${p.max_votes}</span>` : "";
  return `
    <div class="poll-card" data-id="${p.id}">
      <div class="poll-card-header">
        <div class="poll-card-title">${escHtml(p.title)}</div>
        <div class="poll-card-actions">
          <button class="icon-btn results-btn" data-id="${p.id}" title="View results">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          </button>
          <button class="icon-btn edit-btn" data-id="${p.id}" title="Edit">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          ${p.is_active
            ? `<button class="icon-btn close-btn" data-id="${p.id}" title="Close poll">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
               </button>`
            : `<button class="icon-btn reopen-btn" data-id="${p.id}" title="Reopen poll">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
               </button>`}
        </div>
      </div>
      ${p.description ? `<p class="text-muted" style="font-size:.82rem">${escHtml(truncate(p.description,80))}</p>` : ""}
      <div style="display:flex;gap:.4rem;flex-wrap:wrap">${status}${anon}${max}</div>
      <div class="poll-card-meta">ID #${p.id} · ${fmtDate(p.created_at)} · ${p.vote_count ?? 0} vote(s)</div>
    </div>`;
}

function bindCardActions(container) {
  container.querySelectorAll(".results-btn").forEach((btn) => {
    btn.addEventListener("click", () => openResultsModal(btn.dataset.id));
  });
  container.querySelectorAll(".edit-btn").forEach((btn) => {
    btn.addEventListener("click", () => openEditModal(btn.dataset.id));
  });
  container.querySelectorAll(".close-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const ok = await confirmModal("Close this poll? Voting will be disabled.", "Close Poll");
      if (!ok) return;
      try { await api.close(btn.dataset.id); toast("Poll closed.", "success"); loadPolls(); }
      catch (e) { toast(e.message, "error"); }
    });
  });
  container.querySelectorAll(".reopen-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try { await api.reopen(btn.dataset.id); toast("Poll reopened.", "success"); loadPolls(); }
      catch (e) { toast(e.message, "error"); }
    });
  });
}

function openCreateModal() {
  const html = buildPollForm();
  openModal("Create Poll", html, { wide: true });
  initOptionButtons();
  document.getElementById("poll-form-cancel")?.addEventListener("click", () => closeModal(null));
  document.getElementById("poll-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const options = [...document.querySelectorAll(".opt-input")].map((i) => i.value.trim()).filter(Boolean);
    if (options.length < 2) { toast("Minimum 2 options required.", "error"); return; }
    try {
      await api.create({
        title: fd.get("title"),
        description: fd.get("description") || "",
        options,
        is_anonymous: fd.get("is_anonymous") === "on",
        max_votes: parseInt(fd.get("max_votes") || "0"),
      });
      toast("Poll created.", "success");
      closeModal(null);
      loadPolls();
    } catch (err) { toast(err.message, "error", "Create failed"); }
  });
}

async function openEditModal(id) {
  let poll;
  try { poll = await api.get(id); } catch (e) { toast(e.message, "error"); return; }

  const html = `
    <form id="edit-poll-form">
      <div class="form-group"><label>Title *</label><input name="title" value="${escHtml(poll.title)}" required /></div>
      <div class="form-group"><label>Description</label><textarea name="description">${escHtml(poll.description)}</textarea></div>
      <div class="form-group"><label>Options (labels only, count locked)</label>
        <div class="option-list">${poll.options.map((o) => `<input class="opt-input" value="${escHtml(o.label)}" required />`).join("")}</div>
      </div>
      <div style="display:flex;gap:.5rem;justify-content:flex-end;margin-top:.75rem">
        <button type="button" class="btn btn-secondary" id="edit-poll-cancel">Cancel</button>
        <button type="submit" class="btn btn-primary">Save</button>
      </div>
    </form>`;
  openModal(`Edit Poll #${id}`, html);
  document.getElementById("edit-poll-cancel")?.addEventListener("click", () => closeModal(null));
  document.getElementById("edit-poll-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const labels = [...document.querySelectorAll(".opt-input")].map((i) => i.value.trim());
    try {
      await api.update(id, { title: fd.get("title"), description: fd.get("description") || "", option_labels: labels });
      toast("Poll updated.", "success");
      closeModal(null);
      loadPolls();
    } catch (err) { toast(err.message, "error"); }
  });
}

async function openResultsModal(id) {
  const modal = document.getElementById("modal-body");
  openModal("Poll Results", '<div class="loader-wrap"><div class="loader"></div></div>');
  try {
    const data = await api.results(id);
    const { poll, options, total_votes } = data;
    const html = `
      <div style="margin-bottom:.75rem">
        <div style="font-weight:600;color:var(--brand-text);margin-bottom:.25rem">${escHtml(poll.title)}</div>
        ${poll.description ? `<p class="text-muted" style="font-size:.85rem">${escHtml(poll.description)}</p>` : ""}
        <div style="margin-top:.4rem;font-size:.82rem;color:#888">
          ${poll.is_active ? '<span class="badge badge-green">Active</span>' : '<span class="badge badge-gray">Closed</span>'}
          ${poll.is_anonymous ? '&nbsp;<span class="badge badge-blue">Anonymous</span>' : ""}
          &nbsp;${total_votes} vote(s)
        </div>
      </div>
      <div>
        ${options.map((o) => `
          <div class="progress-wrap">
            <div class="progress-label"><span>${escHtml(o.label)}</span><span>${o.count} (${o.percentage}%)</span></div>
            <div class="progress-bar-outer"><div class="progress-bar-inner" style="width:${o.percentage}%"></div></div>
          </div>`).join("")}
      </div>`;
    document.getElementById("modal-body").innerHTML = html;
  } catch (e) {
    document.getElementById("modal-body").innerHTML = `<p class="text-muted">Error: ${e.message}</p>`;
  }
}

function buildPollForm(defaults = {}) {
  return `
    <form id="poll-form">
      <div class="form-group"><label>Title *</label><input name="title" value="${escHtml(defaults.title||"")}" required placeholder="Poll title…" /></div>
      <div class="form-group"><label>Description</label><textarea name="description" placeholder="Optional description…">${escHtml(defaults.description||"")}</textarea></div>
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
        <button type="button" class="btn btn-secondary" id="poll-form-cancel">Cancel</button>
        <button type="submit" class="btn btn-primary">Create Poll</button>
      </div>
    </form>`;
}

function initOptionButtons() {
  document.getElementById("add-opt-btn")?.addEventListener("click", () => {
    const list = document.getElementById("option-list");
    if (!list || list.children.length >= 24) return;
    const row = document.createElement("div");
    row.className = "option-row";
    const n = list.children.length + 1;
    row.innerHTML = `<input class="opt-input" placeholder="Option ${n}" required /><button type="button" class="btn-icon-danger rm-opt"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>`;
    list.appendChild(row);
    row.querySelector(".opt-input")?.focus();
    bindRemove();
  });
  bindRemove();
}

function bindRemove() {
  document.querySelectorAll(".rm-opt").forEach((btn) => {
    btn.onclick = () => {
      const list = document.getElementById("option-list");
      if (list && list.children.length > 2) btn.closest(".option-row")?.remove();
    };
  });
}

function fmtDate(str) {
  if (!str) return "";
  return new Date(str.replace(" ", "T") + "Z").toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function escHtml(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function truncate(s, n) {
  return s && s.length > n ? s.slice(0, n) + "…" : s;
}
