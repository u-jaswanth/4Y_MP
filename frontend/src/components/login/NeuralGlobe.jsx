import { useEffect, useRef } from "react";

/**
 * NeuralGlobe
 * ------------------------------------------------------------
 * The one piece of art on the sign-in stage: a slowly turning globe
 * of connected nodes, with a few pulses of light travelling along its
 * lines. Drawn on a canvas, no text, no data - it stands for the
 * platform as a connected whole and nothing more.
 *
 *  - colour follows --mc-pulse, so it shifts with the selected portal
 *  - leans a few degrees toward the pointer (reads --mx / --my that
 *    Login.jsx writes on the stage)
 *  - reduced-motion: draws a single still frame
 */

const N = 210;

function seeded(seed) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296;
    return s / 4294967296;
  };
}

// Built once: points on a sphere (Fibonacci spiral = even spread),
// each linked to its three nearest neighbours.
const rnd = seeded(7);
const POINTS = [];
const golden = Math.PI * (3 - Math.sqrt(5));
for (let i = 0; i < N; i++) {
  const y = 1 - (i / (N - 1)) * 2;
  const r = Math.sqrt(1 - y * y);
  const t = golden * i;
  POINTS.push({ x: Math.cos(t) * r, y, z: Math.sin(t) * r, hub: i % 19 === 0, ph: rnd() * 6.28, lon: Math.atan2(Math.sin(t) * r, Math.cos(t) * r) });
}

const EDGES = [];
const NEIGH = POINTS.map(() => []);
{
  const seen = new Set();
  POINTS.forEach((p, i) => {
    POINTS.map((q, j) => ({ j, d: (p.x - q.x) ** 2 + (p.y - q.y) ** 2 + (p.z - q.z) ** 2 }))
      .filter((o) => o.j !== i)
      .sort((a, b) => a.d - b.d)
      .slice(0, 3)
      .forEach(({ j }) => {
        const key = i < j ? i + "-" + j : j + "-" + i;
        if (seen.has(key)) return;
        seen.add(key);
        EDGES.push([i, j]);
        NEIGH[i].push(j);
        NEIGH[j].push(i);
      });
  });
}

function readColor(el) {
  const v = getComputedStyle(el).getPropertyValue("--mc-pulse");
  const m = v.match(/[\d.]+/g);
  return m && m.length >= 3 ? [+m[0], +m[1], +m[2]] : [94, 211, 196];
}

