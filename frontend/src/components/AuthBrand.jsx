import BrandMark from "./BrandMark";
import Icon from "./Icon";

/**
 * AuthBrand
 * ------------------------------------------------------------
 * The left-hand panel on the sign-in and register screens. It was
 * duplicated in both pages with different copy; now the copy is
 * passed in and the structure lives here.
 *
 *   title   - headline, a plain string
 *   intro   - one sentence under it
 *   points  - short statements of what the person gets
 */

function AuthBrand({ title, intro, points }) {

  return (

    <aside className="auth-brand">

      <div className="brand-logo">
        <BrandMark onDark size={36} />
      </div>

      <div className="auth-brand-body">

        <h1>{title}</h1>

        <p>{intro}</p>

        <ul className="brand-feature">
          {points.map((point) => (
            <li key={point.icon + point.text}>
              <span className="feature-icon">
                <Icon name={point.icon} size={18} />
              </span>
              <span>{point.text}</span>
            </li>
          ))}
        </ul>

      </div>

      {/* One quiet pulse line, drawn once on load. */}
      <svg
        className="auth-pulse"
        viewBox="0 0 600 90"
        preserveAspectRatio="none"
        aria-hidden="true"
        focusable="false"
      >
        <path
          pathLength="1"
          d="M0 46h150l16-30 22 62 20-46 14 14h96l14-26 22 56 16-30h230"
        />
      </svg>

    </aside>
  );
}

export default AuthBrand;
