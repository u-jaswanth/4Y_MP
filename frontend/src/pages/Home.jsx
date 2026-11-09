import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getToken, landingPath } from "../services/session";

import BrandMark from "../components/BrandMark";
import Icon from "../components/Icon";

import "./home.css";

/**
 * Home
 * ------------------------------------------------------------
 * The first page a visitor sees, at "/". Everything on it describes
 * something the app really does - nothing here is a made-up statistic
 * or testimonial. The product pictures are drawn from sample data and
 * labelled as such.
 *
 * Signed-in visitors get "Open your dashboard" instead of the
 * sign-in / get-started pair, and land on their own role's home.
 */

const STEPS = [
  {
    icon: "upload",
    title: "Add your reports",
    text: "Upload a PDF yourself, or give your hospital your Health ID and they add it straight to your record.",
  },
  {
    icon: "spark",
    title: "Understand them",
    text: "Each report is read and explained in plain language, and every test is tracked against its normal range.",
  },
  {
    icon: "access",
    title: "Share on your terms",
    text: "A doctor asks, you approve. You can take that access back whenever you like.",
  },
];

const TRUST = [
  { icon: "file", text: "Reports explained in plain language" },
  { icon: "access", text: "Doctors see nothing until you approve" },
  { icon: "chain", text: "Every consent change is tamper-evident" },
];


// Draws a small trend line inside the normal band, like the real tiles.
function Spark({ points, band, tone = "brand", w = 220 }) {

  const h = 84;
  const pad = 8;

  const all = [...points, band[0], band[1]];
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const y = (v) => h - pad - ((v - lo) / (hi - lo || 1)) * (h - pad * 2);
  const x = (i) => pad + (i / (points.length - 1)) * (w - pad * 2);

  const path = points.map((v, i) => `${i ? "L" : "M"}${x(i)} ${y(v)}`).join(" ");
  const last = points.length - 1;

  return (
    <svg className={`spark spark-${tone}`} viewBox={`0 0 ${w} ${h}`} aria-hidden="true">
      <rect
        className="spark-band"
        x="0"
        width={w}
        y={y(band[1])}
        height={Math.max(4, y(band[0]) - y(band[1]))}
        rx="4"
      />
      <path className="spark-line" d={path} />
      <circle className="spark-dot" cx={x(last)} cy={y(points[last])} r="4.5" />
    </svg>
  );
}


