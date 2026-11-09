import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReportOut(BaseModel):
    id: uuid.UUID
    filename: str
    report_name: Optional[str] = None
    report_type: Optional[str] = None
    cloud_url: Optional[str] = None
    file_url: Optional[str] = None
    status: str
    analyzed: bool
    analysis_error: Optional[str] = None
    uploaded_at: datetime
    analyzed_at: Optional[datetime] = None

    # Who put this report here - "patient" for the normal self-upload
    # case, "hospital" when hospital staff uploaded it on the
    # patient's behalf (see app/hospitals/routes.py).
    uploaded_by: str = "patient"
    uploaded_by_hospital: Optional[str] = None
    uploaded_by_staff: Optional[str] = None

    # ------------------------------------------------------------
    # PER-REPORT SUMMARY
    # ------------------------------------------------------------
    # Produced during upload (see app/reports/report_summary_service.py)
    # so the Reports page can render the explanation directly beneath
    # the report it belongs to.
    ai_summary: Optional[str] = None
    ai_summary_generated_at: Optional[datetime] = None
    ai_summary_error: Optional[str] = None
    observation_count: Optional[int] = None

    # Both step errors collapsed into one field for the UI.
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class HealthSummaryOut(BaseModel):
    summary: str
    observation_count: int
    # Alias the frontend dashboard currently reads under this name -
    # kept identical to observation_count so both spellings work.
    reports_analyzed: int = 0
    # When this summary was (re)generated. None means it was never
    # generated yet (no processed reports). The frontend can use this
    # to show "updated X ago" instead of implying it's always fresh.
    generated_at: Optional[datetime] = None


class TrendPointOut(BaseModel):
    date: Optional[datetime] = None
    report_name: Optional[str] = None
    value: float
    # "high", "low", "normal", or None when there was no range to judge by.
    status: Optional[str] = None


class TrendTestOut(BaseModel):
    name: str
    unit: str = ""
    range_low: Optional[float] = None
    range_high: Optional[float] = None
    latest_status: Optional[str] = None
    points: list[TrendPointOut]


class TrendsOut(BaseModel):
    reports_analyzed: int = 0
    tests: list[TrendTestOut] = []
