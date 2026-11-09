import { useEffect, useRef, useState } from "react";
import { loginUser } from "../services/api";
import { useNavigate } from "react-router-dom";

import { saveSession, landingPath } from "../services/session";

import BrandMark from "../components/BrandMark";
import AmbientBackground from "../components/login/AmbientBackground";
import NeuralGlobe from "../components/login/NeuralGlobe";
import StatementTicker from "../components/login/StatementTicker";
import LoginConsole from "../components/login/LoginConsole";
import { PORTAL_BY_KEY, PORTAL_LABEL } from "../components/login/portals";

import "./login.css";

/**
 * Login - the "Medical AI OS" entrance.
 *
 * The screen is split: a dark stage on the left (brand, headline, the
 * intelligence visual) and the access console on the right (portal
 * selector + form). All of the AUTHENTICATION behaviour is unchanged
 * from the previous version of this page and lives in this file:
 *
 *   - the person picks a portal BEFORE typing anything;
 *   - there is one /auth/login endpoint, which matches an email or an
 *     issued ID and reports which role the account really is;
 *   - if the picked portal and the account's role disagree, the person
 *     is told to switch portals instead of being dropped into the
 *     wrong one;
 *   - on success: saveSession(result), then navigate(landingPath()).
 *
 * Presentation lives in components/login/* and pages/login.css.
 */

function Login() {
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState("patient");

  const [form, setForm] = useState({
    identifier: "",
    password: "",
  });

  const [error, setError] = useState("");

  const [busy, setBusy] = useState(false);

  const tab = PORTAL_BY_KEY[activeTab];

  const stageRef = useRef(null);

  // which statement the left side is showing; the globe answers each change
  const [step, setStep] = useState(0);

  // Subtle desktop parallax: write the pointer position (-1..1) to CSS
  // variables on the stage; layers read them. One rAF per frame, no
  // React re-render, and skipped for reduced-motion / touch devices.
  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return undefined;

    const quiet = window.matchMedia(
      "(prefers-reduced-motion: reduce), (hover: none)"
    );
    if (quiet.matches) return undefined;

    let frame = 0;
    let nextX = 0;
    let nextY = 0;

    function paint() {
      frame = 0;
      stage.style.setProperty("--mx", nextX.toFixed(3));
      stage.style.setProperty("--my", nextY.toFixed(3));
    }

    function onMove(event) {
      const box = stage.getBoundingClientRect();
      nextX = ((event.clientX - box.left) / box.width - 0.5) * 2;
      nextY = ((event.clientY - box.top) / box.height - 0.5) * 2;
      if (!frame) frame = requestAnimationFrame(paint);
    }

    function onLeave() {
      nextX = 0;
      nextY = 0;
      if (!frame) frame = requestAnimationFrame(paint);
    }

    stage.addEventListener("pointermove", onMove);
    stage.addEventListener("pointerleave", onLeave);
    return () => {
      stage.removeEventListener("pointermove", onMove);
      stage.removeEventListener("pointerleave", onLeave);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  function selectTab(key) {
    setActiveTab(key);
    setError("");
    // The identifier rarely carries over between an email tab and an
    // ID tab, so clear it rather than leaving a stale value sitting
    // under a relabelled field.
    setForm({ identifier: "", password: "" });
  }

  function handleChange(event) {
    setForm({
      ...form,
      [event.target.name]: event.target.value,
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setBusy(true);

    try {
      // loginUser posts whatever object it's handed, and the backend
      // accepts `identifier` (or the older `email` key), matching it
      // against either column - so this call is the same regardless
      // of which portal is active.
      const result = await loginUser({
        identifier: form.identifier.trim(),
        password: form.password,
      });

      // The portal picked *before* typing anything has to agree with
      // the role the server actually found. Disagreeing means the ID
      // belongs to a different kind of account, not that login
      // failed.
      if (result.role !== activeTab) {

        const actualTab = PORTAL_BY_KEY[result.role];

        setError(
          actualTab
            ? `That ID belongs to ${PORTAL_LABEL[result.role]}. ` +
              `Switch to the "${actualTab.label}" tab and try again.`
            : "That account doesn't match the portal you picked."
        );

        return;
      }

      saveSession(result);

      navigate(landingPath());
    } catch (error) {
      setError(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mc-login" data-portal={activeTab}>

      {/* ============ STAGE (left on desktop, top on mobile) ============ */}
      <div className="mc-stage" ref={stageRef}>

        <div className="mc-depth-0">
          <AmbientBackground />
        </div>

        <div className="mc-stage-inner">

          <div className="mc-brand">
            <BrandMark onDark size={36} />
          </div>

          <h1 className="mc-headline" aria-label="The intelligence layer for healthcare.">
            <span className="mc-hl mc-hl-serif" aria-hidden="true">The</span>
            <span className="mc-hl mc-hl-bold" aria-hidden="true">Intelligence</span>
            <span className="mc-hl mc-hl-serif" aria-hidden="true">
              Layer <em>for</em>
            </span>
            <span className="mc-hl mc-hl-bold" aria-hidden="true">Healthcare.</span>
          </h1>

          <StatementTicker onStep={setStep} />

          <NeuralGlobe pulseKey={step} />

        </div>
      </div>

      {/* ============ ACCESS CONSOLE ============ */}
      <main className="mc-side">
        <LoginConsole
          portal={tab}
          form={form}
          error={error}
          busy={busy}
          onSelect={selectTab}
          onChange={handleChange}
          onSubmit={handleSubmit}
          onRegister={() => navigate("/register")}
        />
      </main>

    </div>
  );
}

export default Login;