function Home() {

  const navigate = useNavigate();

  const signedIn = Boolean(getToken());

  const [scrolled, setScrolled] = useState(false);

  const rootRef = useRef(null);

  // Header gains a rule once the page scrolls.
  useEffect(() => {

    function onScroll() {
      setScrolled(window.scrollY > 8);
    }

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });

    return () => window.removeEventListener("scroll", onScroll);

  }, []);

  // Sections fade up as they enter. Content is visible by default;
  // it is only hidden once this effect has confirmed JS and the
  // observer are available, so nothing is ever stuck invisible.
  useEffect(() => {

    const root = rootRef.current;

    if (!root || !("IntersectionObserver" in window)) return undefined;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return undefined;
    }

    root.classList.add("js-ready");

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-in");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );

    root.querySelectorAll(".reveal").forEach((el) => observer.observe(el));

    return () => observer.disconnect();

  }, []);

  function start() {
    navigate(signedIn ? landingPath() : "/register");
  }

  return (

    <div className="home" ref={rootRef}>

      {/* ============ HEADER ============ */}

      <header className={scrolled ? "home-header is-scrolled" : "home-header"}>

        <div className="home-wrap home-header-row">

          <a className="home-logo" href="/" aria-label="MediConnect AI home">
            <BrandMark />
          </a>

          <nav className="home-links" aria-label="Sections">
            <a href="#how">How it works</a>
            <a href="#features">Features</a>
            <a href="#privacy">Privacy</a>
            <a href="#professionals">For hospitals &amp; doctors</a>
          </nav>

          <div className="home-header-cta">
            {signedIn ? (
              <button className="primary-btn" onClick={start}>
                Open your dashboard
              </button>
            ) : (
              <>
                <button className="home-signin" onClick={() => navigate("/login")}>
                  Sign in
                </button>
                <button className="primary-btn" onClick={start}>
                  Get started
                </button>
              </>
            )}
          </div>

        </div>

      </header>


      <main>

        {/* ============ HERO ============ */}

        <section className="hero">

          <div className="home-wrap hero-grid">

            <div className="hero-copy">

              <p className="eyebrow">
                <Icon name="pulse" size={16} />
                Your medical records, in one place
              </p>

              <h1>
                Understand your health reports.
                <span> Share them only when you choose.</span>
              </h1>

              <p className="hero-lede">
                Upload a lab report and get it explained in plain language,
                see how every result is changing over time, and decide which
                doctors are allowed to look.
              </p>

              <div className="hero-actions">

                <button className="primary-btn hero-btn" onClick={start}>
                  {signedIn ? "Open your dashboard" : "Create your account"}
                </button>

                {!signedIn && (
                  <button
                    className="secondary-btn hero-btn"
                    onClick={() => navigate("/login")}
                  >
                    Sign in
                  </button>
                )}

              </div>

              <ul className="hero-trust">
                {TRUST.map((item) => (
                  <li key={item.text}>
                    <Icon name={item.icon} size={18} />
                    {item.text}
                  </li>
                ))}
              </ul>

            </div>


            {/* The product, drawn from sample data */}
            <div className="hero-visual" aria-hidden="true">

              <div className="mock mock-main">

                <div className="mock-head">
                  <strong>Health trends</strong>
                  <span>2 of 8 out of range</span>
                </div>

                <div className="mock-tiles">

                  <div className="mock-tile mock-tile-high">
                    <div className="mock-tile-top">
                      <span>Fasting glucose</span>
                      <em className="tag tag-high">High</em>
                    </div>
                    <div className="mock-value">
                      118 <small>mg/dL</small>
                    </div>
                    <Spark points={[92, 104, 118]} band={[70, 100]} tone="high" />
                  </div>

                  <div className="mock-tile">
                    <div className="mock-tile-top">
                      <span>Hemoglobin</span>
                      <em className="tag tag-ok">In range</em>
                    </div>
                    <div className="mock-value">
                      14.2 <small>g/dL</small>
                    </div>
                    <Spark points={[13.4, 13.8, 14.2]} band={[13, 17]} />
                  </div>

                </div>

              </div>

              <div className="mock mock-note">
                <p className="mock-kicker">In plain language</p>
                <p>
                  Your fasting glucose has crept up across three reports.
                  Worth raising with your doctor at your next visit.
                </p>
              </div>

              <div className="mock mock-consent">
                <span className="mock-avatar">MI</span>
                <div>
                  <strong>Dr. Meera Iyer</strong>
                  <small>wants to view your reports</small>
                </div>
                <span className="mock-approve">Approve</span>
              </div>

              <p className="mock-caption">Sample data</p>

              <svg className="hero-pulse" viewBox="0 0 600 90" preserveAspectRatio="none" aria-hidden="true">
                <path
                  pathLength="1"
                  d="M0 46h150l16-30 22 62 20-46 14 14h96l14-26 22 56 16-30h230"
                />
              </svg>

            </div>

          </div>

        </section>


        {/* ============ HOW IT WORKS ============ */}

        <section className="section" id="how">

          <div className="home-wrap">

            <div className="section-head reveal">
              <p className="eyebrow eyebrow-plain">How it works</p>
              <h2>From a PDF in a drawer to something you can act on.</h2>
            </div>

            <ol className="steps">
              {STEPS.map((step, index) => (
                <li className="step reveal" key={step.title} style={{ "--d": `${index * 90}ms` }}>
                  <span className="step-num">{index + 1}</span>
                  <span className="step-icon">
                    <Icon name={step.icon} size={22} />
                  </span>
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                </li>
              ))}
            </ol>

          </div>

        </section>


        {/* ============ FEATURES ============ */}

        <section className="section section-tint" id="features">

          <div className="home-wrap">

            <div className="section-head reveal">
              <p className="eyebrow eyebrow-plain">What you get</p>
              <h2>Built around the report, not the dashboard.</h2>
            </div>


            {/* 1 - explanations */}
            <div className="feature reveal">

              <div className="feature-copy">
                <span className="feature-icon-lg"><Icon name="spark" size={24} /></span>
                <h3>Every report, explained like a letter.</h3>
                <p>
                  No more searching what “ALT” means. Each report gets a
                  written explanation that says what looks normal, what is
                  worth watching, and what to ask your doctor.
                </p>
                <ul className="tick-list">
                  <li><Icon name="check" size={18} />Plain language, not lab jargon</li>
                  <li><Icon name="check" size={18} />One summary across all your reports</li>
                  <li><Icon name="check" size={18} />Ask the AI follow-up questions about your own results</li>
                </ul>
              </div>

              <div className="feature-art">
                <div className="letter">
                  <p className="letter-kicker">Lipid profile · Aug 16</p>
                  <h4>Overall picture</h4>
                  <p>
                    Your LDL cholesterol is <strong>109 mg/dL</strong>, down
                    from 121 at your last report. That is moving the right
                    way, though still just above the 100 target.
                  </p>
                  <h4>Worth watching</h4>
                  <p>
                    Triglycerides are normal, so the main number to keep an
                    eye on is LDL.
                  </p>
                  <span className="letter-note">Sample data</span>
                </div>
              </div>

            </div>


            {/* 2 - trends */}
            <div className="feature feature-flip reveal">

              <div className="feature-copy">
                <span className="feature-icon-lg"><Icon name="pulse" size={24} /></span>
                <h3>See what is changing, not just what is high.</h3>
                <p>
                  Every test you have more than once becomes a trend, drawn
                  against its normal range, so a slow drift shows up long
                  before it becomes a problem.
                </p>
                <ul className="tick-list">
                  <li><Icon name="check" size={18} />Normal range shaded behind every line</li>
                  <li><Icon name="check" size={18} />Out-of-range values stand out in colour</li>
                  <li><Icon name="check" size={18} />Filter to just the tests that need attention</li>
                </ul>
              </div>

              <div className="feature-art">
                <div className="trend-pair">

                  {[
                    ["LDL cholesterol", "109", "mg/dL", [132, 121, 109], [0, 100], "High", "high"],
                    ["Vitamin D", "26", "ng/mL", [14, 19, 26], [30, 100], "Low", "low"],
                    ["TSH", "2.2", "mIU/L", [2.4, 2.1, 2.2], [0.4, 4], "In range", "ok"],
                  ].map(([name, value, unit, pts, band, label, tone], i) => (
                    <div className={`mock-tile mock-tile-${tone}`} key={name}>
                      <div className="mock-tile-top">
                        <span>{name}</span>
                        <em className={`tag tag-${tone}`}>{label}</em>
                      </div>
                      <div className="mock-value">
                        {value} <small>{unit}</small>
                      </div>
                      <Spark
                        points={pts}
                        band={band}
                        w={i === 0 ? 460 : 220}
                        tone={tone === "ok" ? "brand" : tone}
                      />
                    </div>
                  ))}

                  <span className="letter-note">Sample data</span>

                </div>
              </div>

            </div>


            {/* 3 - doctors */}
            <div className="feature reveal">

              <div className="feature-copy">
                <span className="feature-icon-lg"><Icon name="doctor" size={24} /></span>
                <h3>Find the right doctor, then decide who sees what.</h3>
                <p>
                  Describe what is going on and get doctors ranked by fit,
                  distance and availability. When one of them asks to see
                  your records, you are the one who says yes.
                </p>
                <ul className="tick-list">
                  <li><Icon name="check" size={18} />Matched by specialty, location and urgency</li>
                  <li><Icon name="check" size={18} />Approve or deny each request</li>
                  <li><Icon name="check" size={18} />Revoke access at any time</li>
                </ul>
              </div>

              <div className="feature-art">
                <div className="requests">

                  <div className="request">
                    <span className="mock-avatar">MI</span>
                    <div>
                      <strong>Dr. Meera Iyer</strong>
                      <small>Endocrinologist · asked today</small>
                    </div>
                    <div className="request-actions">
                      <span className="mock-approve">Approve</span>
                      <span className="mock-deny">Deny</span>
                    </div>
                  </div>

                  <div className="request request-done">
                    <span className="mock-avatar mock-avatar-quiet">KN</span>
                    <div>
                      <strong>Dr. Kavya Nair</strong>
                      <small>Cardiologist · access granted</small>
                    </div>
                    <span className="mock-revoke">Revoke</span>
                  </div>

                  <span className="letter-note">Sample data</span>

                </div>
              </div>

            </div>

          </div>

        </section>


        {/* ============ PRIVACY ============ */}

        <section className="section privacy" id="privacy">

          <div className="home-wrap privacy-grid">

            <div className="reveal">
              <p className="eyebrow eyebrow-light">Privacy</p>
              <h2>Your record belongs to you. The system is built to show it.</h2>
              <p className="privacy-lede">
                Medical records are some of the most personal data there is.
                So access is opt-in, and the history of who was allowed in,
                and when, can be checked rather than just trusted.
              </p>
            </div>

            <ul className="privacy-list">

              <li className="reveal" style={{ "--d": "0ms" }}>
                <Icon name="access" size={22} />
                <div>
                  <h3>Consent comes first</h3>
                  <p>A doctor can only open a record after you approve their request.</p>
                </div>
              </li>

              <li className="reveal" style={{ "--d": "80ms" }}>
                <Icon name="chain" size={22} />
                <div>
                  <h3>A tamper-evident history</h3>
                  <p>Every approval and revocation is written to a chained ledger, and the ledger can be audited.</p>
                </div>
              </li>

              <li className="reveal" style={{ "--d": "160ms" }}>
                <Icon name="lock" size={22} />
                <div>
                  <h3>Separate sign-ins for every role</h3>
                  <p>Patients, hospitals, doctors and administrators each get their own portal and their own permissions.</p>
                </div>
              </li>

            </ul>

          </div>

        </section>


        {/* ============ PROFESSIONALS ============ */}

        <section className="section" id="professionals">

          <div className="home-wrap">

            <div className="section-head reveal">
              <p className="eyebrow eyebrow-plain">For hospitals &amp; doctors</p>
              <h2>Less chasing paper. More of the full picture.</h2>
            </div>

            <div className="pro-grid">

              <article className="pro-card reveal" style={{ "--d": "0ms" }}>
                <span className="step-icon"><Icon name="hospital" size={22} /></span>
                <h3>Hospitals</h3>
                <p>
                  List your doctors, and add a report directly to a patient’s
                  record using their Health ID. It lands in their account,
                  ready for them to read and have explained.
                </p>
                <button className="link-btn" onClick={() => navigate("/login")}>
                  Hospital sign in →
                </button>
              </article>

              <article className="pro-card reveal" style={{ "--d": "90ms" }}>
                <span className="step-icon"><Icon name="doctor" size={22} /></span>
                <h3>Doctors</h3>
                <p>
                  Request access to a patient’s record, then read their
                  reports and ask questions grounded in their own results,
                  for as long as they allow it.
                </p>
                <button className="link-btn" onClick={() => navigate("/login")}>
                  Doctor sign in →
                </button>
              </article>

            </div>

          </div>

        </section>


        {/* ============ CLOSING CTA ============ */}

        <section className="closing">

          <div className="home-wrap closing-inner reveal">

            <h2>Start with one report.</h2>

            <p>
              Create an account, upload a lab result, and see it explained in
              plain language.
            </p>

            <div className="hero-actions hero-actions-center">
              <button className="primary-btn hero-btn closing-btn" onClick={start}>
                {signedIn ? "Open your dashboard" : "Create your account"}
              </button>
            </div>

            <p className="disclaimer-line">
              MediConnect AI explains your reports to help you prepare for a
              conversation with your doctor. It does not diagnose or replace
              medical advice.
            </p>

          </div>

        </section>

      </main>


      {/* ============ FOOTER ============ */}

      <footer className="home-footer">

        <div className="home-wrap footer-row">

          <BrandMark onDark />

          <nav aria-label="Footer">
            <a href="#how">How it works</a>
            <a href="#privacy">Privacy</a>
            <button onClick={() => navigate("/login")}>Sign in</button>
            <button onClick={() => navigate("/register")}>Register</button>
          </nav>

        </div>

      </footer>

    </div>
  );
}

export default Home;
