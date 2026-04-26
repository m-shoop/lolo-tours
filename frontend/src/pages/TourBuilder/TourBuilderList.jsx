import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { runReport } from "../../api/reports";
import { useAuth } from "../../context/AuthContext";
import styles from "./TourBuilder.module.css";

function formatPrice(cents) {
  return `$${(cents / 100).toFixed(2)}`;
}

export default function TourBuilderList() {
  const { can } = useAuth();
  const canCreateSlot = can("tour-slot:edit");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    runReport("tours", { sort_by: ["name"], sort_dir: "asc", page_size: 100 })
      .then((data) => !cancelled && setRows(data.rows))
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, []);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Tour Builder</h1>
        <Link to="/admin/tours/new" className={styles.primaryBtn}>
          + New tour template
        </Link>
      </div>

      {loading && <p>Loading…</p>}
      {error && <p className={styles.error}>{error}</p>}

      {!loading && !error && rows.length === 0 && (
        <p>No tours yet. Click "New tour template" to create one.</p>
      )}

      <div className={styles.grid}>
        {rows.map((row) => (
          <div key={row.id} className={styles.card}>
            <Link
              to={`/admin/tours/${row.id}`}
              style={{ color: "inherit", textDecoration: "none" }}
            >
              <div className={styles.cardThumb}>
                {row.thumbnail_url ? (
                  <img
                    src={`/tour-images/${row.thumbnail_url}`}
                    alt={row.thumbnail_alt ?? ""}
                  />
                ) : (
                  <span>No image</span>
                )}
              </div>
              <div className={styles.cardBody}>
                <div className={styles.cardTitle}>{row.name}</div>
                <span
                  className={`${styles.badge} ${
                    row.is_active ? styles.badgeActive : styles.badgeInactive
                  }`}
                >
                  {row.is_active ? "Active" : "Inactive"}
                </span>
                <div className={styles.cardMeta}>
                  {row.duration_minutes} min · max {row.max_capacity} ·{" "}
                  {formatPrice(row.price_per_person)}
                </div>
              </div>
            </Link>
            {canCreateSlot && row.is_active && (
              <div style={{ padding: "0 1rem 1rem" }}>
                <Link
                  to={`/admin/tour-slots/new?tour_id=${row.id}`}
                  className={styles.secondaryBtn}
                  style={{ display: "block", textAlign: "center" }}
                >
                  + Create tour slot
                </Link>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
