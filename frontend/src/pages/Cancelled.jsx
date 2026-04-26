import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { cancelBooking } from "../api/bookings";

export default function Cancelled() {
  const [params] = useSearchParams();
  const code = params.get("code");
  const sessionId = params.get("session_id");
  const [state, setState] = useState("cancelling");

  useEffect(() => {
    if (!code || !sessionId) {
      setState("missing");
      return;
    }
    let cancelled = false;
    cancelBooking(code, { session_id: sessionId })
      .then(() => !cancelled && setState("done"))
      .catch(() => !cancelled && setState("error"));
    return () => {
      cancelled = true;
    };
  }, [code, sessionId]);

  return (
    <section className="page page-cancelled">
      <div className="confirmation-card">
        <p className="confirmation-status status-cancelled">
          Booking not completed.
        </p>
        {state === "cancelling" && (
          <p className="muted">Releasing your seats&hellip;</p>
        )}
        {state === "done" && (
          <p className="muted">
            Your seats have been released. No charge was made.
          </p>
        )}
        {state === "error" && (
          <p className="muted">
            (Could not auto-release seats; they will be released
            automatically within 30 minutes.)
          </p>
        )}
        {state === "missing" && (
          <p className="muted">No booking reference found.</p>
        )}
        <p>
          <Link to="/schedule" className="btn">
            Return to schedule
          </Link>
        </p>
      </div>
    </section>
  );
}
