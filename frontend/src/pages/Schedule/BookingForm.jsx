import { useEffect, useMemo, useState } from "react";
import { createBooking, getSlotAvailability } from "../../api/bookings";
import { formatJuneau } from "../../utils/juneauTime";

function blankParticipant(isLead = false) {
  return { name: "", email: "", is_lead: isLead };
}

export default function BookingForm({
  tour,
  slot,
  guests,
  onBack,
  onCancelToList,
}) {
  const [participants, setParticipants] = useState(() => {
    const arr = [blankParticipant(true)];
    for (let i = 1; i < guests; i++) arr.push(blankParticipant(false));
    return arr;
  });
  const [specialRequests, setSpecialRequests] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [availability, setAvailability] = useState({
    available: slot.available,
    capacity: slot.capacity,
  });

  const numParticipants = participants.length;
  const totalCents = useMemo(
    () => slot.price_per_participant_cents * numParticipants,
    [slot.price_per_participant_cents, numParticipants]
  );

  // Live capacity check whenever the count changes. Informational only —
  // the transactional check happens on submit.
  useEffect(() => {
    let cancelled = false;
    const handle = setTimeout(() => {
      getSlotAvailability(slot.id)
        .then((d) => !cancelled && setAvailability(d))
        .catch(() => {});
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [slot.id, numParticipants]);

  function updateParticipant(index, field, value) {
    setParticipants((prev) =>
      prev.map((p, i) => (i === index ? { ...p, [field]: value } : p))
    );
  }

  function addParticipant() {
    if (numParticipants >= 50) return;
    setParticipants((prev) => [...prev, blankParticipant(false)]);
  }

  function removeParticipant(index) {
    if (participants[index].is_lead) return; // can't remove lead
    if (numParticipants <= 1) return;
    setParticipants((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    const lead = participants[0];
    if (!lead.name.trim() || !lead.email.trim()) {
      setError("Lead participant requires a name and email.");
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        tour_slot_id: slot.id,
        participants: participants.map((p, i) => ({
          name: p.name.trim() || (i === 0 ? "" : `Guest ${i}`),
          email: p.email.trim() || null,
          is_lead: i === 0,
        })),
        special_requests: specialRequests.trim() || null,
      };
      const resp = await createBooking(payload);
      // Hand off to the payment provider (or in the shell, straight to /confirmation).
      window.location.href = resp.redirect_url;
    } catch (err) {
      setSubmitting(false);
      if (err.status === 409 && err.detail?.error === "capacity_exceeded") {
        setError(
          `Only ${err.detail.available} seats left on this slot — please reduce your party size.`
        );
      } else {
        setError(err.message);
      }
    }
  }

  const overCapacity = numParticipants > availability.available;

  return (
    <section className="page page-booking">
      <p>
        <button type="button" className="btn btn-secondary" onClick={onBack}>
          &larr; Back to times
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={onCancelToList}
          style={{ marginLeft: "0.5rem" }}
        >
          Start over
        </button>
      </p>

      <h1>Confirm your booking</h1>
      <p className="tour-meta">
        <strong>{tour.name}</strong> &middot; {formatJuneau(slot.start_time)}
      </p>

      <form className="booking-form" onSubmit={handleSubmit}>
        <h2>Lead participant</h2>
        <div className="participant-row">
          <div className="field">
            <label htmlFor="lead-name">Name</label>
            <input
              id="lead-name"
              required
              value={participants[0].name}
              onChange={(e) => updateParticipant(0, "name", e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="lead-email">Email</label>
            <input
              id="lead-email"
              required
              type="email"
              value={participants[0].email}
              onChange={(e) => updateParticipant(0, "email", e.target.value)}
            />
          </div>
          <div />
        </div>

        {participants.length > 1 && (
          <>
            <h2>Additional guests</h2>
            <p className="muted" style={{ marginTop: 0, fontSize: "0.85rem" }}>
              Optional. Add a name and email if you&apos;d like us to email
              that guest separately.
            </p>
          </>
        )}
        {participants.slice(1).map((p, idx) => {
          const i = idx + 1;
          return (
            <div className="participant-row" key={i}>
              <div className="field">
                <label htmlFor={`p-name-${i}`}>Name (optional)</label>
                <input
                  id={`p-name-${i}`}
                  placeholder={`Guest ${i}`}
                  value={p.name}
                  onChange={(e) =>
                    updateParticipant(i, "name", e.target.value)
                  }
                />
              </div>
              <div className="field">
                <label htmlFor={`p-email-${i}`}>Email (optional)</label>
                <input
                  id={`p-email-${i}`}
                  type="email"
                  value={p.email}
                  onChange={(e) =>
                    updateParticipant(i, "email", e.target.value)
                  }
                />
              </div>
              <button
                type="button"
                className="btn-remove"
                onClick={() => removeParticipant(i)}
                aria-label={`Remove guest ${i}`}
              >
                ✕
              </button>
            </div>
          );
        })}
        <div className="field-inline" style={{ marginBottom: "1rem" }}>
          <button type="button" className="btn btn-secondary" onClick={addParticipant}>
            + Add guest
          </button>
          <span className="muted">
            {numParticipants} {numParticipants === 1 ? "person" : "people"} —{" "}
            {availability.available} seat
            {availability.available === 1 ? "" : "s"} available on this slot
          </span>
        </div>

        <div className="field">
          <label htmlFor="special-requests">Special requests (optional)</label>
          <textarea
            id="special-requests"
            rows={3}
            maxLength={2000}
            value={specialRequests}
            onChange={(e) => setSpecialRequests(e.target.value)}
            placeholder="Accessibility, dietary, or any notes for the guide"
          />
        </div>

        <div className="price-row">
          <span>Total</span>
          <span>${(totalCents / 100).toFixed(2)}</span>
        </div>

        {overCapacity && (
          <p className="error">
            Not enough seats for {numParticipants} guests on this slot.
          </p>
        )}
        {error && <p className="error">{error}</p>}

        <button
          type="submit"
          className="btn"
          disabled={submitting || overCapacity}
        >
          {submitting ? "Redirecting…" : "Proceed to Payment"}
        </button>
      </form>
    </section>
  );
}
