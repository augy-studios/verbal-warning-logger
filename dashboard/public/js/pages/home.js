import { warnings as warnApi, polls as pollsApi, utility as utilApi } from "../api.js";

export function render() {
  return `
    <div class="stats-grid" id="stats-grid">
      ${[1,2,3,4].map(() => `<div class="stat-card"><div class="stat-label">Loading…</div><div class="stat-value">—</div></div>`).join("")}
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1rem;margin-top:1.25rem">
      <div class="card" id="recent-warnings-card">
        <div class="card-title">Recent Warnings</div>
        <div class="loader-wrap"><div class="loader"></div></div>
      </div>
      <div class="card" id="guild-card">
        <div class="card-title">Server Info</div>
        <div class="loader-wrap"><div class="loader"></div></div>
      </div>
    </div>`;
}

export async function init() {
  const [warnStats, pollStats, guildInfo] = await Promise.allSettled([
    warnApi.stats(),
    pollsApi.stats(),
    utilApi.guild(),
  ]);

  const ws = warnStats.status === "fulfilled" ? warnStats.value : null;
  const ps = pollStats.status  === "fulfilled" ? pollStats.value  : null;
  const gi = guildInfo.status  === "fulfilled" ? guildInfo.value  : null;

  document.getElementById("stats-grid").innerHTML = `
    <div class="stat-card">
      <div class="stat-label">Total Warnings</div>
      <div class="stat-value">${ws?.total ?? "—"}</div>
      <div class="stat-sub">+${ws?.last_7_days ?? "—"} this week</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Active Polls</div>
      <div class="stat-value">${ps?.active ?? "—"}</div>
      <div class="stat-sub">${ps?.total ?? "—"} total</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Total Votes Cast</div>
      <div class="stat-value">${ps?.total_votes ?? "—"}</div>
      <div class="stat-sub">across all polls</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Server Members</div>
      <div class="stat-value">${gi?.member_count ? gi.member_count.toLocaleString() : "—"}</div>
      <div class="stat-sub">${gi?.name ?? ""}</div>
    </div>`;

  // Recent warnings
  const rwCard = document.getElementById("recent-warnings-card");
  try {
    const { items } = await warnApi.list({ page: 1, per_page: 5 });
    if (!items.length) {
      rwCard.innerHTML = `<div class="card-title">Recent Warnings</div><p class="text-muted">No warnings yet.</p>`;
    } else {
      rwCard.innerHTML = `<div class="card-title">Recent Warnings</div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>#</th><th>User ID</th><th>Reason</th><th>Date</th></tr></thead>
            <tbody>
              ${items.map((w) => `
                <tr>
                  <td class="cell-id">${w.id}</td>
                  <td class="cell-mono">${w.userId}</td>
                  <td>${escHtml(truncate(w.reason, 40))}</td>
                  <td class="text-muted" style="white-space:nowrap">${fmtDate(w.createdAt)}</td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>
        <div style="margin-top:.75rem"><a class="btn btn-ghost btn-sm" href="#/warnings">View all →</a></div>`;
    }
  } catch {
    rwCard.innerHTML = `<div class="card-title">Recent Warnings</div><p class="text-muted">Could not load warnings.</p>`;
  }

  // Guild card
  const gCard = document.getElementById("guild-card");
  if (gi) {
    const iconUrl = gi.icon
      ? `https://cdn.discordapp.com/icons/${gi.id}/${gi.icon}.png`
      : null;
    gCard.innerHTML = `<div class="card-title">Server Info</div>
      <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.75rem">
        ${iconUrl ? `<img src="${iconUrl}" style="width:3rem;height:3rem;border-radius:50%"/>` : ""}
        <div>
          <div style="font-weight:600;color:var(--brand-text)">${escHtml(gi.name)}</div>
          <div class="text-muted">ID: ${gi.id}</div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.4rem;font-size:.85rem">
        <div class="text-muted">Members</div><div>${gi.member_count?.toLocaleString() ?? "—"}</div>
        <div class="text-muted">Online</div><div>${gi.online_count?.toLocaleString() ?? "—"}</div>
      </div>`;
  } else {
    gCard.innerHTML = `<div class="card-title">Server Info</div><p class="text-muted">Could not load guild info.</p>`;
  }
}

function fmtDate(str) {
  if (!str) return "";
  return new Date(str.replace(" ", "T") + "Z").toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function escHtml(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function truncate(s, n) {
  return s && s.length > n ? s.slice(0, n) + "…" : s;
}
