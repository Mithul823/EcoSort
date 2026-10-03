import hashlib
import json

from image_utils import image_for_chat
from prompt import WELCOME_MESSAGE_TEMPLATE


def start_conversation(state):
    state["messages"] = [{"role": "assistant", "kind": "text", "welcome": True,
                          "content": WELCOME_MESSAGE_TEMPLATE.format(name=state["name"])}]
    state["analyses"] = {}
    state["analysis_data"] = None
    state["report"] = None
    state["upload_version"] = state.get("upload_version", 0) + 1


def combined_analysis(state):
    return {"items": [item for analysis in state["analyses"].values() for item in analysis["items"]]}


def record_analysis(state, original_bytes, image, data):
    image_id = hashlib.sha256(original_bytes).hexdigest()
    state["analyses"][image_id] = data
    state["analysis_data"] = data
    state["messages"].extend([
        {"role": "user", "kind": "image", "content": image_for_chat(image)},
        {"role": "assistant", "kind": "text",
         "content": "Photo analysis: " + json.dumps(data, ensure_ascii=False)},
    ])
    state["report"] = None


def has_conversation(state):
    return any(not message.get("welcome") for message in state["messages"])
