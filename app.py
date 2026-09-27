import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

image = Image.open("test_waste.jpg")

prompt = """
Analyze this waste image.

Identify the visible waste items.

Return only valid JSON in this exact structure:
{
    "items": [
        {
            "item_name": "string",
            "material:: "string",
            "waste_category": "string",
            "disposal_method": "string"
        }
    ]
}

Rules:
- Return JSON only
- Do not include markdown
- Do not include explanation text before or after JSON 
"""
response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=[prompt, image],
    config=types.GenerateContentConfig(
        response_mime_type="application/json"
    )
)

print(response.text)