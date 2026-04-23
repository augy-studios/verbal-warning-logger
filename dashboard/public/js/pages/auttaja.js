import { auttaja as api } from "../api.js";
import { toast, openModal, closeModal } from "../app.js";
import { userIdHtml, setupCopyBtns, resolveUserNames } from "../id-display.js";

let _tab = "search";
let _lbMode = "offender";

export function render() {
  return `
    <div class="tabs">
      <button class="tab-btn ${_tab==="search"?"active":""}" data-tab="search">Search User</button>
      <button class="tab-btn ${_tab==="leaderboard"?"active":""}" data-tab="leaderboard">Leaderboard</button>
    </div>
    <div id="auttaja-content"></div>`;
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
  const content = document.getElementById("auttaja-content");
  if (!content) return;
  if (_tab === "search") renderSearch(content);
  else renderLeaderboard(content);
}

function renderSearch(container) {
  container.innerHTML = `
    <div class="card">
      <div class="card-title">Search Auttaja Records</div>
      <div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1rem">
        <input type="text" id="auttaja-uid" placeholder="Discord User ID or mention (@user)" style="flex:1;min-width:200px" />
        <div style="display:flex;gap:.35rem">
          <button class="btn btn-primary btn-sm" id="search-offender">As Offender</button>
          <button class="btn btn-secondary btn-sm" id="search-punisher">As Punisher</button>
        </div>
        <label style="display:flex;align-items:center;gap:.35rem;font-size:.85rem">
          <input type="checkbox" id="show-removed" /> Show removed
        </label>
      </div>
      <div id="auttaja-results"></div>
    </div>`;

  function getUid() {
    const val = document.getElementById("auttaja-uid")?.value.trim();
    return val?.replace(/[<@!>]/g, "") || "";
  }

  async function doSearch(mode) {
    const uid = getUid();
    if (!uid) { toast("Enter a User ID.", "info"); return; }
    const showRemoved = document.getElementById("show-removed")?.checked;
    const results = document.getElementById("auttaja-results");
    results.innerHTML = '<div class="loader-wrap"><div class="loader"></div></div>';
    try {
      const data = mode === "offender"
        ? await api.offender(uid, { show_removed: showRemoved })
        : await api.punisher(uid, { show_removed: showRemoved });
      renderPunishments(results, data.punishments, uid);
    } catch (e) {
      results.innerHTML = `<div class="notice notice-warn">${e.message}</div>`;
    }
  }

  document.getElementById("search-offender")?.addEventListener("click", () => doSearch("offender"));
  document.getElementById("search-punisher")?.addEventListener("click", () => doSearch("punisher"));
  document.getElementById("auttaja-uid")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") doSearch("offender");
  });
}

function renderPunishments(container, punishments, uid) {
  if (!punishments.length) {
    container.innerHTML = `<p class="text-muted">No records found for user ${escHtml(uid)}.</p>`;
    return;
  }

  const breakdown = {};
  punishments.forEach((p) => { breakdown[p.action] = (breakdown[p.action] || 0) + 1; });

  container.innerHTML = `
    <div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:.75rem">
      ${Object.entries(breakdown).map(([action, cnt]) => `<span class="badge ${actionBadge(action)}">${escHtml(action)}: ${cnt}</span>`).join("")}
      <span class="badge badge-gray">Total: ${punishments.length}</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>#</th><th>Action</th><th>Offender</th><th>Punisher</th><th>Reason</th><th>Date</th><th>Actions</th></tr></thead>
        <tbody>
          ${punishments.map((p) => `
            <tr data-id="${p.id}">
              <td class="cell-id">${p.id}</td>
              <td><span class="badge ${actionBadge(p.action)}">${escHtml(p.action||"?")}</span></td>
              <td>${userIdHtml(p.offender||"")}</td>
              <td>${userIdHtml(p.punisher||"")}</td>
              <td style="max-width:200px"><span title="${escHtml(p.reason||"")}">${escHtml(truncate(p.reason||"—",50))}</span></td>
              <td class="text-muted" style="white-space:nowrap;font-size:.8rem">${fmtDate(p.timestamp)}</td>
              <td><button class="btn btn-secondary btn-sm edit-auttaja-btn" data-id="${p.id}">Edit</button></td>
            </tr>`).join("")}
        </tbody>
      </table>
    </div>`;

  container.querySelectorAll(".edit-auttaja-btn").forEach((btn) => {
    btn.addEventListener("click", () => openEditModal(btn.dataset.id));
  });
  setupCopyBtns(container);
  resolveUserNames(container);
}

