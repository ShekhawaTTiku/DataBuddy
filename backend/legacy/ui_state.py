"""Small, UI-independent session helpers; uploads never become saved files."""
import hashlib
import uuid

from backend.core import config
from backend.core.databuddy import DataBuddy


def initialize_session(state) -> None:
    for key, value in {
        "buddy": None, "dataset_name": None, "dataset_info": None,
        "dataset_fingerprint": None, "messages": [], "uploader_generation": 0,
        "rejected_fingerprint": None,
        "rejected_error": None,
    }.items():
        if key not in state:
            state[key] = value


def upload_fingerprint(filename: str, data: bytes) -> str:
    digest = hashlib.sha256(filename.encode("utf-8") + b"\0")
    digest.update(data)
    return digest.hexdigest()


def replace_dataset(state, filename: str, data: bytes, factory=None) -> bool:
    """Only switch the active session after every replacement step succeeds."""
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise ValueError("This file is larger than the 20 MB upload limit.")
    fingerprint = upload_fingerprint(filename, data)
    if state.get("dataset_fingerprint") == fingerprint:
        return False
    buddy = (factory or DataBuddy)(data, filename=filename)
    profile = buddy.dataset
    info = {
        "rows": len(profile.df), "cols": len(profile.df.columns),
        "columns": [str(c) for c in profile.df.columns],
        "dtypes": {str(c): str(profile.df[c].dtype) for c in profile.df.columns},
        "missing": int(profile.df.isna().sum().sum()),
        "preview": profile.df.head(5), "warnings": list(profile.warnings),
    }
    state.update({"buddy": buddy, "dataset_name": filename, "dataset_info": info,
                  "dataset_fingerprint": fingerprint, "messages": [],
                  "rejected_fingerprint": None, "rejected_error": None})
    return True


def reset_conversation(state) -> None:
    if state.get("buddy") is not None:
        state["buddy"].conversation.clear()
    state["messages"] = []


def clear_dataset(state) -> None:
    generation = state.get("uploader_generation", 0) + 1
    reset_conversation(state)
    state.update({"buddy": None, "dataset_name": None, "dataset_info": None,
                  "dataset_fingerprint": None, "rejected_fingerprint": None,
                  "rejected_error": None,
                  "uploader_generation": generation})


def append_message(state, message: dict) -> None:
    message.setdefault("id", uuid.uuid4().hex)
    state["messages"] = (state.get("messages", []) + [message])[-config.MAX_UI_MESSAGES:]
