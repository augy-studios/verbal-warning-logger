const BASE = "/api";

function getToken() {
  return localStorage.getItem("vigila_token");
}

async function request(method, path, body) {
  const token = getToken();
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (resp.status === 401) {
    localStorage.removeItem("vigila_token");
    window.location.hash = "#/login";
    throw new Error("Unauthorized");
  }

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }

  if (resp.status === 204) return null;
  return resp.json();
}

const get  = (path)        => request("GET",    path);
const post = (path, body)  => request("POST",   path, body);
const put  = (path, body)  => request("PUT",    path, body);
const del  = (path)        => request("DELETE", path);

export const auth = {
  me:     ()     => get("/auth/me"),
  logout: ()     => post("/auth/logout"),
};

export const warnings = {
  list:        (params = {}) => get(`/warnings?${new URLSearchParams(params)}`),
  get:         (id)          => get(`/warnings/${id}`),
  create:      (body)        => post("/warnings", body),
  update:      (id, body)    => put(`/warnings/${id}`, body),
  delete:      (id)          => del(`/warnings/${id}`),
  stats:       ()            => get("/warnings/stats"),
  leaderboard: (mode)        => get(`/warnings/leaderboard?mode=${mode}`),
};

export const polls = {
  list:    (params = {}) => get(`/polls?${new URLSearchParams(params)}`),
  get:     (id)          => get(`/polls/${id}`),
  create:  (body)        => post("/polls", body),
  update:  (id, body)    => put(`/polls/${id}`, body),
  close:   (id)          => del(`/polls/${id}`),
  reopen:  (id)          => post(`/polls/${id}/reopen`),
  results: (id)          => get(`/polls/${id}/results`),
  stats:   ()            => get("/polls/stats"),
};

export const templates = {
  list:       (params = {}) => get(`/poll-templates?${new URLSearchParams(params)}`),
  get:        (id)          => get(`/poll-templates/${id}`),
  create:     (body)        => post("/poll-templates", body),
  update:     (id, body)    => put(`/poll-templates/${id}`, body),
  delete:     (id)          => del(`/poll-templates/${id}`),
  restore:    (id)          => post(`/poll-templates/${id}/restore`),
  use:        (id, body)    => post(`/poll-templates/${id}/use`, body),
  fromPoll:   (pollId)      => post(`/poll-templates/from-poll/${pollId}`),
};

export const auttaja = {
  offender:   (userId, params = {}) => get(`/auttaja/offender/${userId}?${new URLSearchParams(params)}`),
  punisher:   (userId, params = {}) => get(`/auttaja/punisher/${userId}?${new URLSearchParams(params)}`),
  leaderboard: (mode)               => get(`/auttaja/leaderboard?mode=${mode}`),
  get:         (id)                 => get(`/auttaja/${id}`),
  update:      (id, body)           => put(`/auttaja/${id}`, body),
};

export const utility = {
  ping:        ()             => get("/utility/ping"),
  guild:       ()             => get("/utility/guild"),
  user:        (id)           => get(`/utility/discord/user/${id}`),
  channels:    (params = {})  => get(`/utility/channels?${new URLSearchParams(params)}`),
  roles:       ()             => get("/utility/roles"),
  members:     (params = {})  => get(`/utility/members?${new URLSearchParams(params)}`),
  warningIds:  (mode)         => get(`/utility/warning-ids?mode=${mode}`),
};
