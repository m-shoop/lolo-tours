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
  return res.status === 204 ? null : res.json();
}

export async function createTour(payload) {
  const res = await apiFetch("/api/tours", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return jsonOrThrow(res);
}

export async function getTour(tourId) {
  const res = await apiFetch(`/api/tours/${tourId}`, {
    headers: {...authHeaders() },
  });
  return jsonOrThrow(res);
}

export async function updateTour(tourId, payload) {
  const res = await apiFetch(`/api/tours/${tourId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return jsonOrThrow(res);
}

export async function listTourImages(tourId) {
  const res = await apiFetch(`/api/tours/${tourId}/images`, {
    headers: { ...authHeaders() },
  });
  return jsonOrThrow(res);
}

export async function uploadTourImage(tourId, file, { imageAlt, sortOrder = 0, useAsThumbnail = false }) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("image_alt", imageAlt);
  fd.append("sort_order", String(sortOrder));
  fd.append("use_as_thumbnail", String(useAsThumbnail));

  const res = await apiFetch(`/api/tours/${tourId}/images`, {
    method: "POST",
    headers: { ...authHeaders() },
    body: fd,
  });
  return jsonOrThrow(res);
}

export async function updateTourImage(tourId, imageId, payload) {
  const res = await apiFetch(`/api/tours/${tourId}/images/${imageId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });
  return jsonOrThrow(res);
}

export async function deleteTourImage(tourId, imageId) {
  const res = await apiFetch(`/api/tours/${tourId}/images/${imageId}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  return jsonOrThrow(res);
}
