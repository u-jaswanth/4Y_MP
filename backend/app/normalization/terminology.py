import json
import re
from pathlib import Path

# Repo layout is <root>/app/... (this file lives at
# app/normalization/terminology.py), with data/ meant to sit as a
# sibling of the `app` package at the project root. Resolving it
# from __file__ means this works regardless of the working directory
# uvicorn/gunicorn happens to be started from - previously the
# default "data/medical_terminology.json" only worked if the process
# was launched from exactly the right directory.
_DEFAULT_TERMINOLOGY_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "medical_terminology.json"
)


class MedicalTerminology:

    def __init__(
        self,
        terminology_path=None
    ):
        self.terminology_path = Path(
            terminology_path or _DEFAULT_TERMINOLOGY_PATH
        )

        self.concepts = []
        self.alias_lookup = {}

        try:
            with open(
                self.terminology_path,
                "r",
                encoding="utf-8"
            ) as file:
                data = json.load(file)

        except FileNotFoundError:
            # Don't take down the whole ingestion/analysis pipeline
            # over an optional lookup table - normalize_observation()
            # already falls back to the raw observation name when
            # resolve() finds nothing, so an empty table just means
            # "no canonical aliasing", not a hard failure.
            print(
                f"[terminology] WARNING: {self.terminology_path} not found - "
                "continuing without canonical term aliasing. Lab test names "
                "will be used as-is instead of being mapped to standard names."
            )
            return

        self.concepts = data.get("concepts", [])

        self.alias_lookup = {}

        for concept in self.concepts:

            canonical_name = concept["canonical_name"]

            for alias in concept.get("aliases", []):

                normalized_alias = (
                    self._normalize(alias)
                )

                self.alias_lookup[
                    normalized_alias
                ] = concept

            normalized_canonical = (
                self._normalize(canonical_name)
            )

            self.alias_lookup[
                normalized_canonical
            ] = concept


    def _normalize(self, text: str) -> str:

        text = text.lower()

        text = re.sub(
            r"[^a-z0-9\s]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()


    def resolve(self, name: str):

        normalized_name = self._normalize(name)

        return self.alias_lookup.get(
            normalized_name
        )