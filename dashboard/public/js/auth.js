import { auth } from "./api.js";

const KEY = "vigila_token";

export function getToken() {
  return localStorage.getItem(KEY);
}

export function setToken(token) {
  localStorage.setItem(KEY, token);
}

export function clearToken() {
  localStorage.removeItem(KEY);
}

export function isLoggedIn() {
  const token = getToken();
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}

export async function fetchCurrentUser() {
  try {
    return await auth.me();
  } catch {
    return null;
  }
}

export async function logout() {
  try { await auth.logout(); } catch { /* ignore */ }
  clearToken();
}

/** Parse token from URL hash after OAuth callback and persist it. */
export function consumeTokenFromHash() {
  const hash = window.location.hash;
  const match = hash.match(/[?&]token=([^&]+)/);
  if (match) {
    const token = match[1];
    setToken(token);
    // Strip token from URL
    const cleanHash = hash.replace(/[?&]token=[^&]+/, "").replace(/[?&]$/, "");
    window.location.replace(window.location.pathname + cleanHash || "#/dashboard");
    return true;
  }

  const errMatch = hash.match(/[?&]error=([^&]+)/);
  if (errMatch) {
    return { error: decodeURIComponent(errMatch[1]) };
  }

  return false;
}
