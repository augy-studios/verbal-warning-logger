const THEMES = ["classic", "notgreen1", "notgreen2", "notgreen3", "notgreen4", "notgreen5", "white"];
const THEME_COLORS = {
  classic:   "#ccffcc",
  notgreen1: "#ffcccc",
  notgreen2: "#ccccff",
  notgreen3: "#ffffcc",
  notgreen4: "#ffccff",
  notgreen5: "#ccffff",
  white:     "#ffffff",
};

const KEY = "vigila_theme";

export function getTheme() {
  return localStorage.getItem(KEY) || "classic";
}

export function applyTheme(name) {
  if (!THEMES.includes(name)) name = "classic";
  document.documentElement.setAttribute("data-theme", name);
  const color = THEME_COLORS[name];
  const meta = document.getElementById("meta-theme-color");
  if (meta) meta.setAttribute("content", color);
  localStorage.setItem(KEY, name);
}

export function initTheme() {
  applyTheme(getTheme());
}

export function initThemePicker() {
  const modal = document.getElementById("theme-modal");
  const btn   = document.getElementById("theme-btn");
  const close = document.getElementById("theme-modal-close");
  const grid  = document.getElementById("theme-grid");

  if (!modal || !btn || !grid) return;

  function open() {
    modal.classList.remove("hidden");
    // Mark active swatch
    const current = getTheme();
    grid.querySelectorAll(".theme-swatch").forEach((s) => {
      s.classList.toggle("active", s.dataset.theme === current);
    });
  }

  function closeModal() { modal.classList.add("hidden"); }

  btn.addEventListener("click", open);
  close.addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });

  grid.addEventListener("click", (e) => {
    const swatch = e.target.closest(".theme-swatch");
    if (!swatch) return;
    applyTheme(swatch.dataset.theme);
    grid.querySelectorAll(".theme-swatch").forEach((s) => {
      s.classList.toggle("active", s === swatch);
    });
  });
}
