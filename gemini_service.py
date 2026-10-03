import json
import time

import httpx
from google import genai
from google.genai import types
from google.genai.errors import APIError

from prompt import ANALYZE_WASTE_PROMPT, CHAT_PROMPT, SUMMARY_REQUEST_PROMPT
from settings import get_setting
from waste_utils import CATEGORIES, ITEM_FIELDS, validate_analysis


class EcoSortError(Exception):
    pass


def create_client():
    api_key = get_setting("GEMINI_API_KEY")
    if not api_key:
        raise EcoSortError("Add GEMINI_API_KEY to your .env or Streamlit secrets first.")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=20000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )


def generate_response(client, contents, config):
    model = get_setting("GEMINI_MODEL", "gemini-3.5-flash-lite")
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model, contents=contents, config=config
            )
            if not response.text or not response.text.strip():
                raise EcoSortError("Gemini could not produce an answer. Try a clearer photo or rephrase your question.")
            return response.text
        except APIError as error:
            if error.code in (429, 500, 502, 503, 504):
                message = "Gemini is busy or temporarily unavailable. Please try again shortly."
            elif error.code in (401, 403):
                raise EcoSortError("Gemini could not authenticate. Check your API key and model access.") from None
            elif error.code == 404:
                raise EcoSortError("The configured Gemini model is unavailable. Check GEMINI_MODEL with list_model.py.") from None
            else:
                raise EcoSortError("Gemini could not process this request. Check the model setting or try another image.") from None
        except httpx.TransportError:
            message = "The connection to Gemini timed out or failed. Please try again."

        if attempt == 2:
            raise EcoSortError(message) from None
        time.sleep(attempt + 1)


def analyze_waste_image(client, image):
    fields = {name: {"type": "string"} for name in ITEM_FIELDS}
    fields["waste_category"]["enum"] = CATEGORIES
    schema = {
        "type": "object",
        "properties": {"items": {"type": "array", "items": {
            "type": "object", "properties": fields, "required": list(fields),
        }}},
        "required": ["items"],
    }
    text = generate_response(client, [ANALYZE_WASTE_PROMPT, image],
        types.GenerateContentConfig(response_mime_type="application/json",
                                    response_json_schema=schema))
    try:
        return validate_analysis(json.loads(text))
    except (ValueError, TypeError):
        raise EcoSortError("Gemini returned an incomplete analysis. Please try again.") from None


def conversation_contents(analysis, messages):
    contents = [types.Content(role="user", parts=[types.Part.from_text(
        text="Structured waste analysis across this conversation: " + json.dumps(analysis))])]
    for message in messages:
        if message.get("welcome"):
            continue
        role = "model" if message["role"] == "assistant" else "user"
        if message.get("kind") == "image":
            part = types.Part.from_bytes(data=message["content"], mime_type="image/jpeg")
        else:
            part = types.Part.from_text(text=message["content"])
        contents.append(types.Content(role=role, parts=[part]))
    return contents


def answer_question(client, analysis, messages, question):
    contents = conversation_contents(analysis, messages)
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=question)]))
    return generate_response(client, contents,
        types.GenerateContentConfig(system_instruction=CHAT_PROMPT))


def summarize_conversation(client, analysis, messages):
    from waste_utils import count_categories, calculate_recyclability_score

    counts = count_categories(analysis["items"])
    score = calculate_recyclability_score(analysis["items"], counts)
    contents = conversation_contents(analysis, messages)
    contents.append(types.Content(role="user", parts=[types.Part.from_text(
        text=SUMMARY_REQUEST_PROMPT + "\nPython counts: " + json.dumps(counts)
             + f"\nPython recyclability score: {score:.2f}%")]))
    return generate_response(client, contents,
        types.GenerateContentConfig(system_instruction=CHAT_PROMPT))
