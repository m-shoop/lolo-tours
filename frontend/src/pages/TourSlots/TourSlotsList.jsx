import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { runReport } from "../../api/reports";
import { useAuth } from "../../context/AuthContext";
import { formatJuneau } from "../../utils/juneauTime";
import styles from "./TourSlots.module.css";

function statusBadgeClass(status) {
  if (status === "scheduled") return styles.badgeScheduled;
  if (status === "cancelled") return styles.badgeCancelled;
  if (status === "completed") return styles.badgeCompleted;
  return "";
}

export default function TourSlotsList() {
  const { can } = useAuth();
  const canEdit = can("tour-slot:edit");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const now = new Date().toISOString();
    const in30 = new Date(Date.now() + 30 * 24 * 3600 * 1000).toISOString();

    runReport("tour-slots", {
      filters: {
        logic: "AND",
        conditions: [
          { field: "start_time", op: "between", value: [now, in30] },
        ],
      },
      sort_by: ["start_time"],
      sort_dir: "asc",
      page_size: 200,
    })
      .then((data) => !cancelled && setRows(data.rows))
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, []);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Tour Slots</h1>
        <p className={styles.cardMeta} style={{ flex: 1 }}>
          Showing the next 30 days
        </p>
      </div>

      {loading && <p>Loading…</p>}
      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.grid}>
        {canEdit && (
          <Link to="/admin/tour-slots/new" className={styles.addCard}>
            + Add new tour slot
          </Link>
        )}
        {rows.map((row) => (
          <Link
            key={row.id}
            to={canEdit ? `/admin/tour-slots/${row.id}` : "#"}
            className={styles.card}
            onClick={canEdit ? undefined : (e) => e.preventDefault()}
          >
            <div className={styles.cardTitle}>{row.tour_name}</div>
            <div className={styles.cardTime}>{formatJuneau(row.start_time)}</div>
            <div className={styles.cardMeta}>Capacity: {row.capacity}</div>
            <span className={`${styles.badge} ${statusBadgeClass(row.status)}`}>
              {row.status}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
