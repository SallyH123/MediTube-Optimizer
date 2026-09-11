const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const API_PATH_PREFIX = window.location.pathname.startsWith("/cutoff-demo") ? "/demo" : "";
const API_QUERY = API_PATH_PREFIX ? window.location.search : "";

async function request(path, options) {
  const response = await fetch(`${API_BASE_URL}${API_PATH_PREFIX}${path}${API_QUERY}`, options);
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.error || `Request failed (${response.status})`);
  }

  return payload;
}

export function getBoard() {
  return request("/bins");
}

export function tubeBin(binId) {
  return request(`/bins/${encodeURIComponent(binId)}/tube`, { method: "POST" });
}

export function forceTubeBin(binId) {
  return request(`/bins/${encodeURIComponent(binId)}/force-tube`, { method: "POST" });
}

export function refreshSimulation() {
  return request("/simulation/refresh", { method: "POST" });
}
