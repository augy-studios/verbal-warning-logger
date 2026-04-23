const routes = new Map();
let currentRoute = null;

export function register(path, module) {
  routes.set(path, module);
}

export function navigate(path) {
  window.location.hash = `#/${path}`;
}

async function render(path) {
  const module = routes.get(path) || routes.get("dashboard");
  if (!module) return;

  const titleMap = {
    dashboard:  "Dashboard",
    warnings:   "Verbal Warnings",
    polls:      "Polls",
    templates:  "Poll Templates",
    auttaja:    "Auttaja History",
    utility:    "Utility",
  };

  const pageTitle = document.getElementById("page-title");
  const pageBody  = document.getElementById("page-body");
  if (pageTitle) pageTitle.textContent = titleMap[path] || path;
  if (pageBody) pageBody.innerHTML = '<div class="loader-wrap"><div class="loader"></div></div>';

  // Update nav active state
  document.querySelectorAll(".nav-link").forEach((link) => {
    link.classList.toggle("active", link.dataset.route === path);
  });

  currentRoute = path;

  try {
    if (typeof module.render === "function") {
      const html = await module.render();
      if (pageBody) pageBody.innerHTML = html;
    }
    if (typeof module.init === "function") {
      await module.init();
    }
  } catch (err) {
    if (pageBody) {
      pageBody.innerHTML = `<div class="card"><p class="text-muted">Failed to load page: ${err.message}</p></div>`;
    }
  }
}

export function initRouter() {
  async function handleHash() {
    const hash = window.location.hash.replace("#/", "").split("?")[0];
    const path = hash || "dashboard";
    await render(path);
  }

  window.addEventListener("hashchange", handleHash);
  handleHash();
}

export function currentPage() {
  return currentRoute;
}
