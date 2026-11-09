import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    patient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False
    )

    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)

    # User-supplied label/type from the upload form. Nullable so existing
    # rows (uploaded before this column existed) don't break.
    report_name = Column(String, nullable=True)
    report_type = Column(String, nullable=True)

    # Optional off-site mirror of the file (see app/core/cloudinary_client.py).
    # Local file_path above remains the source of truth the ingestion
    # pipeline reads from - these are purely additive.
    cloud_url = Column(String, nullable=True)
    cloud_public_id = Column(String, nullable=True)

    # `analyzed` means "the ingestion pipeline indexed this report".
    # It is now set during upload rather than by a separate user action.
    analyzed = Column(Boolean, default=False)
    analysis_error = Column(Text, nullable=True)

    uploaded_at = Column(DateTime, default=datetime.utcnow)
    analyzed_at = Column(DateTime, nullable=True)

    # ------------------------------------------------------------
    # HOSPITAL-SIDE UPLOAD
    # ------------------------------------------------------------
    # Both stay NULL for the normal case of a patient uploading their
    # own report. When a hospital uploads one on a patient's behalf
    # (see app/hospitals/routes.py) these are filled in so the patient
    # can see who put it there - the same audit trail idea as the
    # doctor/hospital portals' issued credentials.
    uploaded_by_hospital = Column(String, nullable=True)
    uploaded_by_staff = Column(String, nullable=True)

    # ------------------------------------------------------------
    # PER-REPORT SUMMARY
    # ------------------------------------------------------------
    # Written by app/reports/report_summary_service.py right after the
    # report is ingested during upload, so the Reports page can show the
    # explanation underneath the report immediately - no extra click.
    # `summarize` on the API re-runs this on demand.
    ai_summary = Column(Text, nullable=True)
    ai_summary_generated_at = Column(DateTime, nullable=True)
    ai_summary_error = Column(Text, nullable=True)

    # How many lab observations this report's summary was built from.
    # Shown as a small footnote under the summary.
    observation_count = Column(Integer, nullable=True)

    patient = relationship("Patient", back_populates="reports")

    # ------------------------------------------------------------
    # Derived, read-only fields exposed to the API (see
    # app/schemas/report.py - ReportOut reads these like any other
    # attribute thanks to `from_attributes = True`).
    # ------------------------------------------------------------

    @property
    def status(self) -> str:
        """Drives the badge and the status filter on the Reports page.

        'summarized' - ingested and an explanation is ready to show
        'failed'     - ingestion or summarization raised; error text is
                       exposed separately so the UI can print it
        'processing' - stored, but nothing has been produced yet
        """
        if self.analyzed and self.ai_summary:
            return "summarized"

        if self.analysis_error or self.ai_summary_error:
            return "failed"

        return "processing"

    @property
    def uploaded_by(self) -> str:
        """'hospital' or 'patient' - drives a small badge on the Reports page."""
        return "hospital" if self.uploaded_by_hospital else "patient"

    @property
    def error_message(self) -> str | None:
        """Whichever step failed first, in one field for the UI."""
        return self.analysis_error or self.ai_summary_error

    @property
    def file_url(self) -> str | None:
        """Where the frontend should point the 'View' link/button.

        Prefers the Cloudinary mirror (public, no auth needed) and
        falls back to this API's own file-serving endpoint
        (see GET /reports/{id}/file) when Cloudinary isn't configured.
        """
        if self.cloud_url:
            return self.cloud_url
        return f"/reports/{self.id}/file"
