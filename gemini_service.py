import json
from google import genai
from google.genai import types

from prompt import ANALYZE_WASTE_PROMPT


def analyze_waste_image(client, image, model_name):
    response = client.models.generate_content(
        model=model_name,
        contents=[ANALYZE_WASTE_PROMPT, image],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    data = json.loads(response.text)

    return data