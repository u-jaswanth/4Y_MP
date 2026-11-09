from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.patient import Patient
from app.models.report import Report
from app.models.chat_message import ChatMessage
from app.schemas.chat import ChatRequest, ChatResponse, ChatHistoryOut
from app.auth.dependencies import get_current_patient
from app.retrieval.combined_retriever import CombinedRetriever
from app.retrieval.query_router import QueryRouter
from app.generation.context_builder import RAGContextBuilder
from app.generation.answer_generator import MedicalAnswerGenerator
from app.reports import summary_service

router = APIRouter(prefix="/chat", tags=["chat"])

# These load models (embedder, Gemini client) once per process,
# not per request - mirrors backend/rag_chatbot_cli.py.
_retriever = None
_router_ = None
_context_builder = None
_generator = None

# How many past turns to pull back out of the DB to seed context.
# Kept modest - this is for resolving follow-ups ("is that high?"),
# not for replaying the whole conversation into every prompt.
HISTORY_TURNS = 8


def _get_pipeline():
    global _retriever, _router_, _context_builder, _generator

    if _retriever is None:
        _retriever = CombinedRetriever(patient_top_k=5, knowledge_top_k=5)
        _router_ = QueryRouter()
        _context_builder = RAGContextBuilder()
        _generator = MedicalAnswerGenerator()

    return _retriever, _router_, _context_builder, _generator


def _load_recent_history(patient: Patient, db: Session, limit: int) -> list[ChatMessage]:
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.patient_id == patient.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))


@router.get("/history", response_model=ChatHistoryOut)
def get_chat_history(
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    """
    Lets the frontend restore the conversation on mount instead of
    always starting from a blank slate - this is the persisted memory
    that was previously missing entirely (history only lived in the
    browser tab's React state and vanished on refresh/navigation).
    """
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.patient_id == current_patient.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return ChatHistoryOut(messages=rows)


@router.post("", response_model=ChatResponse)
def ask_chatbot(
    payload: ChatRequest,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    message = payload.message.strip()

    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Only search this patient's own analyzed reports - never
    # another patient's data.
    own_document_ids = [
        str(report_id)
        for (report_id,) in db.query(Report.id)
        .filter(Report.patient_id == current_patient.id, Report.analyzed.is_(True))
        .all()
    ]

    retriever, router_, context_builder, generator = _get_pipeline()

    route = router_.route(message)
    comprehensive = route["scope"] == "comprehensive"

    retrieval_result = retriever.retrieve(
        message,
        comprehensive=comprehensive,
        document_ids=own_document_ids,
    )

    observations = retrieval_result["patient"]["observations"]
    knowledge = retrieval_result["knowledge"]

    # ------------------------------------------------------------
    # CONVERSATION HISTORY
    # ------------------------------------------------------------
    # Prefer the frontend-supplied history for this exact request (it
    # includes the message that was just typed), but if it's missing
    # (e.g. a fresh tab that hasn't loaded /chat/history yet) fall
    # back to what's persisted server-side, so context isn't just
    # dropped.
    if payload.history:
        recent_turns = payload.history[-HISTORY_TURNS:]
        turn_lines = [
            f"{'User' if turn.role == 'user' else 'Assistant'}: {turn.content}"
            for turn in recent_turns
        ]
    else:
        persisted = _load_recent_history(current_patient, db, HISTORY_TURNS)
        turn_lines = [
            f"{'User' if row.role == 'user' else 'Assistant'}: {row.content}"
            for row in persisted
        ]

    conversation_history = "\n".join(turn_lines)

    # Anchor every answer with the patient's cached overall health
    # summary (see app/reports/summary_service.py) so the chatbot has
    # some grounding even on a question the per-message RAG retrieval
    # doesn't happen to surface good observations for. This is a plain
    # DB read, not a new Gemini call.
    cached_summary = summary_service.get_cached_summary(current_patient, db)
    if cached_summary.get("reports_analyzed", 0) > 0:
        conversation_history = (
            f"[Patient's overall health summary on file]\n{cached_summary['summary']}\n\n"
            f"{conversation_history}"
        ).strip()

    context = context_builder.build(query=message, retrieval_result=retrieval_result)
    answer = generator.generate(
        query=message,
        retrieved_context=context,
        conversation_history=conversation_history,
    )

    # Persist this turn so it's still there next time the patient
    # opens the chat, even in a new tab or after a refresh.
    db.add(ChatMessage(patient_id=current_patient.id, role="user", content=message))
    db.add(ChatMessage(patient_id=current_patient.id, role="assistant", content=answer))
    db.commit()

    return ChatResponse(
        answer=answer,
        scope=route["scope"],
        patient_observations_used=len(observations),
        knowledge_chunks_used=len(knowledge),
    )
