// The server stores UTC without a zone marker. Add one so the browser
// shows local time, and trim microseconds to milliseconds because
// Safari rejects 6-digit fractions.

export function formatDateTime(value) {

  if (!value) {
    return "";
  }

  const trimmed = String(value).replace(/(\.\d{3})\d+/, "$1");

  const iso = /Z|[+-]\d\d:?\d\d$/.test(trimmed) ? trimmed : `${trimmed}Z`;

  return new Date(iso).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