function NeuralGlobe({ pulseKey = 0 }) {
  const ripples = useRef([]);
  const wrap = useRef(null);
  const canvas = useRef(null);

  // each new statement sends one ripple out from the globe
  useEffect(() => {
    if (pulseKey > 0) ripples.current.push(0);
  }, [pulseKey]);

  useEffect(() => {
    const box = wrap.current;
    const cv = canvas.current;
    if (!box || !cv) return undefined;

    const ctx = cv.getContext("2d");
    const stage = cv.closest(".mc-stage");
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let w = 0;
    let h = 0;
    let dpr = 1;
    let yaw = 0.6;
    let lx = 0;
    let ly = 0;
    let last = 0;
    let raf = 0;
    let color = [94, 211, 196];
    let tick = 0;

    const packets = Array.from({ length: 11 }, (_, i) => {
      const a = Math.floor(rnd() * N);
      return { a, b: NEIGH[a][0], t: rnd(), v: 0.16 + (i % 4) * 0.04 };
    });

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = box.clientWidth;
      h = box.clientHeight;
      cv.width = Math.max(1, Math.round(w * dpr));
      cv.height = Math.max(1, Math.round(h * dpr));
      if (still) draw(0);
    }

    const rgba = (a) => `rgba(${color[0]|0},${color[1]|0},${color[2]|0},${a})`;

    function draw(dt) {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);

      const compact = h < 340;
      const R = compact ? Math.min(w * 0.36, h * 0.38) : Math.min(w * 0.32, h * 0.29);
      const cx = compact ? w / 2 : w * 0.64;
      const cy = compact ? h / 2 : h * 0.8;

      if (!still) {
        const mx = parseFloat(stage?.style.getPropertyValue("--mx")) || 0;
        const my = parseFloat(stage?.style.getPropertyValue("--my")) || 0;
        lx += (mx - lx) * 0.05;
        ly += (my - ly) * 0.05;
        yaw += dt * 0.09;
      }

      const tilt = 0.42 + ly * 0.07;
      const cY = Math.cos(yaw + lx * 0.22), sY = Math.sin(yaw + lx * 0.22);
      const cT = Math.cos(tilt), sT = Math.sin(tilt);

      // a bright meridian sweeps around the globe
      const scan = still ? 1.1 : tick * 0.75;

      // projected positions
      const P = POINTS.map((p) => {
        const x1 = p.x * cY + p.z * sY;
        const z1 = -p.x * sY + p.z * cY;
        const y2 = p.y * cT - z1 * sT;
        const z2 = p.y * sT + z1 * cT;
        const s = 1 + z2 * 0.1;
        let df = p.lon - scan;
        df = Math.atan2(Math.sin(df), Math.cos(df));
        return { x: cx + x1 * R * s, y: cy + y2 * R * s, d: (z2 + 1) / 2, b: Math.exp(-7 * df * df) };
      });

      // soft core light
      let g = ctx.createRadialGradient(cx, cy, R * 0.1, cx, cy, R * 1.45);
      g.addColorStop(0, rgba(0.2));
      g.addColorStop(0.55, rgba(0.06));
      g.addColorStop(1, rgba(0));
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, w, h);

      // rim
      ctx.lineWidth = 1;
      ctx.strokeStyle = rgba(0.16);
      ctx.beginPath(); ctx.arc(cx, cy, R * 1.06, 0, 6.2832); ctx.stroke();
      ctx.strokeStyle = rgba(0.07);
      ctx.beginPath(); ctx.arc(cx, cy, R * 1.22, 0, 6.2832); ctx.stroke();

      // latitude lines
      [-0.55, 0, 0.55].forEach((lat) => {
        const rr = Math.sqrt(1 - lat * lat);
        let prev = null;
        for (let k = 0; k <= 72; k++) {
          const a = (k / 72) * 6.2832;
          const x = Math.cos(a) * rr, z = Math.sin(a) * rr;
          const x1 = x * cY + z * sY, z1 = -x * sY + z * cY;
          const y2 = lat * cT - z1 * sT, z2 = lat * sT + z1 * cT;
          const pt = { x: cx + x1 * R * (1 + z2 * 0.1), y: cy + y2 * R * (1 + z2 * 0.1), d: (z2 + 1) / 2 };
          if (prev) {
            ctx.strokeStyle = rgba(0.02 + 0.09 * (pt.d + prev.d) / 2);
            ctx.beginPath(); ctx.moveTo(prev.x, prev.y); ctx.lineTo(pt.x, pt.y); ctx.stroke();
          }
          prev = pt;
        }
      });

      // links
      EDGES.forEach(([i, j]) => {
        const a = P[i], b = P[j];
        const d = (a.d + b.d) / 2;
        ctx.strokeStyle = rgba(Math.min(1, 0.03 + 0.4 * d * d + 0.5 * Math.max(a.b, b.b) * d));
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      });

      // nodes (back to front)
      const order = P.map((p, i) => i).sort((a, b) => P[a].d - P[b].d);
      order.forEach((i) => {
        const p = P[i], src = POINTS[i];
        const tw = still ? 1 : 0.8 + 0.2 * Math.sin(tick * 1.2 + src.ph);
        if (src.hub) {
          const gl = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, 16 * (0.5 + p.d));
          gl.addColorStop(0, rgba(0.5 * p.d * tw));
          gl.addColorStop(1, rgba(0));
          ctx.fillStyle = gl;
          ctx.fillRect(p.x - 20, p.y - 20, 40, 40);
          ctx.strokeStyle = rgba(0.15 + 0.5 * p.d);
          ctx.beginPath(); ctx.arc(p.x, p.y, 3.4 + 2 * p.d, 0, 6.2832); ctx.stroke();
        }
        ctx.fillStyle = rgba(Math.min(1, (0.18 + 0.82 * p.d) * tw + 0.7 * p.b));
        ctx.beginPath(); ctx.arc(p.x, p.y, (src.hub ? 2.2 : 1.1) + 1.2 * p.d + 1.5 * p.b, 0, 6.2832); ctx.fill();
      });

      // an orbit ring with three satellites, turning on its own axis
      {
        const ro = R * 1.3, th = 1.2, ph = -0.45 + lx * 0.12;
        const cTh = Math.cos(th), sTh = Math.sin(th), cPh = Math.cos(ph), sPh = Math.sin(ph);
        const orb = (a) => {
          const px = Math.cos(a), pz = Math.sin(a);
          const y1 = -pz * sTh, z1 = pz * cTh;
          return { x: cx + (px * cPh - y1 * sPh) * ro * (1 + z1 * 0.08), y: cy + (px * sPh + y1 * cPh) * ro * (1 + z1 * 0.08), d: (z1 + 1) / 2 };
        };
        let prev = orb(0);
        for (let k = 1; k <= 96; k++) {
          const pt = orb((k / 96) * 6.2832);
          ctx.strokeStyle = rgba(0.03 + 0.16 * (pt.d + prev.d) / 2);
          ctx.beginPath(); ctx.moveTo(prev.x, prev.y); ctx.lineTo(pt.x, pt.y); ctx.stroke();
          prev = pt;
        }
        if (!still) {
          for (let sat = 0; sat < 3; sat++) {
            const base = tick * 0.42 + sat * 2.0944;
            for (let tr = 9; tr >= 0; tr--) {
              const pt = orb(base - tr * 0.035);
              ctx.fillStyle = rgba((0.5 - tr * 0.05) * (0.3 + 0.7 * pt.d));
              ctx.beginPath(); ctx.arc(pt.x, pt.y, tr === 0 ? 2.8 : 1.6, 0, 6.2832); ctx.fill();
            }
            const head = orb(base);
            const gl = ctx.createRadialGradient(head.x, head.y, 0, head.x, head.y, 14);
            gl.addColorStop(0, `rgba(255,255,255,${0.8 * (0.3 + 0.7 * head.d)})`);
            gl.addColorStop(0.3, rgba(0.5 * head.d));
            gl.addColorStop(1, rgba(0));
            ctx.fillStyle = gl;
            ctx.fillRect(head.x - 14, head.y - 14, 28, 28);
          }
        }
      }

      // ripples sent out on each new statement
      if (!still) {
        ripples.current = ripples.current.map((t) => t + dt * 0.4).filter((t) => t < 1);
        ripples.current.forEach((t) => {
          ctx.lineWidth = 1.5;
          ctx.strokeStyle = rgba(0.42 * (1 - t) * (1 - t));
          ctx.beginPath(); ctx.arc(cx, cy, R * (1.04 + t * 0.7), 0, 6.2832); ctx.stroke();
          ctx.lineWidth = 1;
        });
      }

      // pulses of light along the links
      if (!still) {
        packets.forEach((k) => {
          k.t += dt * k.v;
          if (k.t >= 1) {
            const from = k.b;
            const options = NEIGH[from].filter((n) => n !== k.a);
            k.a = from;
            k.b = (options.length ? options : NEIGH[from])[Math.floor(rnd() * (options.length || NEIGH[from].length))];
            k.t = 0;
          }
          const a = P[k.a], b = P[k.b];
          const x = a.x + (b.x - a.x) * k.t, y = a.y + (b.y - a.y) * k.t;
          const d = a.d + (b.d - a.d) * k.t;
          const gl = ctx.createRadialGradient(x, y, 0, x, y, 12);
          gl.addColorStop(0, `rgba(255,255,255,${0.9 * d})`);
          gl.addColorStop(0.25, rgba(0.7 * d));
          gl.addColorStop(1, rgba(0));
          ctx.fillStyle = gl;
          ctx.fillRect(x - 12, y - 12, 24, 24);
        });
      }
    }

    function loop(now) {
      const dt = Math.min((now - last) / 1000 || 0, 0.05);
      last = now;
      tick += dt;
      if (Math.floor(tick * 6) % 6 === 0) color = readColor(cv);
      draw(dt);
      raf = requestAnimationFrame(loop);
    }

    const ro = new ResizeObserver(resize);
    ro.observe(box);
    resize();
    color = readColor(cv);
    if (still) draw(0);
    else raf = requestAnimationFrame(loop);

    return () => {
      ro.disconnect();
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div className="mc-globe" ref={wrap} aria-hidden="true">
      <canvas ref={canvas} />
    </div>
  );
}

export default NeuralGlobe;
