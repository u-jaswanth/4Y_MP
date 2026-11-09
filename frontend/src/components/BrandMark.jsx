/**
 * BrandMark
 * ------------------------------------------------------------
 * The logo, in one place. A cross whose horizontal arm is a pulse
 * line - the record (cross) and the live reading (pulse) in one shape.
 * `onDark` flips the wordmark colours for the navy sidebar and the
 * sign-in panel.
 */

function BrandMark({ onDark = false, size = 32 }) {
  return (
    <span className={onDark ? "brand-mark on-dark" : "brand-mark"}>
      <svg
        className="brand-mark-glyph"
        width={size}
        height={size}
        viewBox="0 0 32 32"
        aria-hidden="true"
        focusable="false"
      >
        <rect width="32" height="32" rx="9" className="brand-mark-bg" />
        <path
          d="M16 7v6M16 19v6"
          stroke="#fff"
          strokeWidth="2.6"
          strokeLinecap="round"
          fill="none"
        />
        <path
          d="M6.5 16h5l2-4 3 8 2-4h6.5"
          stroke="#7BE0D0"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
      </svg>
      <span className="brand-mark-word">
        MediConnect<span className="brand-mark-ai"> AI</span>
      </span>
    </span>
  );
}

export default BrandMark;
