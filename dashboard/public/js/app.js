import { consumeTokenFromHash, fetchCurrentUser, isLoggedIn, logout } from "./auth.js";
import { initTheme, initThemePicker } from "./theme.js";
import { initRouter, register } from "./router.js";
import * as home      from "./pages/home.js";
import * as warnings  from "./pages/warnings.js";
import * as polls     from "./pages/polls.js";
import * as templates from "./pages/templates.js";
import * as auttaja   from "./pages/auttaja.js";
import * as utility   from "./pages/utility.js";

// ── Service Worker ───────────────────────────────────────────────────────
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

// ── Toast system ─────────────────────────────────────────────────────────
const ICONS = {
  success: `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`,
  error:   `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
  info:    `<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
};

export function toast(message, type = "info", title = "") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.innerHTML = `${ICONS[type] || ICONS.info}<div class="toast-body">${title ? `<div class="toast-title">${title}</div>` : ""}<div>${message}</div></div>`;
  container.appendChild(el);
  setTimeout(() => {
    el.classList.add("out");
    el.addEventListener("animationend", () => el.remove());
  }, 3500);
}

// ── Modal system ─────────────────────────────────────────────────────────
let _modalResolve = null;

export function openModal(title, html, opts = {}) {
  const backdrop = document.getElementById("modal-backdrop");
  const box      = document.getElementById("modal-box");
  const titleEl  = document.getElementById("modal-title");
  const body     = document.getElementById("modal-body");
  if (!backdrop || !box) return;

  titleEl.textContent = title;
  body.innerHTML = html;
  if (opts.wide) box.classList.add("modal-wide"); else box.classList.remove("modal-wide");
  backdrop.classList.remove("hidden");
  return new Promise((res) => { _modalResolve = res; });
}

export function closeModal(value) {
  const backdrop = document.getElementById("modal-backdrop");
  if (backdrop) backdrop.classList.add("hidden");
  if (_modalResolve) { _modalResolve(value); _modalResolve = null; }
}

export function confirmModal(message, title = "Confirm") {
  return openModal(title, `
    <div class="confirm-box">
      <p>${message}</p>
      <div class="confirm-actions">
        <button class="btn btn-secondary" id="confirm-cancel">Cancel</button>
        <button class="btn btn-danger" id="confirm-ok">Confirm</button>
      </div>
    </div>
  `).then((v) => v === true);
}

// ── Main init ─────────────────────────────────────────────────────────────
async function init() {
  initTheme();

  // Handle OAuth callback token
  const tokenResult = consumeTokenFromHash();
  if (tokenResult && tokenResult.error) {
    showLogin(`Login failed: ${tokenResult.error.replace(/_/g, " ")}`);
    return;
  }
  if (tokenResult === true) return; // Page will reload

  if (!isLoggedIn()) {
    showLogin();
    return;
  }

  const user = await fetchCurrentUser();
  if (!user) {
    showLogin("Session expired. Please log in again.");
    return;
  }

  showApp(user);
}

function showLogin(error) {
  document.getElementById("login-screen").classList.remove("hidden");
  if (error) {
    const el = document.getElementById("login-error");
    if (el) { el.textContent = error; el.classList.remove("hidden"); }
  }
}

function showApp(user) {
  document.getElementById("login-screen").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");

  // Set user info in sidebar
  const avatar = document.getElementById("user-avatar");
  const name   = document.getElementById("user-name");
  if (avatar) avatar.src = user.avatar_url;
  if (name)   name.textContent = user.username;

  // Register pages
  register("dashboard", home);
  register("warnings",  warnings);
  register("polls",     polls);
  register("templates", templates);
  register("auttaja",   auttaja);
  register("utility",   utility);

  initThemePicker();
  initRouter();
  initModalClose();
  initSidebar();

  // Logout
  document.getElementById("logout-btn")?.addEventListener("click", async () => {
    await logout();
    window.location.reload();
  });
}

function initModalClose() {
  const backdrop = document.getElementById("modal-backdrop");
  const close    = document.getElementById("modal-close");

  close?.addEventListener("click", () => closeModal(null));
  backdrop?.addEventListener("click", (e) => {
    if (e.target === backdrop) closeModal(null);
  });
  backdrop?.addEventListener("click", (e) => {
    const ok = e.target.closest("#confirm-ok");
    const cancel = e.target.closest("#confirm-cancel");
    if (ok)     closeModal(true);
    if (cancel) closeModal(false);
  });
}

function initSidebar() {
  const toggle  = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("sidebar");
  toggle?.addEventListener("click", () => sidebar?.classList.toggle("open"));
}

init().catch(console.error);
