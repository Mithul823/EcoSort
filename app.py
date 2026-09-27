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
"""
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=[prompt, image]
)

print(response.text)