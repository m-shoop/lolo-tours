import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getBookingByCode } from "../api/bookings";
import { formatJuneau } from "../utils/juneauTime";

const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 60_000;
const TERMINAL_PAYMENTS = new Set(["paid", "refunded"]);
const TERMINAL_BOOKINGS = new Set(["cancelled"]);

function isTerminal(b) {
  return (
    TERMINAL_PAYMENTS.has(b.payment_status) ||
    TERMINAL_BOOKINGS.has(b.booking_status)
  );
}

function useCountdown(expiresAtIso) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!expiresAtIso) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [expiresAtIso]);
  if (!expiresAtIso) return null;
  const ms = new Date(expiresAtIso).getTime() - now;
  if (ms <= 0) return "expired";
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

export default function Confirmation() {
  const [params] = useSearchParams();
  const code = params.get("code");
  const sessionId = params.get("session_id");
  const [booking, setBooking] = useState(null);
  const [error, setError] = useState(null);
  const startRef = useRef(Date.now());

  useEffect(() => {
    if (!code) {
      setError("Missing booking reference.");
      return;
    }
    let cancelled = false;
    let timer;

    async function tick() {
      try {
        const b = await getBookingByCode(code, sessionId);
        if (cancelled) return;
        setBooking(b);
        const elapsed = Date.now() - startRef.current;
        if (
          b.payment_status === "paid" ||
          isTerminal(b) ||
          elapsed >= POLL_TIMEOUT_MS
        ) {
          return;
        }
        timer = setTimeout(tick, POLL_INTERVAL_MS);
      } catch (e) {
        if (!cancelled) setError(e.message);
      }
    }

    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [code, sessionId]);

  const countdown = useCountdown(booking?.expires_at);

  if (!code) return <p className="error">Missing booking reference.</p>;
  if (error) return <p className="error">{error}</p>;
  if (!booking) return <p>Loading your booking&hellip;</p>;

  const isPaid = booking.payment_status === "paid";
  const isCancelled = booking.booking_status === "cancelled";
  const lead = booking.participants.find((p) => p.is_lead);

  let statusLine;
  if (isPaid) {
    statusLine = (
      <p className="confirmation-status status-paid">
        ✓ Booking confirmed! Confirmation #{booking.code}
      </p>
    );
  } else if (isCancelled) {
    statusLine = (
      <p className="confirmation-status status-cancelled">
        This booking was cancelled.
      </p>
    );
  } else {
    statusLine = (
      <p className="confirmation-status status-pending">
        Processing your payment&hellip; we&apos;ll email you once it&apos;s
        verified.
      </p>
    );
  }

  return (
    <section className="page page-confirmation">
      <div className="confirmation-card">
        {statusLine}
        {isPaid && lead?.email && (
          <p className="muted">A receipt will be emailed to {lead.email}.</p>
        )}
        {!isPaid && !isCancelled && countdown && (
          <p className="countdown">
            Payment must complete within {countdown}.
          </p>
        )}
        <hr />
        <p>
          <strong>Booking code:</strong> {booking.code}
          <br />
          <strong>Status:</strong> {booking.booking_status} /{" "}
          {booking.payment_status}
          <br />
          <strong>Total:</strong> $
          {(booking.total_amount_cents / 100).toFixed(2)}
        </p>
        {isCancelled && (
          <p>
            <Link to="/schedule" className="btn">
              Try again
            </Link>
          </p>
        )}
        <p className="muted" style={{ fontSize: "0.85rem" }}>
          You can close this page. Use the booking code above (plus the lead
          email) on the{" "}
          <Link to="/booking-lookup">booking lookup</Link> page to revisit
          this booking later.
        </p>
        {booking.created_at && (
          <p className="muted" style={{ fontSize: "0.8rem" }}>
            Created {formatJuneau(booking.created_at)}.
          </p>
        )}
      </div>
    </section>
  );
}
