CATEGORIES = ["Recyclable", "Organic", "E-Waste", "Hazardous", "General Waste"]

ITEM_FIELDS = ("item_name", "material", "waste_category", "disposal_method")

def validate_analysis(data):
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("The analysis must contain a list of items.")
    for item in data["items"]:
        if not isinstance(item, dict):
            raise ValueError("Invalid item.")
        for field in ITEM_FIELDS:
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError("An item is missing a required field.")
        if item["waste_category"] not in CATEGORIES:
            raise ValueError("Unknown waste category.")
    return data


def count_categories(items):
    category_counts = dict.fromkeys(CATEGORIES, 0)
    for item in items:
        category_counts[item["waste_category"]] += 1
    return category_counts


def calculate_recyclability_score(items, category_counts):
    if not items:
        return 0
    return category_counts.get("Recyclable", 0) / len(items) * 100
