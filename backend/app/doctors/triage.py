"""
Turns the intake form into something the recommender can rank against.

Two layers, deliberately:

1. `_rule_based()` - a keyword map from the form to specialties, plus
   the red-flag checks. This runs ALWAYS and is never overridden by the
   model. Safety routing should not depend on a network call.

2. `_model_reading()` - the language model reads the free-text symptoms
   and the patient's own report summary, and returns which specialties
   it would send this case to and a short explanation. If it is
   unavailable, times out, or returns something unparseable, the rule
   layer stands on its own and the feature still works.

The model's specialties are merged on top of the rule layer, never
instead of it.
"""

import json
import os
import re

from dotenv import load_dotenv

load_dotenv()


# ============================================================
# THE FORM'S OPTIONS
# ============================================================
# Exposed through GET /doctors/options so the dropdowns and the routing
# table can never drift apart.

HEALTH_CONCERNS: list[dict] = [
    {"value": "general", "label": "General illness or fever",
     "specialties": ["General Physician"]},
    {"value": "heart", "label": "Heart, chest or blood pressure",
     "specialties": ["Cardiology", "General Physician"]},
    {"value": "breathing", "label": "Breathing, cough or chest congestion",
     "specialties": ["Pulmonology", "General Physician"]},
    {"value": "stomach", "label": "Stomach, digestion or liver",
     "specialties": ["Gastroenterology", "General Physician"]},
    {"value": "bones", "label": "Bones, joints, back or injury",
     "specialties": ["Orthopedics"]},
    {"value": "skin", "label": "Skin, hair or nails",
     "specialties": ["Dermatology"]},
    {"value": "brain", "label": "Headache, dizziness or nerves",
     "specialties": ["Neurology", "General Physician"]},
    {"value": "diabetes", "label": "Diabetes, thyroid or hormones",
     "specialties": ["Endocrinology", "General Physician"]},
    {"value": "kidney", "label": "Kidney or urination",
     "specialties": ["Urology", "Nephrology"]},
    {"value": "ent", "label": "Ear, nose or throat",
     "specialties": ["ENT"]},
    {"value": "eye", "label": "Eyes or vision",
     "specialties": ["Ophthalmology"]},
    {"value": "dental", "label": "Teeth or gums",
     "specialties": ["Dentistry"]},
    {"value": "mental", "label": "Mood, anxiety or sleep",
     "specialties": ["Psychiatry"]},
    {"value": "womens", "label": "Women's health or pregnancy",
     "specialties": ["Gynecology"]},
    {"value": "child", "label": "Child health",
     "specialties": ["Pediatrics"]},
    {"value": "unsure", "label": "Not sure - help me decide",
     "specialties": ["General Physician"]},
]

DURATIONS: list[dict] = [
    {"value": "today", "label": "Started today"},
    {"value": "days", "label": "A few days"},
    {"value": "weeks", "label": "One to three weeks"},
    {"value": "months", "label": "One to six months"},
    {"value": "long", "label": "More than six months"},
]

SEVERITIES: list[dict] = [
    {"value": "mild", "label": "Mild - noticeable, not affecting daily life"},
    {"value": "moderate", "label": "Moderate - affecting daily activities"},
    {"value": "severe", "label": "Severe - hard to carry on as usual"},
]


def concern_specialties(concern: str | None) -> list[str]:
    for item in HEALTH_CONCERNS:
        if item["value"] == concern:
            return list(item["specialties"])
    return ["General Physician"]


def concern_label(concern: str | None) -> str:
    for item in HEALTH_CONCERNS:
        if item["value"] == concern:
            return item["label"]
    return "General health concern"


# ============================================================
# SYMPTOM KEYWORDS -> SPECIALTY
# ============================================================

