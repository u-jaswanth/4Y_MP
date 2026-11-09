"""
Builds the per-test history behind the dashboard's "Health trends" card.

Where the numbers come from
---------------------------
Every lab value a report contained is already stored, one row per
value, in `vector_observations` (see app/retrieval/observation_index.py).
The value, unit, reference range and status were written into that
row's `content` text - there is no numeric column. Rather than change
the schema (and leave every existing report without data), this reads
that text back and pulls the fields out again, so trends work on
reports uploaded before this feature existed.

The date of each point is the report's upload date. Reports don't
store the date the sample was taken.

This is read-only: no model calls, no writes.
"""

import re
from collections import Counter, defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.report import Report
from app.vectorstore.models import ObservationRecord


_FIELD = re.compile(r"^(Result|Unit|Reference range|Status|Aliases):\s*(.*)$", re.MULTILINE)

_NUMBER = r"-?\d+(?:\.\d+)?"

# A plain number. Anything with a qualifier ("<0.5", "Positive",
# "1:80") is not plottable and is skipped rather than guessed at.
_PLAIN_VALUE = re.compile(rf"^\s*({_NUMBER}|\d{{1,3}}(?:,\d{{3}})+(?:\.\d+)?)\s*$")

_RANGE_BETWEEN = re.compile(rf"({_NUMBER})\s*(?:-|–|—|to)\s*({_NUMBER})", re.IGNORECASE)
_RANGE_UPPER = re.compile(rf"^\s*(?:<|≤|<=|up to|less than|upto)\s*({_NUMBER})", re.IGNORECASE)
_RANGE_LOWER = re.compile(rf"^\s*(?:>|≥|>=|more than|greater than)\s*({_NUMBER})", re.IGNORECASE)

MAX_TESTS = 40


def _parse_fields(content: str) -> dict:
    return {key: value.strip() for key, value in _FIELD.findall(content or "")}


def _to_number(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    match = _PLAIN_VALUE.match(text)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _parse_range(text: Optional[str]) -> tuple[Optional[float], Optional[float]]:
    if not text or text.lower().startswith("not specified"):
        return None, None

    between = _RANGE_BETWEEN.search(text)
    if between:
        low, high = float(between.group(1)), float(between.group(2))
        if low <= high:
            return low, high
        return None, None

    upper = _RANGE_UPPER.match(text)
    if upper:
        return None, float(upper.group(1))

    lower = _RANGE_LOWER.match(text)
    if lower:
        return float(lower.group(1)), None

    return None, None


def _status(value: float, low: Optional[float], high: Optional[float], reported: str) -> Optional[str]:
    """Trust the numbers when there is a range; otherwise fall back to
    whatever word the lab printed."""

    if high is not None and value > high:
        return "high"
    if low is not None and value < low:
        return "low"
    if low is not None or high is not None:
        return "normal"

    word = (reported or "").lower()
    if "high" in word:
        return "high"
    if "low" in word:
        return "low"
    if "normal" in word or "within" in word:
        return "normal"
    return None


def _display_name(record) -> str:
    return (record.canonical_name or record.observation_name or "").strip()


# ------------------------------------------------------------
# Deciding that two names are the same test
# ------------------------------------------------------------
# Labs (and the model reading them) write the same test many ways:
# "Hemoglobin", "HAEMOGLOBIN (Hb)", "Hemoglobin - Hb". Comparing raw
# names would split each of those into its own one-point "test", so
# nothing would ever have a history. Instead every row offers a few
# normalised candidate names - its own, the text in brackets, and the
# aliases the normaliser attached - and rows that share ANY candidate
# are treated as one test.

_BRACKETS = re.compile(r"[\(\[]([^)\]]*)[\)\]]")


def _clean(text: str) -> str:
    text = text.lower()
    text = text.replace("haem", "hem").replace("leuk", "leuc")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _candidates(name: str, aliases: str) -> set[str]:
    found = set()

    for raw in [name] + ([a for a in aliases.split(",")] if aliases and aliases != "none" else []):
        raw = raw or ""

        inside = _BRACKETS.findall(raw)
        outside = _BRACKETS.sub(" ", raw)

        for piece in [outside] + inside:
            cleaned = _clean(piece)
            if len(cleaned) >= 2:
                # Word order doesn't matter: "Total Cholesterol" and
                # "Cholesterol, Total" are one test.
                found.add(" ".join(sorted(cleaned.split())))

    return found


class _Groups:
    """Tiny union-find over candidate names."""

    def __init__(self):
        self.parent = {}

    def find(self, item):
        self.parent.setdefault(item, item)
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, items):
        items = list(items)
        for other in items[1:]:
            self.parent[self.find(other)] = self.find(items[0])


