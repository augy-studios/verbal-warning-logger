import { warnings as api } from "../api.js";
import { toast, openModal, closeModal, confirmModal } from "../app.js";
import { userIdHtml, setupCopyBtns, resolveUserNames } from "../id-display.js";

let _state = { page: 1, per_page: 20, user_id: "", tab: "list", lb_mode: "offender" };

export function render() {
  return `
    <div class="tabs">
      <button class="tab-btn ${_state.tab === "list" ? "active" : ""}" data-tab="list">All Warnings</button>
      <button class="tab-btn ${_state.tab === "search" ? "active" : ""}" data-tab="search">Search by User</button>
      <button class="tab-btn ${_state.tab === "leaderboard" ? "active" : ""}" data-tab="leaderboard">Leaderboard</button>
    </div>
    <div id="warnings-content"></div>`;
}

export async function init() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      _state.tab = btn.dataset.tab;
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b === btn));
      renderTab();
    });
  });
  renderTab();
}

async function renderTab() {
  const content = document.getElementById("warnings-content");
  if (!content) return;
  content.innerHTML = '<div class="loader-wrap"><div class="loader"></div></div>';
  if (_state.tab === "list")        await renderList(content);
  else if (_state.tab === "search") await renderSearch(content);
  else                               await renderLeaderboard(content);
}

async function renderList(container) {
  const params = { page: _state.page, per_page: _state.per_page };
  if (_state.user_id) params.user_id = _state.user_id;

  let data;
  try { data = await api.list(params); }
  catch (e) { container.innerHTML = `<div class="card"><p class="text-muted">Error: ${e.message}</p></div>`; return; }

  container.innerHTML = `
    <div class="toolbar">
      <div class="toolbar-left">
        <input class="search-input" type="search" id="uid-filter" placeholder="Filter by User ID…" value="${_state.user_id}" />
        <button class="btn btn-secondary btn-sm" id="filter-btn">Filter</button>
        ${_state.user_id ? `<button class="btn btn-ghost btn-sm" id="clear-filter">Clear</button>` : ""}
      </div>
      <div class="toolbar-right">
        <button class="btn btn-primary btn-sm" id="add-warn-btn">+ Add Warning</button>
      </div>
    </div>
    <div class="card">
      <div class="table-wrap">
        <table>
          <thead><tr><th>#</th><th>Date</th><th>User</th><th>Mod</th><th>Reason</th><th>Evidence</th><th>Actions</th></tr></thead>
          <tbody id="warn-tbody">
            ${data.items.map(rowHtml).join("") || `<tr><td colspan="7" style="text-align:center" class="text-muted">No warnings found.</td></tr>`}
          </tbody>
        </table>
      </div>
      ${paginationHtml(data.page, data.pages)}
    </div>`;

  container.querySelector("#filter-btn")?.addEventListener("click", () => {
    _state.user_id = container.querySelector("#uid-filter")?.value.trim() || "";
    _state.page = 1;
    renderList(container);
  });
  container.querySelector("#uid-filter")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") container.querySelector("#filter-btn")?.click();
  });
  container.querySelector("#clear-filter")?.addEventListener("click", () => {
    _state.user_id = ""; _state.page = 1; renderList(container);
  });

  container.querySelectorAll(".pg-btn").forEach((btn) => {
    btn.addEventListener("click", () => { _state.page = parseInt(btn.dataset.page); renderList(container); });
  });

  container.querySelector("#add-warn-btn")?.addEventListener("click", () => openAddModal(container));
  bindRowActions(container, () => renderList(container));
}

function rowHtml(w) {
  return `<tr data-id="${w.id}">
    <td class="cell-id">${w.id}</td>
    <td class="text-muted" style="white-space:nowrap;font-size:.8rem">${fmtDate(w.createdAt)}</td>
    <td>${userIdHtml(w.userId)}</td>
    <td>${userIdHtml(w.modId)}</td>
    <td style="max-width:220px"><span title="${escHtml(w.reason)}">${escHtml(truncate(w.reason, 50))}</span></td>
    <td><a class="link external" href="${escHtml(w.evidenceLink)}" target="_blank" rel="noopener">Link</a></td>
    <td class="td-actions">
      <button class="btn btn-secondary btn-sm edit-btn" data-id="${w.id}">Edit</button>
      <button class="btn btn-danger btn-sm del-btn" data-id="${w.id}">Del</button>
    </td>
  </tr>`;
}