SYMPTOM_ROUTES: list[tuple[tuple[str, ...], str]] = [
    (("chest pain", "chest tightness", "palpitation", "heart", "bp ",
      "blood pressure", "cholesterol"), "Cardiology"),
    (("breathless", "shortness of breath", "wheez", "asthma", "cough",
      "phlegm", "sputum", "smok"), "Pulmonology"),
    (("stomach", "abdomen", "abdominal", "acidity", "gastric", "vomit",
      "nausea", "diarrhea", "diarrhoea", "constipat", "liver", "jaundice",
      "bloat"), "Gastroenterology"),
    (("joint", "knee", "back pain", "neck pain", "shoulder", "fracture",
      "sprain", "swollen ankle", "arthritis", "slipped disc"), "Orthopedics"),
    (("rash", "itch", "acne", "pimple", "skin", "hair fall", "hair loss",
      "eczema", "psoriasis", "fungal"), "Dermatology"),
    (("headache", "migraine", "dizz", "vertigo", "numb", "tingl", "seizure",
      "fits", "fainted", "tremor", "memory loss"), "Neurology"),
    (("sugar", "diabet", "thyroid", "hormone", "weight gain", "weight loss",
      "pcos", "insulin"), "Endocrinology"),
    (("urine", "urinat", "kidney", "stone", "creatinine", "prostate",
      "burning while pass"), "Urology"),
    (("swelling in legs", "dialysis", "renal"), "Nephrology"),
    (("ear", "throat", "sinus", "nose block", "tonsil", "hearing",
      "sore throat", "snor"), "ENT"),
    (("eye", "vision", "blurred", "watering eyes", "spectacle"),
     "Ophthalmology"),
    (("tooth", "teeth", "gum", "dental", "cavity"), "Dentistry"),
    (("anxiet", "depress", "panic", "stress", "insomnia", "can't sleep",
      "cannot sleep", "low mood", "mood"), "Psychiatry"),
    (("period", "menstrual", "pregnan", "vaginal", "menopause", "fibroid"),
     "Gynecology"),
    (("my child", "my son", "my daughter", "baby", "toddler", "infant"),
     "Pediatrics"),
    (("fever", "cold", "body ache", "weakness", "tired", "fatigue"),
     "General Physician"),
]


# ============================================================
# RED FLAGS
# ============================================================
# Deterministic on purpose. These decide whether the page shows an
# "urgent" banner, so they must not depend on a model call succeeding.

EMERGENCY_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    (("crushing chest pain", "chest pain spreading", "pain in left arm",
      "chest pain and sweating"),
     "Chest pain that spreads to the arm, jaw or back needs emergency care now."),
    (("cannot breathe", "can't breathe", "gasping", "blue lips"),
     "Severe difficulty breathing needs emergency care now."),
    (("slurred speech", "face drooping", "one side weak", "one side of my body",
      "sudden weakness on one side"),
     "Sudden weakness on one side, or slurred speech, can mean a stroke - "
     "emergency care now."),
    (("unconscious", "fainted and did not wake", "unresponsive", "seizure now",
      "convulsion"),
     "Loss of consciousness or an ongoing seizure needs emergency care now."),
    (("heavy bleeding", "bleeding won't stop", "vomiting blood",
      "blood in vomit", "coughing blood"),
     "Bleeding that will not stop, or blood in vomit, needs emergency care now."),
    (("suicid", "end my life", "kill myself", "harm myself", "self harm"),
     "Please reach out for immediate support - call a doctor or a crisis "
     "helpline right away, and tell someone you trust."),
]

URGENT_PATTERNS: tuple[str, ...] = (
    "high fever", "fever for", "severe pain", "unbearable", "vomiting since",
    "not able to eat", "not able to walk", "swelling", "injury", "accident",
)


def _red_flags(text: str, severity: str) -> tuple[list[str], str]:
    """Returns (messages, urgency) where urgency is emergency/urgent/routine."""

    lowered = text.lower()

    messages = [
        message
        for patterns, message in EMERGENCY_PATTERNS
        if any(pattern in lowered for pattern in patterns)
    ]

    if messages:
        return messages, "emergency"

    if severity == "severe":
        return (
            ["Severe symptoms are best seen today rather than booked for later."],
            "urgent",
        )

    if any(pattern in lowered for pattern in URGENT_PATTERNS):
        return (
            ["This sounds like it should be looked at within a day or two."],
            "urgent",
        )

    return [], "routine"


# ============================================================
# RULE LAYER
# ============================================================

def _rule_based(form: dict) -> dict:

    symptoms = (form.get("symptoms") or "").strip()
    severity = (form.get("severity") or "mild").lower()
    concern = form.get("concern")

    lowered = symptoms.lower()

    # Specialties suggested by the words they used, in the order the
    # routing table lists them (most specific first).
    from_symptoms = [
        specialty
        for keywords, specialty in SYMPTOM_ROUTES
        if any(keyword in lowered for keyword in keywords)
    ]

    # Who leads depends on whether they told us. Picking "Not sure" is a
    # request to be routed by the description, so the symptom match
    # leads there; otherwise their own choice of concern does.
    if concern == "unsure":
        ordered = from_symptoms + concern_specialties(concern)
    else:
        ordered = concern_specialties(concern) + from_symptoms

    specialties: list[str] = []

    for specialty in ordered:
        if specialty not in specialties:
            specialties.append(specialty)

    # A general physician is always a reasonable place to start, so keep
    # one in the list as a safety net for an unusual description.
    if "General Physician" not in specialties:
        specialties.append("General Physician")

    flags, urgency = _red_flags(symptoms, severity)

    return {
        "specialties": specialties,
        "urgency": urgency,
        "red_flags": flags,
    }


