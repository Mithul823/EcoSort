ANALYZE_WASTE_PROMPT = """
Analyze this waste image.

Identify all clearly visible waste items.

Return ONLY valid JSON in this exact structure:

{
  "items": [
    {
      "item_name": "string",
      "material": "string",
      "waste_category": "string",
      "disposal_method": "string"
    }
  ]
}

For waste_category, you MUST choose exactly one of these values:

- Recyclable
- Organic
- E-Waste
- Hazardous
- General Waste

Classification rules:

- Recyclable:
  Paper, cardboard, recyclable plastic, glass, metal cans, etc.

- Organic:
  Food waste, fruit peels, vegetable waste, biodegradable food matter.

- E-Waste:
  Electronic devices, cables, chargers, circuit boards, electronic components.

- Hazardous:
  Batteries, chemicals, fluorescent lamps, medical waste, or potentially dangerous materials.

- General Waste:
  Items that do not clearly belong to the categories above or are normally non-recyclable.

Important:
- Choose only ONE category for each item.
- Never combine categories.
- Do not invent new category names.
- If uncertain, use General Waste.
- Return JSON only.
- Do not include markdown.
- Do not add explanation before or after the JSON.
"""