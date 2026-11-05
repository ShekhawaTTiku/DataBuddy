import sys

from backend.core.databuddy import DataBuddy
from backend.core.llm_clients import ProviderError


def main():
    if len(sys.argv) < 2:
        print("Usage: python app.py <path-to-csv-or-xlsx> (maximum 20 MB)")
        print("Chat commands: /state, /reset, /quit")
        sys.exit(1)

    path = sys.argv[1]

    # ------------------------------------------------------------------
    # Load and profile the dataset once
    # ------------------------------------------------------------------
    try:
        buddy = DataBuddy(path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading dataset: {type(e).__name__}: {e}")
        sys.exit(1)

    profile = buddy.dataset
    row_count = len(profile.df)
    col_count = len(profile.df.columns)
    print(f"Loaded {profile.filename} — {row_count:,} rows, {col_count} columns.")
    for warning in profile.warnings:
        print(f"Import note: {warning}")
    print("Session only: nothing is saved for later runs. Use non-sensitive demo data.")

    # ------------------------------------------------------------------
    # Question loop
    # ------------------------------------------------------------------
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not question:
            continue

        if question == "/quit":
            break

        if question == "/state":
            print("\n" + buddy.conversation.to_prompt_text())
            continue

        if question == "/reset":
            buddy.conversation.clear()
            print("Conversation state cleared.")
            continue

        try:
            result = buddy.ask(question)
            if result.chart_json:
                print("\n📊 [Chart generated — view in the web app for interactive display]")
            print(f"\n{result.answer}")
            if result.memory_notice:
                print(f"\n{result.memory_notice}")
            if result.result_text:
                print(f"\nComputed evidence:\n{result.result_text}")
            if result.visualization_suggestion:
                print(f"\n💡 {result.visualization_suggestion}")

        except ProviderError as error:
            print(f"\n{error}")
        except Exception:
            print("\nThis request could not be completed. Your dataset is still loaded; try a simpler question.")


if __name__ == "__main__":
    main()
