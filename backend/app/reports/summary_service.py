"""
Owns the patient's cached, cross-report AI health summary - the card on
the dashboard and at the top of the Reports page.

  - `regenerate_and_store_summary()` is the only thing that calls the
    language model for this summary. It now runs during UPLOAD (see
    reports/routes.py: _process_report), not behind a separate button.
    It re-runs the comprehensive query over every processed report, so
    the stored summary always reflects "previous reports + the new one"
    folded into one answer - it just does it once, at upload time,
    instead of on every page view.

  - `get_cached_summary()` is what GET /reports/summary calls. It's a
    plain DB read. The only time it falls back to a model call is for a
    patient who has processed reports but no cache yet (e.g. data that
    existed before this caching was added) - and even then it stores the
    result immediately so it's a one-time cost.

The query below asks for Markdown on purpose: the frontend renders it
through src/components/RichText.jsx, so headings and bullets survive
into the UI instead of arriving as one unbroken paragraph.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.report import Report
from app.retrieval.combined_retriever import CombinedRetriever
from app.generation.context_builder import RAGContextBuilder
from app.generation.answer_generator import MedicalAnswerGenerator

SUMMARY_QUERY = """
Give an overall picture of this patient's health across all of their
uploaded test results, and flag anything abnormal.

Write it in Markdown using exactly these sections, in this order:

## Overall picture
Two or three sentences describing the general state of the results.

## Needs attention
A bullet for each result outside its reference range, formatted as:
**Test name** - value unit (reference range) - High / Low
followed by a short clause on what that test measures. If nothing is
out of range, write one sentence saying so.

## Within range
A single short paragraph naming the groups of tests that came back
normal. Do not list every value again.

## Suggested next steps
Two or three short bullets, always including discussing the results
with a doctor.

Stay under 300 words, use simple language, never invent a value or a
reference range, and do not diagnose.
"""


def _processed_document_ids(patient: Patient, db: Session) -> list[str]:
    return [
        str(report_id)
        for (report_id,) in db.query(Report.id)
        .filter(Report.patient_id == patient.id, Report.analyzed.is_(True))
        .all()
    ]


def _empty_summary_payload(reports_analyzed: int = 0) -> dict:
    return {
        "summary": "",
        "observation_count": 0,
        "reports_analyzed": reports_analyzed,
        "generated_at": None,
    }


def _generate(patient: Patient, db: Session) -> dict:
    """Actually calls the RAG pipeline + the model. Does not touch the DB."""

    own_document_ids = _processed_document_ids(patient, db)
    reports_analyzed = len(own_document_ids)

    if reports_analyzed == 0:
        return _empty_summary_payload()

    retriever = CombinedRetriever(patient_top_k=5, knowledge_top_k=5)
    context_builder = RAGContextBuilder()
    generator = MedicalAnswerGenerator()

    retrieval_result = retriever.retrieve(
        SUMMARY_QUERY,
        comprehensive=True,
        document_ids=own_document_ids,
    )
    observations = retrieval_result["patient"]["observations"]

    if not observations:
        return _empty_summary_payload(reports_analyzed)

    context = context_builder.build(query=SUMMARY_QUERY, retrieval_result=retrieval_result)
    answer = generator.generate(query=SUMMARY_QUERY, retrieved_context=context)

    return {
        "summary": answer,
        "observation_count": len(observations),
        "reports_analyzed": reports_analyzed,
        "generated_at": datetime.utcnow(),
    }


def _store(patient: Patient, db: Session, payload: dict) -> None:
    patient.ai_summary = payload["summary"]
    patient.ai_summary_observation_count = payload["observation_count"]
    patient.ai_summary_reports_analyzed = payload["reports_analyzed"]
    patient.ai_summary_generated_at = payload["generated_at"] or datetime.utcnow()

    db.add(patient)
    db.commit()
    db.refresh(patient)


def regenerate_and_store_summary(patient: Patient, db: Session) -> dict:
    """Called during upload, right after a report finishes processing."""

    payload = _generate(patient, db)
    _store(patient, db, payload)
    return payload


def get_cached_summary(patient: Patient, db: Session) -> dict:
    """Cheap read path for GET /reports/summary - no model call in the common case."""

    if patient.ai_summary and patient.ai_summary_generated_at:
        return {
            "summary": patient.ai_summary,
            "observation_count": patient.ai_summary_observation_count or 0,
            "reports_analyzed": patient.ai_summary_reports_analyzed or 0,
            "generated_at": patient.ai_summary_generated_at,
        }

    # No cache yet. If nothing has been processed, don't call the model.
    if not _processed_document_ids(patient, db):
        return _empty_summary_payload()

    # Processed reports exist but were never cached (e.g. pre-existing
    # data) - generate once here and store it so this is the last time
    # it's slow.
    return regenerate_and_store_summary(patient, db)
