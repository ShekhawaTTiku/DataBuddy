from types import SimpleNamespace

from backend import cli as app
from backend.core.databuddy import AskResult


def test_cli_shows_preserved_computation(monkeypatch, capsys):
    buddy = SimpleNamespace(
        dataset=SimpleNamespace(filename="demo.csv", df=SimpleNamespace(columns=["sales"], __len__=lambda: 1), warnings=[]),
        ask=lambda question: AskResult(answer="Narration unavailable.", result_text="30", status="partial", memory_notice="Memory temporarily unavailable."),
    )
    # The dataset is real so ordinary CLI dimension reporting is also exercised.
    import pandas as pd
    buddy.dataset.df = pd.DataFrame({"sales": [10, 20]})
    monkeypatch.setattr(app, "DataBuddy", lambda _: buddy)
    monkeypatch.setattr(app.sys, "argv", ["app.py", "demo.csv"])
    answers = iter(["total sales", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    app.main()
    output = capsys.readouterr().out
    assert "Computed evidence:\n30" in output
    assert "Session only" in output
    assert "Memory temporarily unavailable." in output


def test_cli_reset_clears_session_without_provider_calls(monkeypatch, capsys):
    from pathlib import Path
    from backend.core.databuddy import DataBuddy
    buddy = DataBuddy(Path(__file__).resolve().parents[1] / "examples" / "demo_sales.csv")
    buddy.conversation.add_turn("previous", "answer")
    monkeypatch.setattr(app, "DataBuddy", lambda _: buddy)
    monkeypatch.setattr(app.sys, "argv", ["app.py", "demo.csv"])
    answers = iter(["/state", "/reset", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    app.main()
    assert buddy.conversation.recent_turns == []
    assert "Conversation state cleared" in capsys.readouterr().out
