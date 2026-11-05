"""Explicitly opt-in live acceptance run. Never imported by the offline suite.

Run from the project root: python scripts/verify_live_demo.py --live
Uses configured providers/quota and the owner's Superstore demo CSV. The report
contains aggregate checks and provider metadata, never raw responses or rows.
"""
import argparse
import base64
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow real provider calls and quota usage")
    parser.add_argument("--pace", type=float, default=40, help="Minimum seconds between Groq-heavy questions")
    args = parser.parse_args()
    if not args.live:
        parser.error("Live calls require the explicit --live flag. No provider was called.")

    import numpy as np
    from backend.core import config
    from backend.core import llm_clients
    from backend.core.databuddy import DataBuddy
    from backend.legacy.ui_state import initialize_session, replace_dataset, reset_conversation

    path = ROOT / "uploads" / "Superstore.csv"
    buddy = DataBuddy(path)
    df = buddy.dataset.df
    expected_sales = round(float(df["Sales"].sum()), 2)
    expected_profit = round(float(df["Profit"].sum()), 2)
    expected_regions = {str(k): round(float(v), 2) for k, v in df.groupby("Region")["Sales"].sum().items()}
    expected_categories = {str(k): round(float(v), 2) for k, v in df.groupby("Category")["Sales"].sum().items()}
    report = {
        "date": "2026-10-22", "timezone": "Asia/Kolkata",
        "dataset": {"filename": path.name, "bytes": path.stat().st_size, "rows": len(df), "columns": len(df.columns)},
        "models": {"code": config.ANALYSIS_MODEL, "memory": config.MEMORY_MODEL,
                   "routing": config.CONVERSATION_MODEL, "explanation": config.EXPLANATION_MODEL,
                   "code_fallback": config.FALLBACK_MODEL},
        "expected": {"sales": expected_sales, "profit": expected_profit, "regional_sales": expected_regions},
        "checks": [], "provider_calls": [],
    }
    report_path = ROOT / "docs" / "LIVE_VERIFICATION_RESULTS.json"
    def save():
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    # Observe application-level provider calls without logging requests/responses.
    original_retry = llm_clients._retry
    def observe(call, provider):
        start = time.monotonic()
        event = {"provider": provider}
        try:
            value = original_retry(call, provider)
            event["outcome"] = "success"
            return value
        except llm_clients.ProviderError as exc:
            event.update(outcome="failed", safe_message=str(exc))
            raise
        finally:
            event["seconds"] = round(time.monotonic() - start, 2)
            report["provider_calls"].append(event)
    llm_clients._retry = observe

    def number_in(text, expected, tolerance=0.02):
        import re
        values = re.findall(r"-?\d+(?:,\d{3})*(?:\.\d+)?(?:[eE][+-]?\d+)?", text or "")
        return any(abs(float(v.replace(",", "")) - expected) <= tolerance for v in values)

    def array(value):
        if isinstance(value, dict) and "bdata" in value:
            return np.frombuffer(base64.b64decode(value["bdata"]), dtype=value["dtype"]).tolist()
        return value if isinstance(value, list) else []

    def chart_correct(result):
        if not result.chart_json:
            return False
        chart = json.loads(result.chart_json)
        observed = {}
        for trace in chart.get("data", []):
            if trace.get("type") != "bar":
                continue
            labels, values = (array(trace.get("y")), array(trace.get("x"))) if trace.get("orientation") == "h" else (array(trace.get("x")), array(trace.get("y")))
            observed.update({str(k): float(v) for k, v in zip(labels, values) if isinstance(v, (int, float))})
        return set(observed) == set(expected_regions) and all(abs(observed[k] - expected_regions[k]) < 0.02 for k in observed)

    def grouped_correct(result):
        return all(k in (result.result_text or "") and number_in(result.result_text, value) for k, value in expected_categories.items())

    plan = [
        ("remember_preference", "Remember that my preferred chart color for this demonstration is teal.", False, lambda r: r.status == "success"),
        ("total_sales", "What is the total Sales across the entire dataset? Give the exact amount.", True, lambda r: number_in(r.result_text, expected_sales)),
        ("explain_calculation", "How was that calculated?", False, lambda r: r.status == "success" and "Sales" in r.answer),
        ("top_region", "Which Region has the highest total Sales? Show its total Sales.", True, lambda r: max(expected_regions, key=expected_regions.get) in (r.result_text or "") and number_in(r.result_text, max(expected_regions.values()))),
        ("regional_chart", "Create a bar chart of total Sales by Region using all rows.", True, chart_correct),
        ("modify_chart", "Change the chart title to Regional Sales Overview, keeping its data unchanged.", True, lambda r: chart_correct(r) and "Regional Sales Overview" in str(json.loads(r.chart_json or "{}").get("layout", {}).get("title", {}))),
        ("total_profit", "What is the total Profit across the entire dataset? Give the exact amount.", True, lambda r: number_in(r.result_text, expected_profit)),
        ("row_count", "How many rows are in the entire dataset?", True, lambda r: number_in(r.result_text, len(df), 0)),
        ("category_sales", "Show the total Sales for each Category across all rows.", True, grouped_correct),
        ("average_discount", "What is the average Discount across the entire dataset? Return the raw decimal average with at least six decimal places.", True, lambda r: number_in(r.result_text, float(df["Discount"].mean()), 0.000001)),
        ("missing_sales", "How many missing values are in the Sales column?", True, lambda r: number_in(r.result_text, int(df["Sales"].isna().sum()), 0)),
        ("recall_old_preference", "What chart color did I ask you to remember earlier?", False, lambda r: "teal" in r.answer.casefold()),
    ]
    previous_heavy = None
    failures = 0
    for index, (name, question, heavy, verify) in enumerate(plan, 1):
        if heavy and previous_heavy is not None:
            delay = max(0, args.pace - (time.monotonic() - previous_heavy))
            if delay:
                time.sleep(delay)
        if heavy:
            previous_heavy = time.monotonic()
        start = time.monotonic()
        check = {"exchange": index, "name": name}
        try:
            result = buddy.ask(question)
            check.update(passed=bool(verify(result)), status=result.status,
                         memory_notice=result.memory_notice,
                         has_computed_evidence=bool(result.result_text), has_chart=bool(result.chart_json))
            if name in {"total_sales", "total_profit", "row_count", "average_discount", "missing_sales"}:
                # Bounded numerical aggregates only, never full model output.
                check["expected_value_found"] = check["passed"]
            if index in {6, 12}:
                check["rollover_passed"] = bool(buddy.conversation.memory_summary and not buddy.conversation.memory_notes)
                check["preference_retained_in_summary"] = "teal" in buddy.conversation.memory_summary.casefold()
        except llm_clients.ProviderError as exc:
            check.update(passed=False, error_type=type(exc).__name__, safe_message=str(exc))
        except Exception as exc:
            check.update(passed=False, error_type=type(exc).__name__)
        check.update(seconds=round(time.monotonic() - start, 2),
                     summary_chars=len(buddy.conversation.memory_summary), notes=len(buddy.conversation.memory_notes),
                     recent_exchanges=len(buddy.conversation.recent_turns))
        report["checks"].append(check)
        save()
        print(json.dumps(check), flush=True)
        if not check["passed"] or check.get("memory_notice") or check.get("rollover_passed") is False:
            failures += 1
        if "configured model" in (check.get("memory_notice") or ""):
            print("Stopping on a memory configuration failure before making further live calls.", flush=True)
            break
        if failures >= 3:
            print("Stopping after three failed checks to avoid wasting provider quota.", flush=True)
            break

    buddy.conversation.clear()
    report["reset_clears_memory"] = not any([buddy.conversation.memory_summary, buddy.conversation.memory_notes,
                                            buddy.conversation.recent_turns, buddy.conversation.chart_history,
                                            buddy.conversation.last_analysis])
    state = {}; initialize_session(state)
    replace_dataset(state, path.name, path.read_bytes())
    state["buddy"].conversation.memory_summary = "Synthetic replacement-check memory"
    replace_dataset(state, "replacement.csv", b"sales\n1\n")
    report["replacement_clears_memory"] = state["buddy"].conversation.memory_summary == ""
    report["separate_session_is_empty"] = DataBuddy(path).conversation.to_prompt_text() == "None yet."
    report["completed_exchanges"] = len(report["checks"])
    report["all_checks_passed"] = (len(report["checks"]) == 12
        and all(c["passed"] and c.get("rollover_passed", True) and not c.get("memory_notice") for c in report["checks"])
        and report["reset_clears_memory"] and report["replacement_clears_memory"] and report["separate_session_is_empty"])
    save()
    print(json.dumps({"report": str(report_path), "all_checks_passed": report["all_checks_passed"]}), flush=True)


if __name__ == "__main__":
    main()
