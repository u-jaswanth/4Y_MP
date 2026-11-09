import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getTrends } from "../services/api";

/**
 * TrendsCard
 * ------------------------------------------------------------
 * "How have my numbers moved?" - one small chart per lab test, drawn
 * from every report the patient has uploaded. The shaded band behind
 * each line is the normal range printed on the latest report, so the
 * question "is that line in the good zone?" answers itself.
 *
 * Plain SVG, no chart library: nothing new to install.
 *
 * Dates are report upload dates (the API does not store the date a
 * sample was taken), so the wording says "reports", not "tests taken".
 */

const INITIAL_COUNT = 6;

const STATUS_LABEL = {
  high: "High",
  low: "Low",
  normal: "In range",
};


// ============================================================
// FORMATTING
// ============================================================

function formatNumber(value) {
  if (value === null || value === undefined) return "";
  return Number.isInteger(value) ? String(value) : String(+value.toFixed(2));
}

function shortDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
  });
}

function longDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function rangeText(test) {
  const { range_low: low, range_high: high, unit } = test;
  const suffix = unit ? ` ${unit}` : "";

  if (low !== null && high !== null) return `${formatNumber(low)}–${formatNumber(high)}${suffix}`;
  if (high !== null) return `up to ${formatNumber(high)}${suffix}`;
  if (low !== null) return `${formatNumber(low)} or more${suffix}`;
  return "";
}


// ============================================================
// THE CHART
// ============================================================

const W = 320;
const H = 116;
const PAD_X = 10;
const PAD_Y = 14;