# ============================================================
# MODEL LAYER
# ============================================================

KNOWN_SPECIALTIES = {
    "General Physician", "Cardiology", "Pulmonology", "Gastroenterology",
    "Orthopedics", "Dermatology", "Neurology", "Endocrinology", "Urology",
    "Nephrology", "ENT", "Ophthalmology", "Dentistry", "Psychiatry",
    "Gynecology", "Pediatrics",
}

TRIAGE_SYSTEM = """
You are a triage assistant for a medical appointment app in India.

You never diagnose and you never suggest medication. Your only job is
to decide which kind of doctor this person should see, and to restate
their situation clearly so the doctor can read it in ten seconds.

Reply with JSON only - no prose, no markdown fences.
"""


def _model_reading(form: dict, report_summary: str | None) -> dict | None:

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        record_block = ""

        if report_summary:
            record_block = (
                "\n\nThis person's most recent lab report summary, for "
                "context only - do not repeat it back verbatim:\n"
                f"{report_summary[:2000]}"
            )

        prompt = f"""
Someone filled in this form:

Health concern: {concern_label(form.get("concern"))}
Symptoms in their words: {form.get("symptoms")}
How long: {form.get("duration")}
Severity: {form.get("severity")}
Area: {form.get("area")}, {form.get("city")}{record_block}

Choose from exactly this list of specialties:
{", ".join(sorted(KNOWN_SPECIALTIES))}

Return JSON with these keys:

{{
  "specialties": ["most appropriate first, at most three"],
  "case_summary": "3-4 sentences in plain English describing the case
                   as a doctor would want it handed over. Mention how
                   long it has been going on and how severe it is.",
  "questions_for_doctor": ["3 short questions this person should ask"],
  "before_the_visit": ["2-3 short practical things to bring or note"]
}}
"""

        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=TRIAGE_SYSTEM,
                temperature=0.2,
                max_output_tokens=800,
            ),
        )

        text = (response.text or "").strip()

        # Strip fences if the model added them anyway.
        text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()

        data = json.loads(text)

        if not isinstance(data, dict):
            return None

        return data

    except Exception as error:  # noqa: BLE001
        print(f"[triage] Model reading unavailable ({error}); using rules only.")
        return None


# ============================================================
# FALLBACK CASE SUMMARY
# ============================================================

DURATION_WORDS = {item["value"]: item["label"].lower() for item in DURATIONS}


def _fallback_case_summary(form: dict) -> str:

    duration = DURATION_WORDS.get(
        form.get("duration"), "for an unspecified period"
    )

    severity = (form.get("severity") or "mild").lower()

    return (
        f"{concern_label(form.get('concern'))}, described as "
        f"{severity}, {duration}. In their words: "
        f"\"{(form.get('symptoms') or '').strip()}\". "
        f"Looking for a doctor near {form.get('area')}, {form.get('city')}."
    )


# ============================================================
# PUBLIC ENTRY POINT
# ============================================================

def understand_case(form: dict, report_summary: str | None = None) -> dict:
    """Merge the rule layer and the model layer into one triage result."""

    rules = _rule_based(form)
    model = _model_reading(form, report_summary)

    specialties = list(rules["specialties"])

    used_model = False

    if model:
        model_specialties = [
            item
            for item in (model.get("specialties") or [])
            if isinstance(item, str) and item in KNOWN_SPECIALTIES
        ]

        if model_specialties:
            used_model = True

            # Model's picks lead; the rule layer's picks follow as
            # backup so a wrong model call cannot hide an obvious match.
            merged = model_specialties + [
                item for item in specialties if item not in model_specialties
            ]
            specialties = merged

    return {
        "specialties": specialties[:4],
        "urgency": rules["urgency"],
        "red_flags": rules["red_flags"],
        "case_summary": (
            (model or {}).get("case_summary")
            or _fallback_case_summary(form)
        ),
        "questions_for_doctor": (model or {}).get("questions_for_doctor") or [
            "What is the most likely cause of these symptoms?",
            "Do I need any tests before the next visit?",
            "What should make me come back sooner?",
        ],
        "before_the_visit": (model or {}).get("before_the_visit") or [
            "Bring any recent lab reports and a list of current medicines.",
            "Note when the symptoms are worst and what makes them better.",
        ],
        "ai_reading_used": used_model,
    }
