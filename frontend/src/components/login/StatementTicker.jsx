import { useEffect, useState } from "react";
import Icon from "../Icon";

/**
 * StatementTicker
 * ------------------------------------------------------------
 * One sentence at a time under the headline, each word easing in,
 * with a three-segment progress line. The statements are the same
 * promises the product already makes elsewhere (patient-approved
 * access, tamper-checked records, plain-language reports) - nothing
 * here claims more than the app does.
 *
 * `onStep` tells the page which statement is showing, so the globe
 * can answer each change with a ripple. With reduced motion all three
 * statements are simply listed.
 */

const STATEMENTS = [
  { icon: "access", text: "Doctors see your records only when you approve." },
  { icon: "chain", text: "Every record is checked for tampering." },
  { icon: "reports", text: "Every report explained in plain language." },
];

const HOLD = 4800;

function StatementTicker({ onStep }) {
  const [i, setI] = useState(0);

  const reduced =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    if (reduced) return undefined;
    const id = setTimeout(() => setI((v) => (v + 1) % STATEMENTS.length), HOLD);
    return () => clearTimeout(id);
  }, [i, reduced]);

  useEffect(() => {
    if (onStep) onStep(i);
  }, [i, onStep]);

  return (
    <div className="mc-say" role="group" aria-label="What MediConnect does">

      <div className="mc-say-body">
        {STATEMENTS.map((item, n) => (
          <p key={item.text} className={n === i ? "mc-say-item is-on" : "mc-say-item"}>
            <span className="mc-say-icon">
              <Icon name={item.icon} size={18} />
            </span>
            <span className="mc-say-text">
              {item.text.split(" ").map((word, w) => (
                <span
                  key={w}
                  className="mc-say-word"
                  style={{ animationDelay: `${0.12 + w * 0.07}s` }}
                >
                  {word}
                </span>
              ))}
            </span>
          </p>
        ))}
      </div>

      <div className="mc-say-bar">
        {STATEMENTS.map((item, n) => (
          <button
            key={item.text}
            type="button"
            aria-label={`Show statement ${n + 1} of ${STATEMENTS.length}`}
            aria-current={n === i}
            className={n === i ? "is-on" : n < i ? "is-done" : ""}
            style={{ "--hold": `${HOLD}ms` }}
            onClick={() => setI(n)}
          />
        ))}
      </div>

    </div>
  );
}

export default StatementTicker;
