from pathlib import Path
import pytest
import config
from ui_state import initialize_session, replace_dataset, clear_dataset, reset_conversation, append_message, upload_fingerprint


def new_state():
    state={}; initialize_session(state); return state


def test_same_name_changed_contents_reload():
    state=new_state()
    replace_dataset(state,"sales.csv",b"sales\n10\n")
    previous=state["buddy"]
    state["messages"].append({"role":"user","content":"old"})
    replace_dataset(state,"sales.csv",b"sales\n20\n")
    assert state["buddy"] is not previous
    assert state["buddy"].dataset.df["sales"].sum()==20
    assert state["messages"]==[]


def test_identical_upload_does_not_reset():
    state=new_state(); data=b"sales\n10\n"
    assert replace_dataset(state,"sales.csv",data)
    previous=state["buddy"]
    assert not replace_dataset(state,"sales.csv",data)
    assert state["buddy"] is previous
    assert upload_fingerprint("sales.csv",memoryview(data))==state["dataset_fingerprint"]


def test_invalid_replacement_keeps_previous_dataset_and_messages():
    state=new_state(); replace_dataset(state,"sales.csv",b"sales\n10\n")
    previous=state["buddy"]; fingerprint=state["dataset_fingerprint"]
    state["messages"].append({"content":"keep this"})
    with pytest.raises(ValueError): replace_dataset(state,"bad.csv",b"")
    assert state["buddy"] is previous
    assert state["dataset_fingerprint"]==fingerprint
    assert state["messages"]==[{"content":"keep this"}]


def test_upload_limit_before_factory(monkeypatch):
    state=new_state(); monkeypatch.setattr(config,"MAX_UPLOAD_BYTES",4)
    def never(*args,**kwargs): pytest.fail("oversized file reached loader")
    with pytest.raises(ValueError,match="20 MB"): replace_dataset(state,"big.csv",b"12345",factory=never)


def test_reset_keeps_dataset_clear_removes_it():
    state=new_state(); replace_dataset(state,"sales.csv",b"sales\n10\n")
    buddy=state["buddy"]; buddy.conversation.add_turn("hello","hi")
    reset_conversation(state)
    assert state["buddy"] is buddy
    assert buddy.conversation.recent_turns==[]
    clear_dataset(state)
    assert state["buddy"] is None
    assert state["dataset_name"] is None
    assert state["messages"]==[]
    assert state["uploader_generation"]==1


def test_display_history_bounded_and_identified(monkeypatch):
    monkeypatch.setattr(config,"MAX_UI_MESSAGES",4)
    state=new_state()
    for i in range(10): append_message(state,{"role":"user","content":str(i)})
    assert [m["content"] for m in state["messages"]]==["6","7","8","9"]
    assert len({m["id"] for m in state["messages"]})==4
