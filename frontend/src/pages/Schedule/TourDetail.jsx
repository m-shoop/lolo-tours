import { useEffect, useMemo, useState } from "react";
import { listSlotsForTour } from "../../api/bookings";
import { listTourImages } from "../../api/tours";
import { formatJuneau } from "../../utils/juneauTime";
import BookingForm from "./BookingForm";

const JUNEAU_TZ = "America/Juneau";

function juneauDateKey(isoStr) {
  const fmt = new Intl.DateTimeFormat("en-CA", {
    timeZone: JUNEAU_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  const parts = Object.fromEntries(
    fmt.formatToParts(new Date(isoStr)).map((p) => [p.type, p.value])
  );
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function juneauDayLabel(isoStr) {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: JUNEAU_TZ,
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(new Date(isoStr));
}

function juneauTimeShort(isoStr) {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: JUNEAU_TZ,
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(isoStr));
}

export default function TourDetail({ tour, guests, onBack }) {
  const [slots, setSlots] = useState([]);
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [openDays, setOpenDays] = useState(new Set());
  const [jumpDate, setJumpDate] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([listSlotsForTour(tour.id, { guests }), listTourImages(tour.id)])
      .then(([slotData, imgData]) => {
        if (cancelled) return;
        setSlots(slotData);
        setImages(imgData);
        // Open the first day by default for convenience.
        if (slotData.length > 0) {
          setOpenDays(new Set([juneauDateKey(slotData[0].start_time)]));
        }
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [tour.id, guests]);

  const dayGroups = useMemo(() => {
    const groups = new Map();
    for (const s of slots) {
      const key = juneauDateKey(s.start_time);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(s);
    }
    return Array.from(groups.entries()).map(([key, items]) => ({
      key,
      label: juneauDayLabel(items[0].start_time),
      items,
    }));
  }, [slots]);

  const availableDateKeys = useMemo(
    () => new Set(dayGroups.map((g) => g.key)),
    [dayGroups]
  );

  function toggleDay(key) {
    setOpenDays((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function handleJump(e) {
    const value = e.target.value;
    setJumpDate(value);
    if (availableDateKeys.has(value)) {
      setOpenDays(new Set([value]));
      requestAnimationFrame(() => {
        const el = document.getElementById(`slot-day-${value}`);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }

  if (selectedSlot) {
    return (
      <BookingForm
        tour={tour}
        slot={selectedSlot}
        guests={guests}
        onBack={() => setSelectedSlot(null)}
        onCancelToList={onBack}
      />
    );
  }

  const thumbnailFirst = [...images].sort(
    (a, b) =>
      Number(b.use_as_thumbnail) - Number(a.use_as_thumbnail) ||
      a.sort_order - b.sort_order
  );

  return (
    <section className="page page-tour-detail">
      <p>
        <button type="button" className="btn-secondary btn" onClick={onBack}>
          &larr; All tours
        </button>
      </p>
      <h1>{tour.name}</h1>
      <p className="tour-meta">
        {tour.duration_minutes} min &middot; ${(tour.price_per_person / 100).toFixed(2)}{" "}
        per person
      </p>

      <div className="tour-detail-panels">
        <div className="tour-photos">
          {thumbnailFirst.length > 0 ? (
            thumbnailFirst.map((img) => (
              <img
                key={img.id}
                src={img.image_url}
                alt={img.image_alt}
              />
            ))
          ) : (
            <p className="muted">No photos yet.</p>
          )}
          {tour.description && <p>{tour.description}</p>}
        </div>

        <div className="tour-times">
          <div className="date-jumper field">
            <label htmlFor="jump-date">Jump to date</label>
            <input
              id="jump-date"
              type="date"
              value={jumpDate}
              onChange={handleJump}
              list="available-dates"
            />
            <datalist id="available-dates">
              {Array.from(availableDateKeys).map((k) => (
                <option key={k} value={k} />
              ))}
            </datalist>
          </div>

          {loading && <p>Loading times&hellip;</p>}
          {error && <p className="error">{error}</p>}
          {!loading && !error && dayGroups.length === 0 && (
            <p>No upcoming times for {guests} guests.</p>
          )}

          {dayGroups.map((g) => (
            <div
              key={g.key}
              className="slot-day"
              id={`slot-day-${g.key}`}
            >
              <button
                type="button"
                className="slot-day-header"
                onClick={() => toggleDay(g.key)}
                aria-expanded={openDays.has(g.key)}
              >
                <span>{g.label}</span>
                <span>{openDays.has(g.key) ? "−" : "+"}</span>
              </button>
              {openDays.has(g.key) && (
                <ul className="slot-day-list">
                  {g.items.map((s) => (
                    <li key={s.id} className="slot-row">
                      <div>
                        <div className="slot-time">
                          {juneauTimeShort(s.start_time)}
                        </div>
                        <div className="slot-availability">
                          {s.available} of {s.capacity} seats left
                        </div>
                      </div>
                      <button
                        type="button"
                        className="btn"
                        onClick={() => setSelectedSlot(s)}
                      >
                        Book
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}

          <p className="tz-note">
            All times shown in Juneau local time (America/Juneau).
          </p>
        </div>
      </div>
    </section>
  );
}
