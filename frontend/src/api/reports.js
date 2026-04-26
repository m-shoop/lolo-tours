import { apiFetch } from "./apiFetch";

function authHeaders() {
  const token = localStorage.getItem("lolo_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function runReport(reportId, requestBody = {}) {
  const res = await apiFetch(`/api/reports/${reportId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(requestBody),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Report request failed");
  }
  return res.json();
}
