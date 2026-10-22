from pathlib import Path
from unittest.mock import MagicMock

import pytest
from streamlit.testing.v1 import AppTest

import config
import analyst
import message_handler
import conversation_state
from ui_state import initialize_session, replace_dataset

ROOT=Path(__file__).resolve().parents[1]


def test_initial_page_without_keys_is_usable():
    app=AppTest.from_file(str(ROOT/"web_app.py")).run(timeout=15)
    assert not app.exception
    assert app.get("file_uploader")[0].proto.max_upload_size_mb==20
    assert ".csv" in app.get("file_uploader")[0].proto.type
    assert ".xls" not in app.get("file_uploader")[0].proto.type
    assert any("API key" in item.value for item in app.warning)


def loaded_app(filename="sales.csv"):
    app=AppTest.from_file(str(ROOT/"web_app.py")).run(timeout=15)
    return app.get("file_uploader")[0].set_value((filename,b"region,sales\nNorth,10\nSouth,20\n","text/csv")).run(timeout=15)


def test_dataset_display_escapes_filename_and_reset_keeps_data():
    app=loaded_app("<b>sales</b>.csv")
    assert not app.exception
    rendered="\n".join(item.value for item in app.markdown)
    assert "&lt;b&gt;sales&lt;/b&gt;.csv" in rendered
    assert "<b>sales</b>.csv" not in rendered
    buddy=app.session_state["buddy"]
    buddy.conversation.add_turn("previous","answer")
    next(b for b in app.button if "Reset conversation" in b.label).click().run()
    assert not app.exception
    assert app.session_state["buddy"] is buddy
    assert buddy.conversation.recent_turns==[]
    next(b for b in app.button if "Remove dataset" in b.label).click().run()
    assert not app.exception
    assert app.session_state["buddy"] is None
    assert app.session_state["messages"]==[]


def test_input_disabled_without_provider_configuration():
    app=loaded_app()
    assert app.chat_input[0].disabled


def test_question_displays_actual_evidence_when_narration_fails(monkeypatch):
    monkeypatch.setattr(config,"GROQ_API_KEY","offline-placeholder")
    monkeypatch.setattr(message_handler,"route_message",lambda **kwargs: {"route":"analysis","reply":""})
    monkeypatch.setattr(analyst,"generate_code",lambda *args,**kwargs: "result = df['sales'].sum()")
    monkeypatch.setattr(analyst,"write_answer",MagicMock(side_effect=RuntimeError("private error body")))
    app=loaded_app()
    app.chat_input[0].set_value("total sales").run(timeout=15)
    assert not app.exception
    assert any("calculation completed" in item.value for item in app.markdown)
    assert any("30" in item.value for item in app.text)
    assert "private error body" not in "\n".join(item.value for item in app.markdown)


def test_memory_rollover_survives_rerun_and_reset_clears_it(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "offline-placeholder")
    monkeypatch.setattr(message_handler, "route_message", lambda **k: {"route": "conversation", "reply": "Noted."})
    summarize = MagicMock(side_effect=lambda p: "Combined memory." if '"new_notes"' in p else "Brief note.")
    monkeypatch.setattr(conversation_state, "call_memory_llm", summarize)
    app = loaded_app()
    for n in range(6):
        app.chat_input[0].set_value(f"hello {n}").run(timeout=15)
        assert not app.exception
    memory = app.session_state["buddy"].conversation
    assert memory.memory_summary == "Combined memory." and memory.memory_notes == []
    assert len(memory.recent_turns) == 6 and summarize.call_count == 6
    app.run(timeout=15)
    assert memory.memory_summary == "Combined memory." and summarize.call_count == 6
    next(b for b in app.button if "Reset conversation" in b.label).click().run()
    assert memory.memory_summary == "" and memory.memory_notes == []


def test_memory_failure_notice_is_safe_and_answer_remains(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "offline-placeholder")
    monkeypatch.setattr(message_handler, "route_message", lambda **k: {"route": "conversation", "reply": "Hello."})
    monkeypatch.setattr(conversation_state, "call_memory_llm", MagicMock(side_effect=RuntimeError("PRIVATE BODY")))
    app = loaded_app()
    app.chat_input[0].set_value("hello").run(timeout=15)
    assert not app.exception
    assert any(item.value == "Hello." for item in app.markdown)
    assert any("memory could not update" in item.value for item in app.caption)
    assert "PRIVATE BODY" not in "\n".join(item.value for item in app.caption)


def test_chart_export_not_generated_on_every_render(monkeypatch):
    import plotly.express as px
    import plotly.io as pio
    monkeypatch.setattr(pio,"to_html",MagicMock(side_effect=AssertionError("Export must be requested")))
    app=loaded_app()
    chart=px.bar(x=["North","South"],y=[10,20])
    app.session_state["messages"]=[{"id":"chart-one","role":"assistant","content":"Chart ready", "chart_json":pio.to_json(chart), "result_text":"North 10; South 20"}]
    app.run(timeout=15)
    assert not app.exception
    pio.to_html.assert_not_called()
    assert any(b.label=="Prepare HTML download" for b in app.button)


def test_real_upload_replacement_and_rejected_file_is_not_reparsed(monkeypatch):
    import ui_state
    app=loaded_app()
    app.get("file_uploader")[0].set_value(("sales.csv",b"sales\n99\n","text/csv")).run()
    assert not app.exception
    assert app.session_state["buddy"].dataset.df["sales"].sum()==99
    previous=app.session_state["buddy"]
    app.get("file_uploader")[0].set_value(("broken.csv",b"","text/csv")).run()
    assert not app.exception
    assert app.session_state["buddy"] is previous
    assert app.error
    factory=MagicMock(side_effect=AssertionError("Rejected file should not be parsed again"))
    monkeypatch.setattr(ui_state,"DataBuddy",factory)
    app.run()
    assert not app.exception
    factory.assert_not_called()
    assert app.session_state["buddy"] is previous
