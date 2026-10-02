import os

from dotenv import load_dotenv
from google import genai
from PIL import Image
from prompt import ANALYZE_WASTE_PROMPT
from gemini_service import analyze_waste_image
from waste_utils import count_categories, calculate_recyclability_score


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

image = Image.open("test_waste.jpg")

data = analyze_waste_image(
    client=client,
    image=image,
    model_name="gemini-3.5-flash"
)
print("\nDetected Waste Items:\n")

for index, item in enumerate(data["items"], start=1):
    print(f"Item {index}")
    print(f"Name: {item['item_name']}")
    print(f"Material: {item['material']}")
    print(f"Waste Category: {item['waste_category']}")
    print(f"Disposal Method: {item['disposal_method']}")
    print("-" * 80)

items = data["items"]
category_counts = count_categories(items)
print("\nWaste Category Summary:\n")
for category, count in category_counts.items():
    print(f"{category}: {count}")

recyclability_score = calculate_recyclability_score(
    items,
    category_counts
)
print("\nRecyclability Score:")
print(f"{recyclability_score:.2f}%")