function bindRowActions(container, refresh) {
  container.querySelectorAll(".edit-btn").forEach((btn) => {
    btn.addEventListener("click", () => openEditModal(btn.dataset.id, refresh));
  });
  container.querySelectorAll(".del-btn").forEach((btn) => {
    btn.addEventListener("click", () => deleteWarning(btn.dataset.id, refresh));
  });
  setupCopyBtns(container);
  resolveUserNames(container);
}

async function renderSearch(container) {
  container.innerHTML = `
    <div class="card">
      <div class="card-title">Search Warnings by User</div>
      <div class="input-group" style="margin-bottom:1rem">
        <input type="search" id="search-uid" placeholder="Discord User ID" />
        <button class="btn btn-primary" id="search-btn">Search</button>
      </div>
      <div id="search-results"></div>
    </div>`;

  async function doSearch() {
    const uid = document.getElementById("search-uid")?.value.trim();
    if (!uid) return;
    const results = document.getElementById("search-results");
    results.innerHTML = '<div class="loader-wrap"><div class="loader"></div></div>';
    try {
      const data = await api.list({ user_id: uid, per_page: 100 });
      if (!data.items.length) {
        results.innerHTML = '<p class="text-muted">No warnings found for this user.</p>';
      } else {
        results.innerHTML = `<div class="table-wrap"><table>
          <thead><tr><th>#</th><th>Date</th><th>Reason</th><th>Evidence</th><th>Mod</th></tr></thead>
          <tbody>${data.items.map((w) => `
            <tr>
              <td class="cell-id">${w.id}</td>
              <td class="text-muted" style="white-space:nowrap;font-size:.8rem">${fmtDate(w.createdAt)}</td>
              <td style="max-width:300px">${escHtml(w.reason)}</td>
              <td><a class="link external" href="${escHtml(w.evidenceLink)}" target="_blank" rel="noopener">Link</a></td>
              <td>${userIdHtml(w.modId)}</td>
            </tr>`).join("")}
          </tbody>
        </table></div>
        <p class="text-muted" style="margin-top:.5rem">${data.total} warning(s) total</p>`;
        setupCopyBtns(results);
        resolveUserNames(results);
      }
    } catch (e) {
      results.innerHTML = `<p class="text-muted">Error: ${e.message}</p>`;
    }
  }

  document.getElementById("search-btn")?.addEventListener("click", doSearch);
  document.getElementById("search-uid")?.addEventListener("keydown", (e) => { if (e.key === "Enter") doSearch(); });
}

async function renderLeaderboard(container) {
  container.innerHTML = `
    <div class="toolbar">
      <div class="toolbar-left">
        <button class="btn ${_state.lb_mode === "offender" ? "btn-primary" : "btn-secondary"} btn-sm" data-mode="offender">Top Offenders</button>
        <button class="btn ${_state.lb_mode === "mod" ? "btn-primary" : "btn-secondary"} btn-sm" data-mode="mod">Top Moderators</button>
      </div>
    </div>
    <div id="lb-content"><div class="loader-wrap"><div class="loader"></div></div></div>`;

  container.querySelectorAll("[data-mode]").forEach((btn) => {
    btn.addEventListener("click", () => {
      _state.lb_mode = btn.dataset.mode;
      container.querySelectorAll("[data-mode]").forEach((b) => {
        b.className = `btn ${b === btn ? "btn-primary" : "btn-secondary"} btn-sm`;
      });
      loadLb();
    });
  });

  async function loadLb() {
    const el = document.getElementById("lb-content");
    if (!el) return;
    el.innerHTML = '<div class="loader-wrap"><div class="loader"></div></div>';
    try {
      const data = await api.leaderboard(_state.lb_mode);
      if (!data.length) { el.innerHTML = '<p class="text-muted">No data yet.</p>'; return; }
      const medals = [
        `<img class="medal-svg" src="https://cdn.jsdelivr.net/npm/twemoji@14.0.2/assets/svg/1f947.svg" alt="🥇" />`,
        `<img class="medal-svg" src="https://cdn.jsdelivr.net/npm/twemoji@14.0.2/assets/svg/1f948.svg" alt="🥈" />`,
        `<img class="medal-svg" src="https://cdn.jsdelivr.net/npm/twemoji@14.0.2/assets/svg/1f949.svg" alt="🥉" />`,
      ];
      const medalClass = ["gold","silver","bronze"];
      el.innerHTML = `<div class="lb-list">${data.map((row, i) => `
        <div class="lb-row">
          <div class="lb-rank ${medalClass[i] || ""}">${medals[i] || `#${i+1}`}</div>
          <div class="lb-user">${userIdHtml(row.user_id)}</div>
          <div class="lb-count">${row.count}</div>
        </div>`).join("")}
      </div>`;
      setupCopyBtns(el);
      resolveUserNames(el);
    } catch (e) {
      el.innerHTML = `<p class="text-muted">Error: ${e.message}</p>`;
    }
  }

  loadLb();
}

