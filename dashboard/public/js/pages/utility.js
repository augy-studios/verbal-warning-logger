import { utility as api } from "../api.js";
import { toast } from "../app.js";
import { idWithNameHtml, userIdHtml, setupCopyBtns, resolveUserNames } from "../id-display.js";

let _tab = "members";

export function render() {
  return `
    <div class="tabs">
      <button class="tab-btn ${_tab==="members"?"active":""}" data-tab="members">Search Members</button>
      <button class="tab-btn ${_tab==="channels"?"active":""}" data-tab="channels">Channels</button>
      <button class="tab-btn ${_tab==="roles"?"active":""}" data-tab="roles">Roles</button>
      <button class="tab-btn ${_tab==="ids"?"active":""}" data-tab="ids">Warning IDs</button>
      <button class="tab-btn ${_tab==="ping"?"active":""}" data-tab="ping">Bot Status</button>
    </div>
    <div id="utility-content"></div>`;
}

export async function init() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      _tab = btn.dataset.tab;
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b===btn));
      renderTab();
    });
  });
  renderTab();
}

function renderTab() {
  const content = document.getElementById("utility-content");
  if (!content) return;
  const tabs = { members: renderMembers, channels: renderChannels, roles: renderRoles, ids: renderIds, ping: renderPing };
  (tabs[_tab] || renderMembers)(content);
}

async function renderMembers(container) {
  container.innerHTML = `
    <div class="card">
      <div class="card-title">Search Guild Members</div>
      <div class="input-group" style="margin-bottom:1rem">
        <input type="search" id="member-query" placeholder="Search by name…" />
        <select id="role-filter" style="max-width:200px"><option value="">All roles</option></select>
        <button class="btn btn-primary btn-sm" id="member-search-btn">Search</button>
      </div>
      <div id="member-results"><p class="text-muted">Enter a name or select a role to search.</p></div>
    </div>`;

  // Load roles for filter
  try {
    const roles = await api.roles();
    const sel = document.getElementById("role-filter");
    if (sel) {
      roles.forEach((r) => {
        const opt = document.createElement("option");
        opt.value = r.id; opt.textContent = r.name;
        sel.appendChild(opt);
      });
    }
  } catch {}

  async function doSearch() {
    const query = document.getElementById("member-query")?.value.trim();
    const roleId = document.getElementById("role-filter")?.value;
    const results = document.getElementById("member-results");
    if (!query && !roleId) { toast("Enter a search term or select a role.", "info"); return; }
    results.innerHTML = '<div class="loader-wrap"><div class="loader"></div></div>';
    try {
      const params = {};
      if (query) params.query = query;
      if (roleId) params.role_id = roleId;
      params.limit = 100;
      const members = await api.members(params);
      if (!members.length) { results.innerHTML = '<p class="text-muted">No members found.</p>'; return; }
      results.innerHTML = `<div class="table-wrap"><table>
        <thead><tr><th>User</th><th>ID</th><th>Roles</th></tr></thead>
        <tbody>${members.map((m) => `
          <tr>
            <td>
              <div style="display:flex;align-items:center;gap:.5rem">
                ${m.avatar_url ? `<img src="${escHtml(m.avatar_url)}" style="width:1.5rem;height:1.5rem;border-radius:50%" />` : `<div style="width:1.5rem;height:1.5rem;border-radius:50%;background:var(--brand-mid)"></div>`}
                <span>${escHtml(m.username)}</span>
              </div>
            </td>
            <td>${idWithNameHtml(m.id, null)}</td>
            <td><span class="text-muted" style="font-size:.78rem">${m.roles.length} role(s)</span></td>
          </tr>`).join("")}
        </tbody>
      </table></div>
      <p class="text-muted" style="margin-top:.5rem">${members.length} member(s) found</p>`;
      setupCopyBtns(results);
    } catch (e) {
      results.innerHTML = `<p class="text-muted">Error: ${e.message}</p>`;
    }
  }

  document.getElementById("member-search-btn")?.addEventListener("click", doSearch);
  document.getElementById("member-query")?.addEventListener("keydown", (e) => { if (e.key==="Enter") doSearch(); });
}

async function renderChannels(container) {
  container.innerHTML = `
    <div class="card">
      <div class="card-title">Guild Channels</div>
      <div class="input-group" style="margin-bottom:1rem">
        <input type="text" id="cat-id" placeholder="Category ID (optional, to filter)" />
        <button class="btn btn-primary btn-sm" id="load-channels-btn">Load Channels</button>
      </div>
      <div id="channel-results"><p class="text-muted">Click Load Channels to fetch channel list.</p></div>
    </div>`;

  async function load() {
    const catId = document.getElementById("cat-id")?.value.trim();
    const results = document.getElementById("channel-results");
    results.innerHTML = '<div class="loader-wrap"><div class="loader"></div></div>';
    try {
      const params = catId ? { category_id: catId } : {};
      const channels = await api.channels(params);
      const types = { 0:"Text", 2:"Voice", 4:"Category", 5:"Announcement", 13:"Stage", 15:"Forum" };
      const channelNames = Object.fromEntries(channels.map((c) => [c.id, c.name]));
      results.innerHTML = `<div class="table-wrap"><table>
        <thead><tr><th>Name</th><th>Type</th><th>ID</th><th>Parent</th></tr></thead>
        <tbody>${channels.map((c) => `
          <tr>
            <td>${escHtml(c.name)}</td>
            <td><span class="badge badge-gray" style="font-size:.72rem">${types[c.type]||c.type}</span></td>
            <td>${idWithNameHtml(c.id, null)}</td>
            <td>${c.parent_id ? idWithNameHtml(c.parent_id, channelNames[c.parent_id]) : "—"}</td>
          </tr>`).join("")}
        </tbody>
      </table></div>
      <p class="text-muted" style="margin-top:.5rem">${channels.length} channel(s)</p>`;
      setupCopyBtns(results);
    } catch (e) {
      results.innerHTML = `<p class="text-muted">Error: ${e.message}</p>`;
    }
  }

  document.getElementById("load-channels-btn")?.addEventListener("click", load);
}

