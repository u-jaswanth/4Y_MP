"""
Builds the plain-language explanation that appears directly underneath
a single report on the Reports page.

This is deliberately separate from app/reports/summary_service.py:

  - summary_service  -> ONE summary folding together EVERY processed
                        report (the "AI Health Summary" card and the
                        dashboard card).
  - this module      -> ONE summary per report, scoped to that report's
                        own document_id only.

Both are generated during upload (see reports/routes.py: upload_report)
so nothing has to be triggered by hand afterwards.

If Gemini is unavailable - no API key, rate limited, timed out - we do
NOT leave the report without an explanation. `_fallback_summary()`
builds a readable Markdown breakdown straight from the indexed
observations, so the user always sees their values, reference ranges
and which ones are out of range.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.report import Report
from app.retrieval.combined_retriever import CombinedRetriever
from app.generation.context_builder import RAGContextBuilder
from app.generation.answer_generator import MedicalAnswerGenerator


# The summary is rendered as Markdown by the frontend (see
# src/components/RichText.jsx), so the format is requested explicitly
# here - otherwise Gemini returns one long unstructured paragraph,
# which is what made the old summaries so hard to read.
REPORT_SUMMARY_QUERY = """
Explain this single medical report to the patient who owns it.

Write it in Markdown using exactly these sections, in this order:

## What this report covers
One or two sentences naming the type of report and what it looks at.

## Your results
A bullet for each test that was found. Format each bullet as:
**Test name** - value unit (reference range) - Normal / High / Low
Use the exact values, units and reference ranges from the records.
Never invent a value or a range. If a range is missing, write
"no reference range given" instead of guessing one.

## What stands out
Only the results outside their reference range, each with one short
sentence on what that test generally measures. If everything is within
range, say so in one sentence and skip the list.

## What this could mean
Two to four sentences of general medical context for the results above.
Use cautious wording ("can be associated with", "common causes
include"). Do not diagnose and do not recommend specific medication.

## Suggested next steps
Two or three short bullets, always including discussing the results
with a doctor.

Keep the whole thing under 350 words and use simple language a
non-medical reader understands.
"""


# ============================================================
# DETERMINISTIC FALLBACK (no LLM)
# ============================================================

def _observation_rows(observations: list[dict]) -> list[dict]:
    """Flatten retrieved observations into plain value rows."""

    extract = RAGContextBuilder._extract_field

    rows = []

    for observation in observations:
        metadata = observation.get("metadata", {}) or {}
        evidence = observation.get("document", "") or ""

        rows.append(
            {
                "name": (
                    metadata.get("observation_name")
                    or metadata.get("canonical_name")
                    or "Unnamed test"
                ),
                "result": extract(evidence, "Result"),
                "unit": extract(evidence, "Unit"),
                "reference_range": extract(evidence, "Reference range"),
                "status": (extract(evidence, "Status") or "").strip(),
            }
        )

    return rows


def _is_abnormal(status: str) -> bool:
    normalized = (status or "").strip().lower()

    if not normalized:
        return False

    return normalized not in {"normal", "within range", "not specified", "none"}


def _fallback_summary(observations: list[dict]) -> str:
    """Readable Markdown built from the records alone - used when the
    language model can't be reached, so the report is never left blank."""

    rows = _observation_rows(observations)

    if not rows:
        return (
            "## What this report covers\n\n"
            "This report was stored, but no individual test results could "
            "be read from it. That usually means the file is a scan with "
            "low-quality text. Re-uploading a clearer copy normally fixes "
            "it.\n"
        )

    abnormal = [row for row in rows if _is_abnormal(row["status"])]

    lines = [
        "## Your results",
        "",
    ]

    for row in rows:
        unit = row["unit"] if row["unit"] not in (None, "", "not specified") else ""
        reference = (
            row["reference_range"]
            if row["reference_range"] not in (None, "", "not specified")
            else "no reference range given"
        )
        status = row["status"] or "not flagged"

        lines.append(
            f"- **{row['name']}** - {row['result']} {unit} "
            f"({reference}) - {status}".replace("  ", " ")
        )

    lines.append("")
    lines.append("## What stands out")
    lines.append("")

    if abnormal:
        for row in abnormal:
            lines.append(
                f"- **{row['name']}** is outside the reference range "
                f"({row['result']} {row['unit']}, expected "
                f"{row['reference_range']})."
            )
    else:
        lines.append(
            "Every result in this report falls inside its laboratory "
            "reference range."
        )

    lines.append("")
    lines.append("## Suggested next steps")
    lines.append("")
    lines.append("- Go through these results with your doctor.")
    lines.append("- Keep this report so future results can be compared to it.")

    return "\n".join(lines)


# ============================================================
# GENERATION
# ============================================================

def _generate(report: Report) -> dict:
    """Retrieve this report's own observations and explain them.

    Never raises: any failure is returned as `error` so the upload
    request still succeeds and the report still appears in the list.
    """

    document_id = str(report.id)

    try:
        retriever = CombinedRetriever(patient_top_k=25, knowledge_top_k=5)

        retrieval_result = retriever.retrieve(
            REPORT_SUMMARY_QUERY,
            comprehensive=True,
            # Scope retrieval to THIS report only - that's what makes
            # the summary specific to the report it sits under, rather
            # than a repeat of the overall health summary.
            document_ids=[document_id],
        )

        observations = retrieval_result["patient"]["observations"]

    except Exception as error:  # noqa: BLE001
        return {
            "summary": None,
            "observation_count": 0,
            "error": f"Could not read this report's indexed results: {error}",
        }

    if not observations:
        return {
            "summary": _fallback_summary([]),
            "observation_count": 0,
            "error": None,
        }

    # ------------------------------------------------------------
    # Preferred path: let the model explain the results.
    # ------------------------------------------------------------
    try:
        context = RAGContextBuilder().build(
            query=REPORT_SUMMARY_QUERY,
            retrieval_result=retrieval_result,
        )

        answer = MedicalAnswerGenerator().generate(
            query=REPORT_SUMMARY_QUERY,
            retrieved_context=context,
        )

        # MedicalAnswerGenerator swallows its own errors and returns a
        # short apology string instead of raising. Those strings are
        # useless underneath a report, so treat them as a miss and fall
        # back to the values we already have.
        if not answer or len(answer.strip()) < 120:
            answer = _fallback_summary(observations)

    except Exception:  # noqa: BLE001
        answer = _fallback_summary(observations)

    return {
        "summary": answer.strip(),
        "observation_count": len(observations),
        "error": None,
    }


def regenerate_and_store(report: Report, db: Session) -> Report:
    """Build this report's summary and persist it on the row.

    Called once during upload, and again whenever the user presses
    Summarize on the Reports page.
    """

    payload = _generate(report)

    report.ai_summary = payload["summary"]
    report.observation_count = payload["observation_count"]
    report.ai_summary_error = payload["error"]
    report.ai_summary_generated_at = (
        datetime.utcnow() if payload["summary"] else None
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return report
