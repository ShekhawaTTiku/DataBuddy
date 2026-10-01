import sys

from databuddy import DataBuddy


def main():
    if len(sys.argv) < 2:
        print("Usage: python app.py <path-to-csv-or-excel>")
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
            if result.visualization_suggestion:
                print(f"\n💡 {result.visualization_suggestion}")

        except Exception as e:
            print(f"\nError: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