def _title(name: str) -> str:
    """The normaliser lower-cases names it doesn't recognise."""
    return name.title() if name.islower() else name


def build_trends(patient: Patient, db: Session) -> dict:

    reports = (
        db.query(Report.id, Report.report_name, Report.uploaded_at)
        .filter(Report.patient_id == patient.id, Report.analyzed.is_(True))
        .all()
    )

    if not reports:
        return {"reports_analyzed": 0, "tests": []}

    by_document = {str(r.id): r for r in reports}

    # Select only the columns needed - the embedding vector on each
    # row is large and irrelevant here.
    rows = (
        db.query(
            ObservationRecord.document_id,
            ObservationRecord.observation_name,
            ObservationRecord.canonical_name,
            ObservationRecord.content,
        )
        .filter(ObservationRecord.document_id.in_(list(by_document.keys())))
        .all()
    )

    # First pass: read every row and learn which names belong together.
    parsed = []
    groups = _Groups()

    for row in rows:

        name = _display_name(row)
        if not name:
            continue

        fields = _parse_fields(row.content)

        value = _to_number(fields.get("Result"))
        if value is None:
            continue

        candidates = _candidates(name, fields.get("Aliases", ""))
        candidates |= _candidates(row.observation_name or "", "")

        if not candidates:
            continue

        groups.union(candidates)
        parsed.append((row, name, fields, value, next(iter(candidates))))

    # Second pass: one series per group, one point per report.
    series: dict[str, dict[str, dict]] = defaultdict(dict)
    names: dict[str, Counter] = defaultdict(Counter)
    units: dict[str, Counter] = defaultdict(Counter)
    ranges: dict[str, dict[str, tuple]] = defaultdict(dict)

    for row, name, fields, value, anchor in parsed:

        key = groups.find(anchor)

        report = by_document.get(row.document_id)
        if report is None or row.document_id in series[key]:
            continue

        low, high = _parse_range(fields.get("Reference range"))

        unit = fields.get("Unit", "")
        if unit and unit.lower() != "not specified":
            units[key][unit] += 1

        names[key][name] += 1
        ranges[key][row.document_id] = (low, high)

        series[key][row.document_id] = {
            "report_id": row.document_id,
            "report_name": report.report_name,
            "date": report.uploaded_at.isoformat() if report.uploaded_at else None,
            "value": value,
            "status": _status(value, low, high, fields.get("Status", "")),
        }

    tests = []

    for key, points_by_report in series.items():

        points = sorted(points_by_report.values(), key=lambda p: p["date"] or "")

        latest_report_id = points[-1]["report_id"]
        low, high = ranges[key].get(latest_report_id, (None, None))

        tests.append(
            {
                "name": _title(names[key].most_common(1)[0][0]),
                "unit": units[key].most_common(1)[0][0] if units[key] else "",
                # The band drawn behind the chart is the latest report's
                # range, since labs change ranges and that is the one
                # the latest value was judged against.
                "range_low": low,
                "range_high": high,
                "latest_status": points[-1]["status"],
                "points": [
                    {k: v for k, v in p.items() if k != "report_id"} for p in points
                ],
            }
        )

    # Out-of-range first, then the tests with the most history.
    def sort_key(test):
        out_of_range = test["latest_status"] in ("high", "low")
        return (not out_of_range, -len(test["points"]), test["name"].lower())

    tests.sort(key=sort_key)

    return {
        "reports_analyzed": len(reports),
        "tests": tests[:MAX_TESTS],
    }
