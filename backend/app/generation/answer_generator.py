# import os

# from dotenv import load_dotenv
# from google import genai
# from google.genai import types

# from .prompt import SYSTEM_PROMPT, build_prompt


# load_dotenv()


# class MedicalAnswerGenerator:

#     def __init__(self):

#         api_key = os.getenv("GEMINI_API_KEY")

#         if not api_key:
#             raise ValueError(
#                 "GEMINI_API_KEY is not set."
#             )

#         self.client = genai.Client(
#             api_key=api_key
#         )

#         self.model = "gemini-3.6-flash"

#     def generate(
#         self,
#         query: str,
#         retrieved_context: str
#     ) -> str:

#         prompt = build_prompt(
#             query=query,
#             retrieved_context=retrieved_context
#         )

#         try:

#             response = self.client.models.generate_content(
#                 model=self.model,
#                 contents=prompt,
#                 config=types.GenerateContentConfig(
#                     system_instruction=SYSTEM_PROMPT,
#                     temperature=0.2,
#                     max_output_tokens=800,
#                 )
#             )

#             if not response.text:
#                 return (
#                     "I couldn't generate an answer "
#                     "from the available information."
#                 )

#             return response.text.strip()

#         except Exception as error:

#             error_text = str(error)

#             if "503" in error_text:
#                 return (
#                     "The medical AI service is temporarily "
#                     "unavailable. Please try again in a moment."
#                 )

#             if "429" in error_text:
#                 return (
#                     "The medical AI service has temporarily "
#                     "reached its request limit. Please try "
#                     "again later."
#                 )

#             return (
#                 "I couldn't generate the answer right now. "
#                 "Please try again."
#             )





# import os
# import time

# from dotenv import load_dotenv
# from google import genai
# from google.genai import types

# from .prompt import SYSTEM_PROMPT, build_prompt


# load_dotenv()


# class MedicalAnswerGenerator:

#     def __init__(self):

#         api_key = os.getenv(
#             "GEMINI_API_KEY"
#         )

#         if not api_key:
#             raise ValueError(
#                 "GEMINI_API_KEY is not set."
#             )

#         self.client = genai.Client(
#             api_key=api_key
#         )

#         self.model = "gemini-3.6-flash"

#     def generate(
#         self,
#         query: str,
#         retrieved_context: str
#     ) -> str:

#         prompt = build_prompt(
#             query=query,
#             retrieved_context=retrieved_context
#         )

#         print(
#             "\n[GENERATION] Sending request to Gemini..."
#         )

#         start_time = time.perf_counter()

#         try:

#             response = (
#                 self.client.models.generate_content(
#                     model=self.model,
#                     contents=prompt,
#                     config=types.GenerateContentConfig(
#                         system_instruction=SYSTEM_PROMPT,

#                         temperature=0.2,

#                         # Increase from 800 so answers
#                         # don't get cut unnecessarily.
#                         max_output_tokens=1200,
#                     )
#                 )
#             )

#             elapsed = (
#                 time.perf_counter()
#                 - start_time
#             )

#             print(
#                 f"[GENERATION] Gemini request completed "
#                 f"in {elapsed:.3f} seconds"
#             )

#             if not response.text:

#                 print(
#                     "[GENERATION] Gemini returned "
#                     "an empty response."
#                 )

#                 return (
#                     "I couldn't generate an answer "
#                     "from the available information."
#                 )

#             return response.text.strip()

#         except Exception as error:

#             elapsed = (
#                 time.perf_counter()
#                 - start_time
#             )

#             print(
#                 f"[GENERATION ERROR] "
#                 f"Failed after {elapsed:.3f} seconds"
#             )

#             print(
#                 f"[GENERATION ERROR] "
#                 f"{type(error).__name__}: {error}"
#             )

#             error_text = str(error).lower()

#             if (
#                 "503" in error_text
#                 or "unavailable" in error_text
#                 or "overloaded" in error_text
#             ):

