from datetime import datetime, timezone
from waste_utils import count_categories, calculate_recyclability_score


def generate_report(analysis, messages, summary="", name=""):
    items = analysis["items"]
    counts = count_categories(items)
    score = calculate_recyclability_score(items, counts)
    lines = ["EcoSort AI Report", datetime.now(timezone.utc).strftime("Generated: %Y-%m-%d %H:%M UTC"),
             "", f"Detected items: {len(items)}", f"Recyclability score: {score:.2f}%",
             "Score = recyclable item count / total item count; not weight or recovery rate.",
             "", "CATEGORY SUMMARY"]
    if name:
        lines.insert(1, f"Prepared for: {name}")
    for category, count in counts.items():
        lines.append(f"{category}: {count}")
    lines.extend(["", "DETECTED ITEMS"])
    for index, item in enumerate(items, 1):
        lines.extend([f"{index}. {item['item_name']}", f"Material: {item['material']}",
                      f"Category: {item['waste_category']}", f"Disposal: {item['disposal_method']}", ""])
    if not items:
        lines.append("No waste items were detected.")
    if summary:
        lines.extend(["", "AI CONVERSATION SUMMARY", summary])
    if messages:
        lines.extend(["", "FOLLOW-UP CONVERSATION"])
        for message in messages:
            label = "You" if message["role"] == "user" else "EcoSort"
            content = "[Waste photo uploaded]" if message.get("kind") == "image" else message["content"]
            lines.extend([f"{label}: {content}", ""])
    lines.extend(["", "AI identification may be uncertain. Confirm local disposal rules."])
    return "\n".join(lines)
