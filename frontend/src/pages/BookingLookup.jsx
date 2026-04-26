import { useState } from "react";
import { Link } from "react-router-dom";
import {
  cancelBooking,
  lookupBooking,
  updateBooking,
} from "../api/bookings";
import { formatJuneau } from "../utils/juneauTime";

export default function BookingLookup() {
  const [code, setCode] = useState("");
  const [email, setEmail] = useState("");
  const [booking, setBooking] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleLookup(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const b = await lookupBooking(code.trim().toUpperCase(), email.trim());
      setBooking(b);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (booking) {
    return (
      <BookingDetail
        booking={booking}
        email={email}
        onUpdated={setBooking}
        onReset={() => {
          setBooking(null);
          setCode("");
          setEmail("");
        }}
      />
    );
  }

  return (
    <section className="page page-lookup">
      <div className="lookup-card">
        <h1>Look up your booking</h1>
        <form onSubmit={handleLookup}>
          <div className="field">
            <label htmlFor="lookup-code">Booking code</label>
            <input
              id="lookup-code"
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              maxLength={8}
              minLength={8}
              placeholder="e.g. ABCD2345"
              style={{ textTransform: "uppercase" }}
            />
          </div>
          <div className="field">
            <label htmlFor="lookup-email">Lead email</label>
            <input
              id="lookup-email"
              required
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          {error && <p className="error">{error}</p>}
          <button type="submit" className="btn" disabled={submitting}>
            {submitting ? "Looking up…" : "Find booking"}
          </button>
        </form>
        <p className="muted" style={{ marginTop: "1rem", fontSize: "0.85rem" }}>
          The booking code was shown on your confirmation page after payment.
        </p>
      </div>
    </section>
  );
}

function BookingDetail({ booking, email, onUpdated, onReset }) {
  const [specialRequests, setSpecialRequests] = useState(
    booking.special_requests || ""
  );
  const [participants, setParticipants] = useState(booking.participants);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  const editable =
    booking.booking_status === "pending" &&
    booking.payment_status === "unpaid";

  function updatePart(idx, field, value) {
    setParticipants((prev) =>
      prev.map((p, i) => (i === idx ? { ...p, [field]: value } : p))
    );
  }

  async function handleSave() {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await updateBooking(booking.code, {
        auth: { email },
        special_requests: specialRequests.trim() || null,
        participants: participants.map((p) => ({
          id: p.id,
          name: p.name,
          email: p.email,
        })),
      });
      onUpdated(updated);
      setNotice("Saved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel() {
    if (!window.confirm("Cancel this booking? This cannot be undone.")) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await cancelBooking(booking.code, { email });
      onUpdated(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page page-lookup">
      <div className="lookup-card">
        <p>
          <button type="button" className="btn btn-secondary" onClick={onReset}>
            &larr; Look up another
          </button>
        </p>
        <h1>Booking #{booking.code}</h1>
        <p>
          <strong>Status:</strong> {booking.booking_status} /{" "}
          {booking.payment_status}
          <br />
          <strong>Total:</strong> $
          {(booking.total_amount_cents / 100).toFixed(2)}
        </p>
        {booking.expires_at && (
          <p className="countdown">
            Pending payment expires {formatJuneau(booking.expires_at)}.
          </p>
        )}

        {!editable && (
          <p className="muted">
            This booking is no longer editable. To request a refund or change a
            paid booking, please contact us.
          </p>
        )}

        <h2>Participants</h2>
        {participants.map((p, idx) => (
          <div className="participant-row" key={p.id}>
            <div className="field">
              <label>Name {p.is_lead && "(lead)"}</label>
              <input
                value={p.name || ""}
                disabled={!editable}
                onChange={(e) => updatePart(idx, "name", e.target.value)}
              />
            </div>
            <div className="field">
              <label>Email</label>
              <input
                type="email"
                value={p.email || ""}
                disabled={!editable}
                onChange={(e) => updatePart(idx, "email", e.target.value)}
              />
            </div>
            <div />
          </div>
        ))}

        <div className="field">
          <label htmlFor="lookup-special">Special requests</label>
          <textarea
            id="lookup-special"
            rows={3}
            disabled={!editable}
            value={specialRequests}
            onChange={(e) => setSpecialRequests(e.target.value)}
          />
        </div>

        {error && <p className="error">{error}</p>}
        {notice && <p className="muted">{notice}</p>}

        {editable && (
          <div className="field-inline">
            <button
              type="button"
              className="btn"
              disabled={busy}
              onClick={handleSave}
            >
              Save changes
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={busy}
              onClick={handleCancel}
            >
              Cancel booking
            </button>
          </div>
        )}

        <p style={{ marginTop: "1.5rem" }}>
          <Link to="/schedule">Back to schedule</Link>
        </p>
      </div>
    </section>
  );
}
