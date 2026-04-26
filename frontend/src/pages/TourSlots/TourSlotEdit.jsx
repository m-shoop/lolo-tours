import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { getSlotAvailability } from "../../api/bookings";
import { runReport } from "../../api/reports";
import { createTourSlot, updateTourSlot } from "../../api/tourSlots";
import {
  juneauLocalToUtcIso,
  utcIsoToJuneauLocal,
} from "../../utils/juneauTime";
import styles from "./TourSlots.module.css";

function centsToDollars(cents) {
  return (cents / 100).toFixed(2);
}

function dollarsToCents(dollars) {
  const n = parseFloat(dollars);
  if (!Number.isFinite(n)) return null;
  return Math.round(n * 100);
}

const STATUSES = ["scheduled", "cancelled", "completed"];

// Business hours bracket the time dropdown. Outside this range, a loaded
// value is still preserved (added to the option list as a one-off).
const TIME_START_HOUR = 0;
const TIME_END_HOUR = 23;
const TIME_STEP_MINUTES = 5;

const STANDARD_TIME_OPTIONS = (() => {
  const out = [];
  for (let h = TIME_START_HOUR; h <= TIME_END_HOUR; h++) {
    for (let m = 0; m < 60; m += TIME_STEP_MINUTES) {
      out.push(`${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`);
    }
  }
  return out;
})();

function formatTimeLabel(value) {
  const [h, m] = value.split(":").map(Number);
  const hour12 = ((h + 11) % 12) + 1;
  const ampm = h < 12 ? "AM" : "PM";
  return `${hour12}:${String(m).padStart(2, "0")} ${ampm}`;
}

function timeOptionsIncluding(extraTime) {
  if (!extraTime || STANDARD_TIME_OPTIONS.includes(extraTime)) {
    return STANDARD_TIME_OPTIONS;
  }
  return [...STANDARD_TIME_OPTIONS, extraTime].sort();
}

