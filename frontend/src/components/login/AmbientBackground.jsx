/**
 * AmbientBackground
 * ------------------------------------------------------------
 * Two slow pools of light and an edge vignette behind the stage.
 * Decorative only.
 */
function AmbientBackground() {
  return (
    <div className="mc-network" aria-hidden="true">
      <div className="mc-glow mc-glow-a" />
      <div className="mc-glow mc-glow-b" />
      <div className="mc-vignette" />
    </div>
  );
}

export default AmbientBackground;
