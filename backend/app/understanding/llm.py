import json

from google import genai
from google.genai import types

from app.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL
)

from .prompts import (
    SYSTEM_PROMPT,
    build_prompt
)

from .schemas import (
    UniversalMedicalDocument
)


class DocumentUnderstandingLLM:

    def __init__(self):

        self.client = genai.Client(
            api_key=GEMINI_API_KEY
        )


    def understand(
        self,
        document_id: str,
        cleaned_text: str
    ) -> UniversalMedicalDocument:

        response = (
            self.client.models.generate_content(

                model=GEMINI_MODEL,

                contents=build_prompt(
                    cleaned_text,
                    document_id
                ),

                config=types.GenerateContentConfig(

                    system_instruction=
                    SYSTEM_PROMPT,

                    temperature=0,

                    response_mime_type=
                    "application/json"
                )
            )
        )


        if not response.text:

            raise RuntimeError(
                "LLM returned an empty response."
            )


        try:

            data = json.loads(
                response.text
            )

        except json.JSONDecodeError as error:

            print("\nRAW LLM RESPONSE:")
            print(response.text)

            raise RuntimeError(
                "LLM returned invalid JSON."
            ) from error


        try:

            return (
                UniversalMedicalDocument
                .model_validate(data)
            )

        except Exception as error:

            print("\n==============================")
            print("LLM JSON FAILED SCHEMA VALIDATION")
            print("==============================")

            print(
                json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False
                )
            )

            print(
                "\nVALIDATION ERROR:"
            )

            print(error)

            raise