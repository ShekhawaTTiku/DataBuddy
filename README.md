# DataBuddy

Working repository: [ShekhawaTTiku/DataBuddynew](https://github.com/ShekhawaTTiku/DataBuddynew) (private). See [the GitHub checkpoint record](docs/GITHUB_CHECKPOINT.md) for the grouped commits and local-only data exclusions.

A personal data-analysis demonstration: ask questions about a CSV or XLSX file, run generated pandas calculations, and inspect computed evidence and interactive Plotly charts.

The dedicated React/TypeScript frontend and FastAPI backend wrap the working Python core. It includes uploads, temporary chat, progressive answers, early computed results/charts, exports and session usage controls. Responses support reconnect and Stop while preserving the six-exchange memory cycle. See [streaming and recovery](docs/STREAMING.md). The legacy Streamlit and terminal interfaces remain available.

## Dedicated web app

See [working setup and deployment](docs/WEBAPP_SETUP.md) for the finalized stack and commands. Start the API with `python -m uvicorn api.main:app --port 8000 --workers 1 --no-access-log`; in `frontend`, run `npm ci` then `npm run dev`. Install `requirements-api-lock.txt` first and configure provider keys privately in the existing `.env`.

The web app has a 15-message session allowance, subject to one usage adjustment; clear/reset keeps the allowance. Docker/Render and Cloudflare Pages configuration is included, but nothing is deployed. [Verification](docs/WEBAPP_VERIFICATION.md) records tests and the remaining Linux hosting check.

## Legacy interfaces

Use Python 3.11.9 (the verified version), create a virtual environment, and install `requirements.txt`. Copy `.env.example` to `.env` and set a Groq and/or Mistral key. Add a Gemini key for primary conversation summarization; Mistral can also handle memory when Gemini is unavailable. Keep real keys private. Then run:

```powershell
python -m streamlit run web_app.py
```

For the terminal:

```powershell
python app.py examples/demo_sales.csv
```

For offline regression checks:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

See [setup and configuration](docs/SETUP.md) for full instructions and the Windows dependency snapshot.

## Actual capabilities and limits

- CSV is the main demo format. XLSX reads its first sheet with openpyxl. XLS, XLSM and XLSB are not supported.
- Maximum upload: **20 MiB (20,971,520 bytes)**, displayed as 20 MB. Processing limits also apply: 250,000 rows, 200 columns and bounded cell/profile/output sizes.
- Uploads are loaded from memory, not saved as dataset files. Conversation, summaries and chart context are session-only; no database, disk history or account system is used. One brief note per completed exchange becomes one rolling paragraph after six notes; the latest six full exchanges are also retained by default.
- Six recent turns and five recent charts are retained by default; the UI displays up to 40 recent messages. Reset clears conversation/chart context; Remove dataset clears the active dataset too.
- Ambiguous or mixed date text stays unchanged with a notice. Leading-zero CSV identifiers remain text. CSV uses comma separators and pandas default missing-value markers.
- Answers include computed evidence. A narration failure preserves the calculation/chart. Optional visualization suggestions are disabled by default to reduce calls.
- Groq handles code and result narration; Gemini handles memory. Mistral handles routing/chat/explanation and is the fallback for all Groq/Gemini roles. Summary failure preserves answers and bounded recent context. Model access and free quotas depend on the provider account. No paid hosting, paid upgrade or live deployment is enabled. See [provider and memory behavior](docs/PROVIDERS_AND_MEMORY.md).

## Privacy and execution

Use non-sensitive, trusted demonstration datasets. Provider prompts may contain sample rows, statistics, category values, results and conversation context. Basic code checks, a child-process timeout and output limits reduce accidental unsafe behavior; **this is not a hardened sandbox for arbitrary public code execution**. See [security and privacy](docs/SECURITY_AND_PRIVACY.md).

The dedicated web app exports PNG and self-contained HTML from the analysis panel. Exports contain the plotted data. The legacy Streamlit HTML export still loads Plotly from the internet.

## Documentation

Start with the [documentation index](docs/README.md), [work log](docs/WORK_LOG.md), [architecture](docs/ARCHITECTURE.md), [demo checklist](docs/DEMO_CHECKLIST.md), and [validation record](docs/VALIDATION.md).

Work takes place in `D:/projects/databuddy 2.0`; the original `D:/projects/DataBuddy` remains the local backup. The dedicated frontend/API and their documentation are included in this repository. The owner authorized grouped commits and pushes on 2026-10-27; see [the checkpoint record](docs/GITHUB_CHECKPOINT.md). Hosting configuration is included, but no deployment is performed by that publication.
