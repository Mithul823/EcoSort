def count_categories(items): 
    category_counts = {}
    for item in items:
        category = item["waste_category"]

        if category in category_counts:
            category_counts[category] += 1 
        else:
            category_counts[category] = 1
    return category_counts

def calculate_recyclability_score(items, category_counts):

    total_items = len(items)
    if total_items == 0: return 0
    recyclable_items = category_counts.get("Recyclable", 0)
    score = (recyclable_items / total_items) * 100
    return score