function paginationHtml(page, pages) {
  if (pages <= 1) return "";
  const btns = [];
  btns.push(`<button class="btn btn-secondary btn-sm pg-btn" data-page="${Math.max(1,page-1)}" ${page<=1?"disabled":""}>←</button>`);
  for (let p = Math.max(1,page-2); p <= Math.min(pages,page+2); p++) {
    btns.push(`<button class="btn ${p===page?"btn-primary":"btn-secondary"} btn-sm pg-btn" data-page="${p}">${p}</button>`);
  }
  btns.push(`<button class="btn btn-secondary btn-sm pg-btn" data-page="${Math.min(pages,page+1)}" ${page>=pages?"disabled":""}>→</button>`);
  return `<div class="pagination">${btns.join("")}<span class="pagination-info">Page ${page} of ${pages}</span></div>`;
}

async function openAddModal(container) {
  const html = `
    <form id="warn-form">
      <div class="form-group"><label>User ID *</label><input type="text" name="userId" placeholder="Discord User ID" required /></div>
      <div class="form-group"><label>Reason *</label><textarea name="reason" required placeholder="Reason for warning…"></textarea></div>
      <div class="form-group"><label>Evidence Link *</label><input type="url" name="evidenceLink" placeholder="https://discord.com/channels/…" required /></div>
      <div class="form-group"><label>Mod ID (leave blank to use yourself)</label><input type="text" name="modId" placeholder="Discord Mod User ID" /></div>
      <div style="display:flex;gap:.5rem;justify-content:flex-end;margin-top:.75rem">
        <button type="button" class="btn btn-secondary" id="form-cancel">Cancel</button>
        <button type="submit" class="btn btn-primary">Add Warning</button>
      </div>
    </form>`;

  openModal("Add Verbal Warning", html);
  document.getElementById("form-cancel")?.addEventListener("click", () => closeModal(null));
  document.getElementById("warn-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await api.create({
        userId: fd.get("userId"),
        reason: fd.get("reason"),
        evidenceLink: fd.get("evidenceLink"),
        modId: fd.get("modId") || "0",
      });
      toast("Warning added successfully.", "success");
      closeModal(null);
      renderList(container);
    } catch (err) {
      toast(err.message, "error", "Failed to add warning");
    }
  });
}

async function openEditModal(id, refresh) {
  let w;
  try { w = await api.get(id); } catch (e) { toast(e.message, "error"); return; }

  const html = `
    <form id="edit-form">
      <div class="form-group"><label>User ID *</label><input type="text" name="userId" value="${escHtml(String(w.userId))}" required /></div>
      <div class="form-group"><label>Reason *</label><textarea name="reason" required>${escHtml(w.reason)}</textarea></div>
      <div class="form-group"><label>Evidence Link *</label><input type="url" name="evidenceLink" value="${escHtml(w.evidenceLink)}" required /></div>
      <div class="form-group"><label>Mod ID *</label><input type="text" name="modId" value="${escHtml(String(w.modId))}" required /></div>
      <div style="display:flex;gap:.5rem;justify-content:flex-end;margin-top:.75rem">
        <button type="button" class="btn btn-secondary" id="edit-cancel">Cancel</button>
        <button type="submit" class="btn btn-primary">Save Changes</button>
      </div>
    </form>`;

  openModal(`Edit Warning #${id}`, html);
  document.getElementById("edit-cancel")?.addEventListener("click", () => closeModal(null));
  document.getElementById("edit-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await api.update(id, {
        userId: fd.get("userId"),
        reason: fd.get("reason"),
        evidenceLink: fd.get("evidenceLink"),
        modId: fd.get("modId"),
      });
      toast("Warning updated.", "success");
      closeModal(null);
      refresh();
    } catch (err) {
      toast(err.message, "error", "Failed to update warning");
    }
  });
}

async function deleteWarning(id, refresh) {
  const ok = await confirmModal(`Permanently delete warning #${id}? This cannot be undone.`, "Delete Warning");
  if (!ok) return;
  try {
    await api.delete(id);
    toast(`Warning #${id} deleted.`, "success");
    refresh();
  } catch (e) {
    toast(e.message, "error", "Delete failed");
  }
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