export default function TourSlotEdit({ mode }) {
  const { slotId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [tours, setTours] = useState([]);
  const [tourId, setTourId] = useState(searchParams.get("tour_id") ?? "");
  const [dateLocal, setDateLocal] = useState("");
  const [timeLocal, setTimeLocal] = useState("");
  const [capacity, setCapacity] = useState("");
  const [priceDollars, setPriceDollars] = useState("");
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState("scheduled");
  // Snapshot of the saved values, used to detect unsaved edits in edit mode.
  // null until first load completes.
  const [original, setOriginal] = useState(null);
  // In edit mode: # of participants holding seats on this slot. Drives the
  // "existing bookings keep their current price" warning when price is dirty.
  const [seatsTaken, setSeatsTaken] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  const selectedTour = useMemo(
    () => tours.find((t) => t.id === tourId),
    [tours, tourId]
  );

  const timeOptions = useMemo(
    () => timeOptionsIncluding(timeLocal),
    [timeLocal]
  );

  const hasChanges = useMemo(() => {
    if (mode !== "edit" || !original) return true;
    return (
      dateLocal !== original.dateLocal ||
      timeLocal !== original.timeLocal ||
      capacity !== original.capacity ||
      priceDollars !== original.priceDollars ||
      notes !== original.notes ||
      status !== original.status
    );
  }, [
    mode,
    original,
    dateLocal,
    timeLocal,
    capacity,
    priceDollars,
    notes,
    status,
  ]);

  const priceIsDirty =
    mode === "edit" && original && priceDollars !== original.priceDollars;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const toursData = await runReport("tours", {
          filters: {
            logic: "AND",
            conditions: [{ field: "is_active", op: "equals", value: true }],
          },
          columns: ["id", "name", "max_capacity", "price_per_person"],
          page_size: 200,
        });
        if (cancelled) return;
        setTours(toursData.rows);

        if (mode === "edit" && slotId) {
          const slotData = await runReport("tour-slots", {
            filters: {
              logic: "AND",
              conditions: [{ field: "id", op: "equals", value: slotId }],
            },
            columns: [
              "id",
              "tour_id",
              "tour_name",
              "start_time",
              "capacity",
              "price_per_participant_cents",
              "status",
              "notes",
            ],
            page_size: 1,
          });
          if (cancelled) return;
          const row = slotData.rows[0];
          if (!row) {
            setError("Slot not found");
          } else {
            setTourId(row.tour_id);
            const [d, t] = utcIsoToJuneauLocal(row.start_time).split("T");
            const loadedCapacity = String(row.capacity);
            const loadedPriceDollars = centsToDollars(
              row.price_per_participant_cents
            );
            const loadedNotes = row.notes ?? "";
            setDateLocal(d);
            setTimeLocal(t);
            setCapacity(loadedCapacity);
            setPriceDollars(loadedPriceDollars);
            setNotes(loadedNotes);
            setStatus(row.status);
            setOriginal({
              dateLocal: d,
              timeLocal: t,
              capacity: loadedCapacity,
              priceDollars: loadedPriceDollars,
              notes: loadedNotes,
              status: row.status,
            });

            // Background fetch for the "existing bookings keep current
            // price" warning. Failure is silent — the warning just won't
            // appear, which is no worse than not having it.
            getSlotAvailability(slotId)
              .then((a) => !cancelled && setSeatsTaken(a.taken))
              .catch(() => {});
          }
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [mode, slotId]);

  // When the user picks a template (in create mode), pre-fill capacity and
  // price from the template's defaults if the user hasn't typed them yet.
  useEffect(() => {
    if (mode !== "create" || !selectedTour) return;
    if (capacity === "") {
      setCapacity(String(selectedTour.max_capacity));
    }
    if (priceDollars === "") {
      setPriceDollars(centsToDollars(selectedTour.price_per_person));
    }
  }, [mode, selectedTour, capacity, priceDollars]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setNotice(null);

    if (!tourId) { setError("Pick a tour template"); return; }
    if (!dateLocal || !timeLocal) { setError("Set a start date and time"); return; }
    const cap = Number(capacity);
    if (!Number.isInteger(cap) || cap <= 0) {
      setError("Capacity must be a positive integer");
      return;
    }
    const priceCents = dollarsToCents(priceDollars);
    if (priceCents === null || priceCents < 0) {
      setError("Price must be a non-negative number");
      return;
    }

    const startIso = juneauLocalToUtcIso(`${dateLocal}T${timeLocal}`);

    setSaving(true);
    try {
      if (mode === "create") {
        const created = await createTourSlot({
          tour_id: tourId,
          start_time: startIso,
          capacity: cap,
          price_per_participant_cents: priceCents,
          notes: notes || null,
        });
        navigate(`/admin/tour-slots/${created.id}`, { replace: true });
        setNotice("Slot created.");
      } else {
        await updateTourSlot(slotId, {
          start_time: startIso,
          capacity: cap,
          price_per_participant_cents: priceCents,
          notes: notes || null,
          status,
        });
        setOriginal({
          dateLocal,
          timeLocal,
          capacity,
          priceDollars,
          notes,
          status,
        });
        setNotice("Saved.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className={styles.page}>Loading…</div>;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>
          {mode === "create" ? "New tour slot" : "Edit tour slot"}
        </h1>
        <Link to="/admin/tour-slots" className={styles.secondaryBtn}>
          ← Back
        </Link>
      </div>

      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.formRow}>
          <label htmlFor="tour">Tour template</label>
          <div>
            <select
              id="tour"
              className={styles.select}
              value={tourId}
              onChange={(e) => setTourId(e.target.value)}
              disabled={mode === "edit"}
              required
            >
              <option value="">— Select a tour —</option>
              {tours.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} (max {t.max_capacity})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className={styles.formRow}>
          <label htmlFor="date">Start time (Juneau)</label>
          <div>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              <input
                id="date"
                type="date"
                className={styles.input}
                value={dateLocal}
                onChange={(e) => setDateLocal(e.target.value)}
                required
              />
              <select
                id="time"
                className={styles.select}
                value={timeLocal}
                onChange={(e) => setTimeLocal(e.target.value)}
                required
              >
                <option value="">— Select time —</option>
                {timeOptions.map((t) => (
                  <option key={t} value={t}>
                    {formatTimeLabel(t)}
                  </option>
                ))}
              </select>
            </div>
            <div className={styles.hint}>
              Times are entered and shown in America/Juneau. They're stored as UTC.
            </div>
          </div>
        </div>

        <div className={styles.formRow}>
          <label htmlFor="capacity">Capacity</label>
          <input
            id="capacity"
            className={styles.input}
            type="number"
            min="1"
            required
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
          />
        </div>

        <div className={styles.formRow}>
          <label htmlFor="price">Price per participant ($)</label>
          <div>
            <input
              id="price"
              className={styles.input}
              type="number"
              min="0"
              step="0.01"
              required
              value={priceDollars}
              onChange={(e) => setPriceDollars(e.target.value)}
            />
            {mode === "create" && (
              <div className={styles.hint}>
                Pre-filled from the tour template. Edit to override for this
                slot only.
              </div>
            )}
            {priceIsDirty && seatsTaken > 0 && (
              <div className={styles.hint}>
                Existing bookings on this slot ({seatsTaken} seat
                {seatsTaken === 1 ? "" : "s"}) will keep their current price
                of ${original.priceDollars}. The new price applies to future
                bookings only.
              </div>
            )}
          </div>
        </div>

        <div className={styles.formRow}>
          <label htmlFor="notes">Notes</label>
          <textarea
            id="notes"
            className={styles.textarea}
            maxLength={500}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>

        {mode === "edit" && (
          <div className={styles.formRow}>
            <label htmlFor="status">Status</label>
            <select
              id="status"
              className={styles.select}
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        )}

        {error && <div className={styles.error}>{error}</div>}
        {notice && <div className={styles.success}>{notice}</div>}

        <div className={styles.actions}>
          <Link to="/admin/tour-slots" className={styles.secondaryBtn}>
            Cancel
          </Link>
          <button
            type="submit"
            className={styles.primaryBtn}
            disabled={saving || !hasChanges}
          >
            {saving ? "Saving…" : mode === "create" ? "Create" : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}
