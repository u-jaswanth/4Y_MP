"""
Ranks the doctor directory against one triage result.

The score is a weighted sum out of 100, and every component that
contributed is returned alongside it as a short phrase - so the UI can
show *why* a doctor came first instead of asking the user to trust a
number.

Weights:

    specialty match   50   the single biggest factor
    distance          20   from the user's area to the doctor's
    rating            15
    experience        10
    availability       5   plus an emergency bonus for urgent cases

Nothing here calls a model. Given the same inputs it produces the same
ranking every time, which is what you want when someone is choosing who
to see.
"""

from sqlalchemy.orm import Session

from app.models.doctor import Doctor
from app.doctors.locations import coordinates_for, distance_km, travel_hint

SPECIALTY_WEIGHT = 50.0
DISTANCE_WEIGHT = 20.0
RATING_WEIGHT = 15.0
EXPERIENCE_WEIGHT = 10.0
AVAILABILITY_WEIGHT = 5.0

# Beyond this, extra distance stops costing anything more - a doctor
# 40km away is not meaningfully worse than one 25km away.
DISTANCE_CEILING_KM = 25.0


def _specialty_score(doctor: Doctor, specialties: list[str]) -> tuple[float, str | None]:
    """Full marks for the top-ranked specialty, less for the ones after."""

    if doctor.specialty not in specialties:
        return 0.0, None

    rank = specialties.index(doctor.specialty)

    # 1.0, 0.8, 0.64, 0.51 ...
    factor = 0.8 ** rank

    if rank == 0:
        reason = f"Specialises in {doctor.specialty.lower()}, the best fit for this case"
    else:
        reason = f"{doctor.specialty} - a reasonable alternative for this case"

    return SPECIALTY_WEIGHT * factor, reason


def _focus_score(doctor: Doctor, symptoms: str) -> tuple[float, str | None]:
    """A small bump when the doctor's listed focus matches the words used."""

    lowered = (symptoms or "").lower()

    matches = [
        item for item in doctor.focus_list
        if item and item.lower() in lowered
    ]

    if not matches:
        return 0.0, None

    return min(len(matches) * 3.0, 6.0), (
        f"Listed experience with {', '.join(matches[:2])}"
    )


def _distance_score(distance: float | None) -> tuple[float, str]:

    if distance is None:
        return DISTANCE_WEIGHT * 0.4, "Location not matched"

    if distance >= DISTANCE_CEILING_KM:
        return 0.0, travel_hint(distance)

    factor = 1 - (distance / DISTANCE_CEILING_KM)

    return DISTANCE_WEIGHT * factor, travel_hint(distance)


def _rating_score(doctor: Doctor) -> tuple[float, str | None]:

    rating = doctor.rating or 0.0

    if rating <= 0:
        return 0.0, None

    # 3.0 -> 0, 5.0 -> full
    factor = max(0.0, min(1.0, (rating - 3.0) / 2.0))

    reason = None

    if rating >= 4.7 and (doctor.reviews_count or 0) >= 300:
        reason = f"Rated {rating} from {doctor.reviews_count} patient reviews"

    return RATING_WEIGHT * factor, reason


def _experience_score(doctor: Doctor) -> tuple[float, str | None]:

    years = doctor.experience_years or 0

    factor = min(years, 25) / 25

    reason = f"{years} years in practice" if years >= 15 else None

    return EXPERIENCE_WEIGHT * factor, reason


def _availability_score(doctor: Doctor, urgency: str) -> tuple[float, str | None]:

    score = 0.0
    reason = None

    slot = (doctor.next_available or "").lower()

    if slot.startswith("today"):
        score += AVAILABILITY_WEIGHT
        reason = f"Has a slot {doctor.next_available.lower()}"

    if urgency in {"emergency", "urgent"} and doctor.handles_emergencies:
        score += 8.0
        reason = "Attached to a 24x7 emergency department"

    return score, reason


def rank_doctors(
    db: Session,
    triage: dict,
    form: dict,
    limit: int = 6,
) -> list[dict]:
    """Return the best matches, highest score first."""

    specialties: list[str] = triage["specialties"]
    urgency: str = triage["urgency"]

    origin = coordinates_for(form.get("area"))

    candidates = (
        db.query(Doctor)
        .filter(Doctor.specialty.in_(specialties))
        .all()
    )

    # Nothing in the requested specialties - fall back to the whole
    # directory rather than showing an empty page.
    if not candidates:
        candidates = db.query(Doctor).all()

    results = []

    for doctor in candidates:

        distance = distance_km(
            origin,
            (doctor.latitude, doctor.longitude)
            if doctor.latitude is not None else None,
        )

        parts = []

        specialty_points, specialty_reason = _specialty_score(doctor, specialties)
        focus_points, focus_reason = _focus_score(doctor, form.get("symptoms", ""))
        distance_points, distance_reason = _distance_score(distance)
        rating_points, rating_reason = _rating_score(doctor)
        experience_points, experience_reason = _experience_score(doctor)
        availability_points, availability_reason = _availability_score(doctor, urgency)

        total = (
            specialty_points
            + focus_points
            + distance_points
            + rating_points
            + experience_points
            + availability_points
        )

        for reason in (
            specialty_reason,
            focus_reason,
            availability_reason,
            rating_reason,
            experience_reason,
        ):
            if reason:
                parts.append(reason)

        results.append(
            {
                "doctor": doctor,
                "match_score": round(min(total, 100.0)),
                "distance_km": distance,
                "distance_label": distance_reason,
                "reasons": parts[:4],
                "is_primary_specialty": (
                    bool(specialties) and doctor.specialty == specialties[0]
                ),
            }
        )

    results.sort(key=lambda item: item["match_score"], reverse=True)

    return results[:limit]
