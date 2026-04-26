import { apiFetch } from "./apiFetch";

function authHeaders() {
  const token = localStorage.getItem("lolo_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function jsonOrThrow(res) {
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export async function createTourSlot(payload) {
  const res = await apiFetch("/api/tour-slots", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return jsonOrThrow(res);
}

export async function updateTourSlot(slotId, payload) {
  const res = await apiFetch(`/api/tour-slots/${slotId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return jsonOrThrow(res);
}
