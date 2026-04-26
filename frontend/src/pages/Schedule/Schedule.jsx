import { useEffect, useState } from "react";
import { listToursWithAvailability } from "../../api/bookings";
import TourDetail from "./TourDetail";
import TourList from "./TourList";

export default function Schedule() {
  const [guests, setGuests] = useState(2);
  const [tours, setTours] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTour, setSelectedTour] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    listToursWithAvailability(guests)
      .then(setTours)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [guests]);

  if (selectedTour) {
    return (
      <TourDetail
        tour={selectedTour}
        guests={guests}
        onBack={() => setSelectedTour(null)}
      />
    );
  }

  return (
    <section className="page page-schedule">
      <h1>Find &amp; Book a Tour</h1>
      <div className="schedule-controls">
        <label htmlFor="guests-input">Guests</label>
        <input
          id="guests-input"
          type="number"
          min="1"
          max="50"
          value={guests}
          onChange={(e) =>
            setGuests(Math.max(1, Number(e.target.value) || 1))
          }
        />
        <span className="muted push-right">
          Tours that can&apos;t fit your party are dimmed.
        </span>
      </div>
      {loading && <p>Loading tours&hellip;</p>}
      {error && <p className="error">Could not load tours: {error}</p>}
      {!loading && !error && (
        <TourList tours={tours} onSelect={setSelectedTour} />
      )}
    </section>
  );
}
