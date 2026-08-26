const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function request(path, options) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
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