#                 return (
#                     "Gemini is temporarily unavailable "
#                     "or overloaded. Please try again."
#                 )

#             if "429" in error_text:

#                 return (
#                     "Gemini has temporarily reached "
#                     "its request limit. Please try again later."
#                 )

#             if "timeout" in error_text:

#                 return (
#                     "The Gemini request timed out. "
#                     "Please try again."
#                 )

#             return (
#                 "I couldn't generate the answer right now. "
#                 "Please try again."
#             )







import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .prompt import SYSTEM_PROMPT, build_prompt

load_dotenv()


class MedicalAnswerGenerator:

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=api_key)

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.5-flash-lite"
        )

    def generate(
        self,
        query: str,
        retrieved_context: str,
        conversation_history: str = ""
    ) -> str:

        prompt = build_prompt(
            query=query,
            retrieved_context=retrieved_context,
            conversation_history=conversation_history
        )

        print("\n[GENERATION] Sending request to Gemini...")

        start_time = time.perf_counter()

        try:

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2,
                    max_output_tokens=1200,
                )
            )

            elapsed = time.perf_counter() - start_time

            print(
                f"[GENERATION] Gemini request completed "
                f"in {elapsed:.3f} seconds"
            )

            # -----------------------------------------
            # RESPONSE DIAGNOSTICS
            # -----------------------------------------

            print("\n" + "=" * 70)
            print("GEMINI RESPONSE DEBUG")
            print("=" * 70)

            # Finish reason
            try:
                candidate = response.candidates[0]

                finish_reason = getattr(
                    candidate,
                    "finish_reason",
                    None
                )

                print(
                    f"Finish reason      : {finish_reason}"
                )

            except Exception as error:
                print(
                    f"Finish reason      : unavailable ({error})"
                )

            # Usage information
            try:
                usage = response.usage_metadata

                prompt_tokens = getattr(
                    usage,
                    "prompt_token_count",
                    None
                )

                output_tokens = getattr(
                    usage,
                    "candidates_token_count",
                    None
                )

                total_tokens = getattr(
                    usage,
                    "total_token_count",
                    None
                )

                print(
                    f"Prompt tokens      : {prompt_tokens}"
                )

                print(
                    f"Output tokens      : {output_tokens}"
                )

                print(
                    f"Total tokens       : {total_tokens}"
                )

            except Exception as error:
                print(
                    f"Token usage        : unavailable ({error})"
                )

            # Prompt feedback
            try:
                prompt_feedback = getattr(
                    response,
                    "prompt_feedback",
                    None
                )

                print(
                    f"Prompt feedback    : {prompt_feedback}"
                )

            except Exception:
                pass

            print("=" * 70)

            # -----------------------------------------
            # RESPONSE TEXT
            # -----------------------------------------

            if not response.text:

                print(
                    "[GENERATION] Gemini returned empty response."
                )

                return (
                    "I couldn't generate the answer "
                    "from the available information."
                )

            answer = response.text.strip()

            print(
                f"[GENERATION] Answer characters : {len(answer)}"
            )

            print(
                f"[GENERATION] Answer words      : "
                f"{len(answer.split())}"
            )

            return answer

        except Exception as error:

            elapsed = time.perf_counter() - start_time

            print(
                f"\n[GENERATION ERROR] "
                f"Failed after {elapsed:.3f} seconds"
            )

            print(
                f"[GENERATION ERROR] "
                f"{type(error).__name__}: {error}"
            )

            error_text = str(error).lower()

            if (
                "503" in error_text
                or "unavailable" in error_text
                or "overloaded" in error_text
            ):
                return (
                    "Gemini is temporarily unavailable "
                    "or overloaded. Please try again."
                )

            if "429" in error_text:
                return (
                    "Gemini has temporarily reached "
                    "its request limit. Please try again later."
                )

            if "timeout" in error_text:
                return (
                    "The Gemini request timed out. "
                    "Please try again."
                )

            return (
                "I couldn't generate the answer right now. "
                "Please try again."
            )