async function openEditModal(id) {
  let p;
  try { p = await api.get(id); } catch (e) { toast(e.message, "error"); return; }
  const ACTIONS = ["ban","mute","kick","warn","softban","tempban","unban","unmute"];
  const html = `
    <form id="auttaja-edit-form">
      <div class="form-group"><label>Offender ID *</label><input name="offender" value="${escHtml(String(p.offender||""))}" required /></div>
      <div class="form-group"><label>Punisher ID *</label><input name="punisher" value="${escHtml(String(p.punisher||""))}" required /></div>
      <div class="form-group"><label>Action *</label>
        <select name="action">
          ${ACTIONS.map((a) => `<option value="${a}" ${p.action===a?"selected":""}>${a}</option>`).join("")}
        </select>
      </div>
      <div class="form-group"><label>Reason *</label><textarea name="reason" required>${escHtml(p.reason||"")}</textarea></div>
      <div style="display:flex;gap:.5rem;justify-content:flex-end;margin-top:.75rem">
        <button type="button" class="btn btn-secondary" id="ae-cancel">Cancel</button>
        <button type="submit" class="btn btn-primary">Save</button>
      </div>
    </form>`;
  openModal(`Edit Punishment #${id}`, html);
  document.getElementById("ae-cancel")?.addEventListener("click", () => closeModal(null));
  document.getElementById("auttaja-edit-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await api.update(id, { offender: fd.get("offender"), punisher: fd.get("punisher"), action: fd.get("action"), reason: fd.get("reason") });
      toast("Punishment updated.", "success"); closeModal(null);
    } catch (err) { toast(err.message, "error"); }
  });
}

async function renderLeaderboard(container) {
  container.innerHTML = `
    <div class="toolbar">
      <div class="toolbar-left">
        <button class="btn ${_lbMode==="offender"?"btn-primary":"btn-secondary"} btn-sm" data-mode="offender">Top Offenders</button>
        <button class="btn ${_lbMode==="punisher"?"btn-primary":"btn-secondary"} btn-sm" data-mode="punisher">Top Punishers</button>
      </div>
    </div>
    <div id="auttaja-lb"><div class="loader-wrap"><div class="loader"></div></div></div>`;

  container.querySelectorAll("[data-mode]").forEach((btn) => {
    btn.addEventListener("click", () => {
      _lbMode = btn.dataset.mode;
      container.querySelectorAll("[data-mode]").forEach((b) => {
        b.className = `btn ${b===btn?"btn-primary":"btn-secondary"} btn-sm`;
      });
      loadLb();
    });
  });

  async function loadLb() {
    const el = document.getElementById("auttaja-lb");
    if (!el) return;
    el.innerHTML = '<div class="loader-wrap"><div class="loader"></div></div>';
    try {
      const data = await api.leaderboard(_lbMode);
      if (!data.length) { el.innerHTML = '<p class="text-muted">No data.</p>'; return; }
      const medals = [
        `<img class="medal-svg" src="https://cdn.jsdelivr.net/npm/twemoji@14.0.2/assets/svg/1f947.svg" alt="🥇" />`,
        `<img class="medal-svg" src="https://cdn.jsdelivr.net/npm/twemoji@14.0.2/assets/svg/1f948.svg" alt="🥈" />`,
        `<img class="medal-svg" src="https://cdn.jsdelivr.net/npm/twemoji@14.0.2/assets/svg/1f949.svg" alt="🥉" />`,
      ];
      const medalClass = ["gold","silver","bronze"];
      el.innerHTML = `<div class="lb-list">${data.map((row,i) => `
        <div class="lb-row">
          <div class="lb-rank ${medalClass[i]||""}">${medals[i]||`#${i+1}`}</div>
          <div class="lb-user">${userIdHtml(row.user_id)}</div>
          <div class="lb-count">${row.count}</div>
        </div>`).join("")}
      </div>`;
      setupCopyBtns(el);
      resolveUserNames(el);
    } catch (e) {
      el.innerHTML = `<div class="notice notice-warn">${e.message}</div>`;
    }
  }

  loadLb();
}

function actionBadge(action) {
  const map = { ban:"badge-red", mute:"badge-yellow", kick:"badge-blue", warn:"badge-yellow", softban:"badge-purple", tempban:"badge-red", unban:"badge-green", unmute:"badge-green" };
  return map[action] || "badge-gray";
}

function fmtDate(str) {
  if (!str) return "—";
  try { return new Date(str).toLocaleDateString(undefined,{year:"numeric",month:"short",day:"numeric"}); } catch { return str; }
}
function escHtml(s) { return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function truncate(s,n) { return s&&s.length>n?s.slice(0,n)+"…":s; }
