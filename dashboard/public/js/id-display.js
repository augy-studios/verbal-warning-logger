import { utility } from "./api.js";

const COPY_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;
const CHECK_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>`;

const _nameCache = {};

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export function copyBtnHtml(value) {
  return `<button class="copy-id-btn" type="button" data-copy="${esc(String(value))}" title="Copy to clipboard">${COPY_SVG}</button>`;
}

// ID cell with async Discord username lookup
export function userIdHtml(uid) {
  if (!uid && uid !== 0) return `<span class="cell-mono">—</span>`;
  const str = String(uid);
  return `<span class="id-with-name"><span class="cell-mono">${esc(str)}</span>${copyBtnHtml(str)}<span class="id-name text-muted" data-uid-name="${esc(str)}"></span></span>`;
}

// ID cell with a known name (channels, roles, etc.)
export function idWithNameHtml(id, name) {
  if (!id && id !== 0) return `<span class="cell-mono">—</span>`;
  const nameStr = name ? `<span class="id-name text-muted">${esc(String(name))}</span>` : "";
  return `<span class="id-with-name"><span class="cell-mono">${esc(String(id))}</span>${copyBtnHtml(id)}${nameStr}</span>`;
}

export function setupCopyBtns(container) {
  container.querySelectorAll(".copy-id-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const text = btn.dataset.copy;
      try {
        await navigator.clipboard.writeText(text);
        btn.innerHTML = CHECK_SVG;
        btn.classList.add("copy-id-btn--done");
        setTimeout(() => {
          if (btn.isConnected) {
            btn.innerHTML = COPY_SVG;
            btn.classList.remove("copy-id-btn--done");
          }
        }, 1500);
      } catch {}
    });
  });
}

export function resolveUserNames(container) {
  const els = container.querySelectorAll("[data-uid-name]");
  const toFetch = new Map();

  els.forEach((el) => {
    const uid = el.dataset.uidName;
    if (uid in _nameCache) {
      if (_nameCache[uid]) el.textContent = _nameCache[uid];
    } else {
      if (!toFetch.has(uid)) toFetch.set(uid, []);
      toFetch.get(uid).push(el);
    }
  });

  Promise.allSettled(
    [...toFetch.entries()].map(async ([uid, uidEls]) => {
      try {
        const u = await utility.user(uid);
        _nameCache[uid] = u.username;
        uidEls.forEach((el) => { if (el.isConnected) el.textContent = u.username; });
      } catch {
        _nameCache[uid] = "";
      }
    })
  );
}
