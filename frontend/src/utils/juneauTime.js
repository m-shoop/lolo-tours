/**
 * Lolo Tours runs in Juneau, Alaska (America/Juneau). All `start_time` values
 * are stored as UTC. The admin UI accepts and displays Juneau wall-clock time.
 *
 * These helpers bridge between:
 *   - the browser's `<input type="datetime-local">` value (a naive local string)
 *   - the API's UTC ISO 8601 string
 *
 * The conversion uses Intl.DateTimeFormat to compute the actual Juneau offset
 * for the given instant, which handles DST transitions correctly except for
 * the ambiguous hour at fall-back (where we accept whichever offset Intl picks).
 */
const JUNEAU_TZ = "America/Juneau";

function getJuneauOffsetMinutes(utcDate) {
  // Returns minutes to add to UTC to get Juneau wall time. Negative because
  // Juneau is behind UTC (e.g. -480 in DST, -540 in standard time).
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: JUNEAU_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const parts = Object.fromEntries(
    fmt.formatToParts(utcDate).map((p) => [p.type, p.value])
  );
  const asLocalUtc = Date.UTC(
    Number(parts.year),
    Number(parts.month) - 1,
    Number(parts.day),
    Number(parts.hour) % 24,
    Number(parts.minute),
    Number(parts.second)
  );
  return Math.round((asLocalUtc - utcDate.getTime()) / 60000);
}

/**
 * "2026-05-15T14:30" (intended as Juneau wall time) → UTC ISO string.
 */
export function juneauLocalToUtcIso(localStr) {
  if (!localStr) return null;
  // Start with the assumption that the local string is UTC. That gives us a
  // reference instant, from which we look up the actual Juneau offset and
  // shift back. (Doing it this way handles DST without hard-coding offsets.)
  const naive = new Date(`${localStr}:00Z`);
  const offsetMinutes = getJuneauOffsetMinutes(naive);
  const utcMs = naive.getTime() - offsetMinutes * 60000;
  return new Date(utcMs).toISOString();
}

/**
 * UTC ISO string → "2026-05-15T14:30" suitable for `<input type="datetime-local">`.
 */
export function utcIsoToJuneauLocal(isoStr) {
  if (!isoStr) return "";
  const utc = new Date(isoStr);
  const fmt = new Intl.DateTimeFormat("en-CA", {
    timeZone: JUNEAU_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const parts = Object.fromEntries(
    fmt.formatToParts(utc).map((p) => [p.type, p.value])
  );
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour === "24" ? "00" : parts.hour}:${parts.minute}`;
}

/**
 * Pretty-print a UTC ISO timestamp in Juneau time, e.g. "May 15, 2026, 2:30 PM AKDT".
 */
export function formatJuneau(isoStr) {
  if (!isoStr) return "";
  return new Intl.DateTimeFormat("en-US", {
    timeZone: JUNEAU_TZ,
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(new Date(isoStr));
}
