import { useRef } from "react";
import Icon from "../Icon";

/**
 * PortalSelector
 * ------------------------------------------------------------
 * Four large options in place of the old tab strip. Implemented as a
 * radio group (one stop in the tab order, arrow keys move between
 * options) because that is what choosing one-of-four actually is.
 */

function PortalSelector({ portals, active, onSelect }) {
  const refs = useRef({});

  function onKeyDown(event, index) {
    const keys = {
      ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1,
    };
    if (!(event.key in keys)) return;

    event.preventDefault();
    const next = portals[(index + keys[event.key] + portals.length) % portals.length];
    onSelect(next.key);
    refs.current[next.key]?.focus();
  }

  return (
    <div className="mc-portals" role="radiogroup" aria-label="Choose a portal">
      {portals.map((portal, index) => {
        const isActive = portal.key === active;
        return (
          <button
            key={portal.key}
            ref={(node) => { refs.current[portal.key] = node; }}
            type="button"
            role="radio"
            aria-checked={isActive}
            tabIndex={isActive ? 0 : -1}
            data-portal={portal.key}
            className={isActive ? "mc-portal is-active" : "mc-portal"}
            onClick={() => onSelect(portal.key)}
            onKeyDown={(event) => onKeyDown(event, index)}
          >
            <span className="mc-portal-icon">
              <Icon name={portal.icon} size={20} />
            </span>
            <span className="mc-portal-title">{portal.label}</span>
            <span className="mc-portal-active" aria-hidden="true" />
          </button>
        );
      })}
    </div>
  );
}

export default PortalSelector;