function TrendChart({ test }) {

  const points = test.points;

  const [active, setActive] = useState(points.length - 1);

  const geometry = useMemo(() => {

    const values = points.map((p) => p.value);
    const dataMin = Math.min(...values);
    const dataMax = Math.max(...values);

    // Zoom to the data, not to the range: otherwise a value of 210
    // against a 150-450 range is a flat line hugging the floor.
    // The band is clipped to this window.
    const span = dataMax - dataMin;
    const pad = Math.max(span, Math.abs(dataMax) * 0.1, 1) * 0.6;
    const min = dataMin - pad;
    const max = dataMax + pad;

    const x = (i) =>
      PAD_X + (i * (W - PAD_X * 2)) / Math.max(points.length - 1, 1);

    const y = (v) =>
      PAD_Y + (1 - (v - min) / (max - min)) * (H - PAD_Y * 2);

    const clampY = (v) => Math.min(H - PAD_Y / 2, Math.max(PAD_Y / 2, y(v)));

    const low = test.range_low;
    const high = test.range_high;

    let band = null;

    if (low !== null || high !== null) {
      const top = high !== null ? clampY(high) : PAD_Y / 2;
      const bottom = low !== null ? clampY(low) : H - PAD_Y / 2;
      if (bottom > top) band = { top, height: bottom - top };
    }

    return {
      band,
      coords: points.map((p, i) => ({ x: x(i), y: y(p.value) })),
    };

  }, [points, test.range_low, test.range_high]);

  const { coords, band } = geometry;

  const path = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x} ${c.y}`).join(" ");

  function handleMove(event) {
    const box = event.currentTarget.getBoundingClientRect();
    const ratio = (event.clientX - box.left) / box.width;
    setActive(
      Math.min(points.length - 1, Math.max(0, Math.round(ratio * (points.length - 1))))
    );
  }

  function handleKey(event) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      setActive((i) => Math.max(0, i - 1));
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      setActive((i) => Math.min(points.length - 1, i + 1));
    }
  }

  const current = points[active];

  const summary =
    `${test.name}: ${points.length} readings from ${shortDate(points[0].date)} ` +
    `to ${shortDate(points[points.length - 1].date)}. Latest ` +
    `${formatNumber(points[points.length - 1].value)} ${test.unit}.`;

  return (

    <div
      className="trend-chart"
      tabIndex={0}
      role="group"
      aria-label={`${summary} Use the left and right arrow keys to move between readings.`}
      onMouseMove={handleMove}
      onMouseLeave={() => setActive(points.length - 1)}
      onKeyDown={handleKey}
    >

      <svg viewBox={`0 0 ${W} ${H}`} aria-hidden="true">

        {band && (
          <rect
            className="trend-band"
            x="0"
            y={band.top}
            width={W}
            height={band.height}
          />
        )}

        <path className="trend-line" d={path} />

        {coords.map((c, i) => (
          <circle
            key={i}
            className={`trend-dot trend-dot-${points[i].status || "none"}${i === active ? " is-active" : ""}`}
            cx={c.x}
            cy={c.y}
            r={i === active ? 5 : 3.2}
          />
        ))}

      </svg>

      <div
        className="trend-tooltip"
        style={{
          // Keep the bubble inside the tile at the first and last point.
          left: `${Math.min(84, Math.max(16, (coords[active].x / W) * 100))}%`,
        }}
      >
        <strong>
          {formatNumber(current.value)} {test.unit}
        </strong>
        <span>{longDate(current.date)}</span>
      </div>

      <div className="trend-axis" aria-hidden="true">
        <span>{shortDate(points[0].date)}</span>
        <span>{shortDate(points[points.length - 1].date)}</span>
      </div>

    </div>
  );
}


// ============================================================
// SINGLE READING - where the value sits against its normal range
// ============================================================

function RangeBar({ test, value, status }) {

  const low = test.range_low;
  const high = test.range_high;

  if (low === null && high === null) return null;

  const lo = Math.min(value, low ?? value, high ?? value);
  const hi = Math.max(value, low ?? value, high ?? value);
  const pad = Math.max(hi - lo, Math.abs(hi) * 0.2, 1) * 0.35;

  const min = lo - pad;
  const max = hi + pad;

  const pct = (v) => ((v - min) / (max - min)) * 100;

  const bandStart = low !== null ? pct(low) : 0;
  const bandEnd = high !== null ? pct(high) : 100;

  return (
    <div className="range-bar" aria-hidden="true">
      <div
        className="range-bar-band"
        style={{ left: `${bandStart}%`, width: `${bandEnd - bandStart}%` }}
      ></div>
      <div
        className={`range-bar-marker range-bar-marker-${status || "none"}`}
        style={{ left: `${pct(value)}%` }}
      ></div>
    </div>
  );
}


// ============================================================
// ONE TEST
// ============================================================

function TrendTile({ test }) {

  const points = test.points;
  const latest = points[points.length - 1];
  const previous = points.length > 1 ? points[points.length - 2] : null;

  const diff = previous ? latest.value - previous.value : 0;

  const direction = diff > 0 ? "up" : diff < 0 ? "down" : "flat";

  const range = rangeText(test);

  return (

    <article className={`trend-tile trend-tile-${latest.status || "none"}`}>

      <header className="trend-tile-head">

        <h4>{test.name}</h4>

        {latest.status && (
          <span className={`trend-status trend-status-${latest.status}`}>
            {STATUS_LABEL[latest.status]}
          </span>
        )}

      </header>

      <div className="trend-value-row">

        <span className="trend-value">{formatNumber(latest.value)}</span>

        {test.unit && <span className="trend-unit">{test.unit}</span>}

        {previous && (
          <span className={`trend-delta trend-delta-${direction}`}>
            <span aria-hidden="true">
              {direction === "up" ? "▲" : direction === "down" ? "▼" : "–"}
            </span>
            {direction === "flat"
              ? "No change"
              : `${formatNumber(Math.abs(diff))} since ${shortDate(previous.date)}`}
          </span>
        )}

      </div>

      {points.length > 1 ? (
        <TrendChart test={test} />
      ) : (
        <RangeBar test={test} value={latest.value} status={latest.status} />
      )}

      {range && (
        <p className="trend-range">
          <span className="trend-range-swatch" aria-hidden="true"></span>
          Normal range {range}
        </p>
      )}

    </article>
  );
}


// ============================================================
// THE CARD
// ============================================================

function TrendsCard() {

  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [filter, setFilter] = useState("all");
  const [showAll, setShowAll] = useState(false);

  async function load() {
    try {
      setLoading(true);
      setError("");
      setData(await getTrends());
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const tests = data ? data.tests : [];

  // Every test is shown. Ones seen in two or more reports get a
  // chart; the rest show where their one value sits in its range.
  const withHistory = tests.filter((t) => t.points.length > 1);
  const pool = tests;

  const isOut = (t) => t.latest_status === "high" || t.latest_status === "low";
  const outCount = pool.filter(isOut).length;

  const filtered = filter === "out" ? pool.filter(isOut) : pool;
  const visible = showAll ? filtered : filtered.slice(0, INITIAL_COUNT);

  let subtitle = "";
  if (data && tests.length > 0) {
    if (outCount > 0) {
      subtitle = `${outCount} of ${tests.length} ${outCount === 1 ? "value is" : "values are"} outside the normal range in your latest reports.`;
    } else {
      subtitle = `All ${tests.length} values are in range in your latest reports.`;
    }
  }

  return (

    <section className="dashboard-card trends-card" aria-labelledby="trends-title">

      <div className="trends-head">

        <div>
          <h3 id="trends-title">Health trends</h3>
          {subtitle && <p>{subtitle}</p>}
        </div>

        {!loading && !error && pool.length > 0 && outCount > 0 && (
          <div className="trends-filter" role="group" aria-label="Filter tests">
            <button
              type="button"
              aria-pressed={filter === "all"}
              className={filter === "all" ? "active" : ""}
              onClick={() => { setFilter("all"); setShowAll(false); }}
            >
              All
            </button>
            <button
              type="button"
              aria-pressed={filter === "out"}
              className={filter === "out" ? "active" : ""}
              onClick={() => { setFilter("out"); setShowAll(false); }}
            >
              Out of range ({outCount})
            </button>
          </div>
        )}

      </div>


      {loading ? (

        <div className="trends-grid" aria-busy="true">
          {[0, 1, 2].map((n) => (
            <div key={n} className="trend-tile trend-skeleton"></div>
          ))}
        </div>

      ) : error ? (

        <div className="trends-empty">
          <p>{error}</p>
          <button type="button" className="secondary-btn compact-btn" onClick={load}>
            Try again
          </button>
        </div>

      ) : tests.length === 0 ? (

        <div className="trends-empty">
          <p>
            {data && data.reports_analyzed > 0
              ? "No numeric results could be read from your reports yet."
              : "Upload a lab report and your results are charted here."}
          </p>
          <button
            type="button"
            className="primary-btn compact-btn"
            onClick={() => navigate("/reports")}
          >
            Upload a report
          </button>
        </div>

      ) : (

        <>

          <div className="trends-grid">
            {visible.map((test) => (
              <TrendTile key={test.name} test={test} />
            ))}
          </div>

          {filtered.length > INITIAL_COUNT && (
            <button
              type="button"
              className="show-more-btn"
              aria-expanded={showAll}
              onClick={() => setShowAll(!showAll)}
            >
              {showAll ? "Show fewer" : `Show all ${filtered.length} tests`}
              <span className="chevron" aria-hidden="true">▾</span>
            </button>
          )}

          <p className="trends-foot">
            {withHistory.length > 0
              ? `${withHistory.length} of ${tests.length} tests appear in more than one report and show a trend. Tests found in a single report show only their latest value.`
              : "Upload another report that includes the same tests to see how your values change."}
          </p>

        </>

      )}

    </section>
  );
}

export default TrendsCard;
