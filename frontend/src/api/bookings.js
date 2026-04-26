async function jsonOrThrow(res) {
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const detail = data.detail;
    const msg =
      typeof detail === "string"
        ? detail
        : detail?.error || `Request failed (${res.status})`;
    const err = new Error(msg);
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  return res.status === 204 ? null : res.json();
}

export async function listToursWithAvailability(guests) {
  const url = guests
    ? `/api/tours?guests=${encodeURIComponent(guests)}`
    : "/api/tours";
  const res = await fetch(url);
  return jsonOrThrow(res);
}

export async function listSlotsForTour(tourId, { guests, from, to } = {}) {
  const params = new URLSearchParams();
  if (guests) params.set("guests", String(guests));
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  const qs = params.toString();
  const res = await fetch(
    `/api/tours/${tourId}/slots${qs ? `?${qs}` : ""}`
  );
  return jsonOrThrow(res);
}

export async function getSlotAvailability(slotId) {
  const res = await fetch(`/api/tour-slots/${slotId}/availability`);
  return jsonOrThrow(res);
}

export async function createBooking(payload) {
  const res = await fetch("/api/bookings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return jsonOrThrow(res);
}

export async function getBookingByCode(code, sessionId) {
  const url = sessionId
    ? `/api/bookings/${code}?session_id=${encodeURIComponent(sessionId)}`
    : `/api/bookings/${code}`;
  const res = await fetch(url);
  return jsonOrThrow(res);
}

export async function lookupBooking(code, email) {
  const res = await fetch("/api/bookings/lookup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, email }),
  });
  return jsonOrThrow(res);
}

export async function updateBooking(code, payload) {
  const res = await fetch(`/api/bookings/${code}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return jsonOrThrow(res);
}

export async function cancelBooking(code, auth) {
  const res = await fetch(`/api/bookings/${code}/cancel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ auth }),
  });
  return jsonOrThrow(res);
}
