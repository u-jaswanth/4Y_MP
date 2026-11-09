/**
 * RichText
 * ------------------------------------------------------------
 * The AI summaries come back as Markdown - headings, bullets, bold
 * test names. Rendering them inside a plain <p> is what made them look
 * like a wall of text with literal ## and ** characters in it.
 *
 * This turns that Markdown into real elements. It is deliberately tiny
 * and dependency-free (no react-markdown install needed) and covers
 * exactly what the summary prompts ask for:
 *
 *   ## Heading          -> <h4 class="rt-heading">
 *   ### Heading         -> <h5 class="rt-subheading">
 *   - item  /  * item   -> <ul class="rt-list">
 *   1. item             -> <ol class="rt-list">
 *   **bold**            -> <strong>
 *   *italic*  /  _it_   -> <em>
 *   `code`              -> <code>
 *   ---                 -> <hr>
 *   blank line          -> paragraph break
 *
 * Bullets written as "**ALT** - 62 U/L (7-56) - High" also get their
 * trailing status word turned into a coloured pill, which is the bit
 * that actually makes results scannable.
 */

// ============================================================
// INLINE FORMATTING
// ============================================================

const INLINE_PATTERN =
  /(\*\*[^*]+\*\*|__[^_]+__|\*[^*\n]+\*|_[^_\n]+_|`[^`]+`)/g;

function renderInline(text, keyPrefix = "i") {

  if (!text) {
    return null;
  }

  const parts = String(text).split(INLINE_PATTERN).filter(Boolean);

  return parts.map((part, index) => {

    const key = `${keyPrefix}-${index}`;

    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={key}>{part.slice(2, -2)}</strong>;
    }

    if (part.startsWith("__") && part.endsWith("__")) {
      return <strong key={key}>{part.slice(2, -2)}</strong>;
    }

    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={key}>{part.slice(1, -1)}</code>;
    }

    if (
      (part.startsWith("*") && part.endsWith("*")) ||
      (part.startsWith("_") && part.endsWith("_"))
    ) {
      return <em key={key}>{part.slice(1, -1)}</em>;
    }

    return <span key={key}>{part}</span>;
  });
}

// ============================================================
// RESULT STATUS PILL
// ============================================================
// Bullets from the summary prompts end in a status word. Pulling it
// out and colouring it is what lets someone scan a list of results
// without reading every line.

const STATUS_STYLES = {
  high: "rt-pill rt-pill-alert",
  low: "rt-pill rt-pill-alert",
  elevated: "rt-pill rt-pill-alert",
  abnormal: "rt-pill rt-pill-alert",
  borderline: "rt-pill rt-pill-watch",
  normal: "rt-pill rt-pill-ok",
  "within range": "rt-pill rt-pill-ok"
};

function splitTrailingStatus(text) {

  const match = String(text).match(
    /\s[-–—]\s*(high|low|elevated|abnormal|borderline|normal|within range)\s*\.?$/i
  );

  if (!match) {
    return { body: text, status: null };
  }

  return {
    body: text.slice(0, match.index),
    status: match[1]
  };
}

function ListItemContent({ text, keyPrefix }) {

  const { body, status } = splitTrailingStatus(text);

  if (!status) {
    return <>{renderInline(text, keyPrefix)}</>;
  }

  const className =
    STATUS_STYLES[status.toLowerCase()] || "rt-pill";

  return (
    <>
      {renderInline(body, keyPrefix)}
      <span className={className}>{status}</span>
    </>
  );
}

// ============================================================
// BLOCK PARSING
// ============================================================

function parseBlocks(markdown) {

  const lines = String(markdown).replace(/\r\n/g, "\n").split("\n");

  const blocks = [];
  let paragraph = [];
  let list = null;

  function flushParagraph() {
    if (paragraph.length) {
      blocks.push({ type: "paragraph", text: paragraph.join(" ") });
      paragraph = [];
    }
  }

  function flushList() {
    if (list) {
      blocks.push(list);
      list = null;
    }
  }

  function flushAll() {
    flushParagraph();
    flushList();
  }

  lines.forEach((rawLine) => {

    const line = rawLine.trim();

    // --- blank line ---------------------------------------
    if (!line) {
      flushAll();
      return;
    }

    // --- horizontal rule ----------------------------------
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(line)) {
      flushAll();
      blocks.push({ type: "rule" });
      return;
    }

    // --- heading ------------------------------------------
    const heading = line.match(/^(#{1,6})\s+(.*)$/);

    if (heading) {
      flushAll();
      blocks.push({
        type: "heading",
        level: heading[1].length,
        text: heading[2].replace(/[:#]+$/, "")
      });
      return;
    }

    // --- bullet -------------------------------------------
    const bullet = line.match(/^[-*•]\s+(.*)$/);

    if (bullet) {
      flushParagraph();

      if (!list || list.ordered) {
        flushList();
        list = { type: "list", ordered: false, items: [] };
      }

      list.items.push(bullet[1]);
      return;
    }

    // --- numbered item ------------------------------------
    const numbered = line.match(/^\d+[.)]\s+(.*)$/);

    if (numbered) {
      flushParagraph();

      if (!list || !list.ordered) {
        flushList();
        list = { type: "list", ordered: true, items: [] };
      }

      list.items.push(numbered[1]);
      return;
    }

    // --- a bold line on its own reads as a heading --------
    const boldOnly = line.match(/^\*\*(.+?)\*\*:?$/);

    if (boldOnly) {
      flushAll();
      blocks.push({ type: "heading", level: 3, text: boldOnly[1] });
      return;
    }

    // --- plain text ---------------------------------------
    flushList();
    paragraph.push(line);
  });

  flushAll();

  return blocks;
}

// ============================================================
// COMPONENT
// ============================================================

function RichText({ children, className = "" }) {

  const source = typeof children === "string" ? children.trim() : "";

  if (!source) {
    return null;
  }

  const blocks = parseBlocks(source);

  return (

    <div className={`rich-text ${className}`.trim()}>

      {blocks.map((block, index) => {

        const key = `b-${index}`;

        if (block.type === "rule") {
          return <hr key={key} className="rt-rule" />;
        }

        if (block.type === "heading") {

          if (block.level <= 2) {
            return (
              <h4 key={key} className="rt-heading">
                {renderInline(block.text, key)}
              </h4>
            );
          }

          return (
            <h5 key={key} className="rt-subheading">
              {renderInline(block.text, key)}
            </h5>
          );
        }

        if (block.type === "list") {

          const ListTag = block.ordered ? "ol" : "ul";

          return (
            <ListTag key={key} className="rt-list">

              {block.items.map((item, itemIndex) => (
                <li key={`${key}-${itemIndex}`}>
                  <ListItemContent
                    text={item}
                    keyPrefix={`${key}-${itemIndex}`}
                  />
                </li>
              ))}

            </ListTag>
          );
        }

        return (
          <p key={key} className="rt-paragraph">
            {renderInline(block.text, key)}
          </p>
        );
      })}

    </div>
  );
}

export default RichText;