async function renderRoles(container) {
  container.innerHTML = `<div class="card"><div class="card-title">Guild Roles</div><div class="loader-wrap"><div class="loader"></div></div></div>`;
  try {
    const roles = await api.roles();
    const rolesHtml = `<div class="table-wrap"><table>
      <thead><tr><th>Name</th><th>ID</th><th>Color</th><th>Position</th></tr></thead>
      <tbody>${roles.map((r) => `
        <tr>
          <td style="display:flex;align-items:center;gap:.5rem">
            <span style="width:.75rem;height:.75rem;border-radius:50%;background:${r.color?"#"+r.color.toString(16).padStart(6,"0"):"#ccc"};flex-shrink:0"></span>
            ${escHtml(r.name)}
          </td>
          <td>${idWithNameHtml(r.id, null)}</td>
          <td class="cell-mono">${r.color?"#"+r.color.toString(16).padStart(6,"0"):"—"}</td>
          <td>${r.position}</td>
        </tr>`).join("")}
      </tbody>
    </table></div>`;
    container.querySelector(".card").innerHTML = `<div class="card-title">Guild Roles</div>${rolesHtml}<p class="text-muted" style="margin-top:.5rem">${roles.length} role(s)</p>`;
    setupCopyBtns(container.querySelector(".card"));
  } catch (e) {
    container.querySelector(".card").innerHTML = `<div class="card-title">Guild Roles</div><p class="text-muted">Error: ${e.message}</p>`;
  }
}

async function renderIds(container) {
  container.innerHTML = `
    <div class="card">
      <div class="card-title">Retrieve User IDs from Warnings</div>
      <div class="toolbar" style="margin-bottom:1rem">
        <div class="toolbar-left">
          <button class="btn btn-primary btn-sm" data-mode="offender" id="ids-offender">Offenders</button>
          <button class="btn btn-secondary btn-sm" data-mode="mod" id="ids-mod">Moderators</button>
        </div>
        <div class="toolbar-right">
          <button class="btn btn-ghost btn-sm" id="copy-ids-btn">Copy All IDs</button>
        </div>
      </div>
      <div id="ids-results"><p class="text-muted">Click Offenders or Moderators to load.</p></div>
    </div>`;

  let _currentIds = [];

  async function loadIds(mode) {
    const results = document.getElementById("ids-results");
    results.innerHTML = '<div class="loader-wrap"><div class="loader"></div></div>';
    try {
      const data = await api.warningIds(mode);
      _currentIds = data.map((r) => r.user_id);
      results.innerHTML = `<div class="table-wrap"><table>
        <thead><tr><th>User</th><th>Count</th></tr></thead>
        <tbody>${data.map((r) => `
          <tr>
            <td>${userIdHtml(r.user_id)}</td>
            <td>${r.count}</td>
          </tr>`).join("")}
        </tbody>
      </table></div>
      <p class="text-muted" style="margin-top:.5rem">${data.length} unique user(s)</p>`;
      setupCopyBtns(results);
      resolveUserNames(results);
    } catch (e) {
      results.innerHTML = `<p class="text-muted">Error: ${e.message}</p>`;
    }
  }

  container.querySelectorAll("[data-mode]").forEach((btn) => {
    btn.addEventListener("click", () => {
      container.querySelectorAll("[data-mode]").forEach((b) => {
        b.className = `btn ${b===btn?"btn-primary":"btn-secondary"} btn-sm`;
      });
      loadIds(btn.dataset.mode);
    });
  });

  document.getElementById("copy-ids-btn")?.addEventListener("click", () => {
    if (!_currentIds.length) return;
    navigator.clipboard.writeText(_currentIds.join("\n")).then(
      () => toast("IDs copied to clipboard.", "success"),
      () => toast("Copy failed.", "error")
    );
  });
}

async function renderPing(container) {
  container.innerHTML = `<div class="card"><div class="card-title">Bot Status</div><div class="loader-wrap"><div class="loader"></div></div></div>`;
  try {
    const data = await api.ping();
    const statusBadge = data.status === "online"
      ? `<span class="badge badge-green">Online</span>`
      : `<span class="badge badge-yellow">Unknown</span>`;
    container.querySelector(".card").innerHTML = `
      <div class="card-title">Bot Status</div>
      <div style="display:flex;align-items:center;gap:1rem;margin-bottom:.75rem">
        ${statusBadge}
        <span style="font-size:.9rem;color:#555">
          ${data.latency_ms !== null ? `Latency: <strong>${data.latency_ms}ms</strong>` : "Latency: unknown"}
        </span>
      </div>
      <button class="btn btn-secondary btn-sm" id="refresh-ping">Refresh</button>`;
    container.querySelector("#refresh-ping")?.addEventListener("click", () => renderPing(container));
  } catch (e) {
    container.querySelector(".card").innerHTML = `
      <div class="card-title">Bot Status</div>
      <span class="badge badge-red">Error</span>
      <p class="text-muted" style="margin-top:.5rem">${e.message}</p>`;
  }
}

function escHtml(s) { return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
