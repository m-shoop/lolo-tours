export default function TourList({ tours, onSelect }) {
  if (tours.length === 0) {
    return <p>No tours available yet. Check back soon.</p>;
  }
  // Available first, unavailable at the end (and dimmed).
  const sorted = [...tours].sort((a, b) => {
    const aAvail = a.has_available_capacity !== false;
    const bAvail = b.has_available_capacity !== false;
    if (aAvail === bAvail) return a.name.localeCompare(b.name);
    return aAvail ? -1 : 1;
  });
  return (
    <ul className="tour-list">
      {sorted.map((tour) => {
        const available = tour.has_available_capacity !== false;
        return (
          <li
            key={tour.id}
            className={`tour-card${available ? "" : " unavailable"}`}
          >
            <div className="tour-card-header">
              <h2>{tour.name}</h2>
              <span className="tour-meta">
                ${(tour.price_per_person / 100).toFixed(2)} / person
              </span>
            </div>
            {tour.description && <p>{tour.description}</p>}
            <p className="tour-meta">
              {tour.duration_minutes} min &middot; up to {tour.max_capacity}{" "}
              guests
            </p>
            {available ? (
              <button
                type="button"
                className="btn"
                onClick={() => onSelect(tour)}
              >
                See times
              </button>
            ) : (
              <p className="muted">No available time slots.</p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
