<div align="center">

# 🤖 DataBuddy

### Ask Questions About Your CSV and Excel Data

*A conversational data analyst with a React interface, a FastAPI backend, computed answers and interactive charts.*

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-Web%20App-149ECA?style=for-the-badge&logo=react&logoColor=white)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-Frontend-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![LLM APIs](https://img.shields.io/badge/LLM-Groq%20%7C%20Mistral%20%7C%20Gemini-6C63FF?style=for-the-badge)](#-provider-configuration)

**[Live Demo](https://databuddy-demo.pages.dev/) · [Overview](#-overview) · [How It Works](#-how-it-works) · [Setup](#-installation) · [Privacy](#-data-and-privacy)**

</div>

---

<div align="center">

### 🌐 Live Demo

**[Try DataBuddy → databuddy-demo.pages.dev](https://databuddy-demo.pages.dev/)**

[![Live Demo](https://img.shields.io/badge/Live_Demo-Open_App-237A70?style=for-the-badge&logo=cloudflarepages&logoColor=white)](https://databuddy-demo.pages.dev/)

</div>

The frontend runs on **Cloudflare Pages Free** and the Docker-packaged API runs on **Render Free**. The API can sleep during inactivity, so the first request may take about a minute to wake it. Use **Try sample data** to explore the interface with a small built-in dataset.

---

## ✨ Overview

**DataBuddy** lets you upload a CSV or XLSX file and explore it through natural-language questions. It profiles the dataset, routes your request, generates pandas calculations when needed, executes them in a bounded child process, and explains the computed results.

The web app pairs a **React/TypeScript frontend** with a **FastAPI backend** around the Python analysis core. You can inspect calculation evidence, open interactive Plotly charts, export charts, and follow answers as text arrives. Dataset and conversation state are temporary and held in server memory.

| 📁 Input | 💬 Questions | 🧮 Analysis | 📊 Output |
|:---:|:---:|:---:|:---:|
| CSV or first-sheet XLSX | Natural-language questions and follow-ups | Generated pandas code with execution limits | Progressive answers, computed tables and interactive charts |

---

## 🚀 Features

- 📂 Upload CSV or XLSX files up to **20 MiB**, or start with sample data.
- 🔎 Preview your dataset and inspect column types, missing values and import notices.
- 💬 Ask analysis questions and follow-ups, or explain the previous calculation. Greetings, introductions and general questions work before an upload.
- 🐼 Inspect computed results and the calculation code behind an answer.
- 📈 Open interactive Plotly charts and export PNG or self-contained HTML files.
- ⚡ Read progressive answers and see ready results or charts while narration is arriving.
- ⏹️ Stop an active response or reconnect to the existing response after a reload.
- 🧠 Keep bounded conversation context with summaries updated in six-exchange cycles.
- 🧭 Choose dataset-aware suggestions for exploration, charts, comparisons, trends and data quality.
- 🌗 Use light/dark themes and a layout that adapts to desktop and mobile screens.
- 🔁 Use Groq, Gemini and Mistral with configured fallback and session usage feedback.

---

## 🔄 How It Works

```text
React / TypeScript frontend
        │
        ▼
FastAPI session API
        │
        ▼
Load CSV or first-sheet XLSX into memory
        │
        ▼
Profile columns, types, missing values and sample rows
        │
        ▼
Route the message
        │
        ├── Conversation / time / explain previous analysis
        │
        └── Data-analysis question
                  │
                  ▼
          Generate pandas code
                  │
                  ▼
          Execute in a child process
          with code, time and output limits
                  │
                  ▼
          Publish computed evidence and charts
                  │
                  ▼
          Stream the result explanation
        │
        ▼
Update bounded conversation memory and usage
```

Provider prompts may include sample rows, dataset statistics, conversation context and computed results. The execution checks are **not a hardened security sandbox**. See [Data and Privacy](#-data-and-privacy).

---

## ⚙️ Requirements

- **Python 3.11** for the backend and analysis core.
- **Node.js 24** and npm for the frontend.
- Groq, Gemini and Mistral API keys for the configured primary and fallback roles.
- Network access to the providers and enough memory for the dataset and calculation worker.
- Docker when running the packaged backend locally.

`requirements/api-lock.txt` pins the tested Python API runtime. `frontend/package-lock.json` locks the browser dependencies. The optional Streamlit and terminal entry points are retained in the repository.

---

## 📦 Installation

### 1. Clone the Repository and Install Backend Dependencies

```bash
git clone https://github.com/ShekhawaTTiku/DataBuddy.git
cd DataBuddy
python -m venv .venv
```

Activate the virtual environment. In Windows PowerShell, run

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux, run

```bash
source .venv/bin/activate
```

Then install the API dependencies

```bash
python -m pip install -r requirements/api-lock.txt
```

### 2. Configure Provider Keys

On a fresh clone, copy `.env.example` to `.env` and enter your own keys. The core loads this file from the repository root.

```dotenv
GROQ_API_KEY=your-groq-key
GEMINI_API_KEY=your-gemini-key
MISTRAL_API_KEY=your-mistral-key
DATABUDDY_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
EXEC_TIMEOUT_SECONDS=30
DEBUG=false
```

Keep real keys private. Hosted backend keys belong in Render's **Environment Variables** section. The frontend's `VITE_API_URL` is a public API address and must contain no credentials.

### 3. Install Frontend Dependencies

```bash
cd frontend
npm ci
```

---

## ▶️ Usage

### Dedicated Web App

Start the backend from the repository root with the virtual environment active

```bash
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

In a second terminal, start the frontend

```bash
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`. Vite forwards local `/api` requests to port 8000. Leave `VITE_API_URL` empty for this setup. The health endpoint is `http://127.0.0.1:8000/api/health`.

Start chatting immediately. Upload a dataset or use the sample when you want calculations or charts. Your introductory conversation and memory carry into the first upload. Uploads support **CSV and the first worksheet of XLSX**, up to **20 MiB (20,971,520 bytes)**. Additional row, column and processing limits apply.

### Terminal Chat

From the repository root, run

```bash
python -m backend.cli examples/demo_sales.csv
```

| Command | Action |
|---|---|
| `/state` | Display the current in-memory conversation context. |
| `/reset` | Clear conversation context for this run. |
| `/quit` | Exit the session. |

The terminal interface also uses temporary state. For the retained Streamlit interface, install `requirements/legacy.txt` and run `python -m streamlit run web_app.py`.

### Example Questions

- “Which region has the highest total sales?”
- “Show monthly revenue as a line chart.”
- “Compare the average order value by category.”
- “How did you calculate the previous result?”

### Offline Checks

```bash
python -m pip install -r requirements/dev.txt
python -m pytest -q
```

In `frontend`, run `npm test` and `npm run build`. Regression tests use fake provider responses and consume no live model quota. Historical test and resource measurements are recorded in [verification](docs/WEBAPP_VERIFICATION.md) and [container verification](docs/CONTAINER_VERIFICATION.md).

---

## 🧠 Provider Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GROQ_API_KEY` | User supplied | Authenticate analysis-code generation and result narration. |
| `ANALYSIS_MODEL` | `openai/gpt-oss-120b` | Groq-hosted analysis and narration model. |
| `GEMINI_API_KEY` | User supplied | Authenticate conversation-memory summaries. |
| `MEMORY_MODEL` | `gemini-3.5-flash-lite` | Primary memory-summary model. |
| `MISTRAL_API_KEY` | User supplied | Authenticate routing, conversation, explanation and fallback. |
| `MISTRAL_CHAT_MODEL` | `ministral-8b-latest` | Route messages and answer ordinary conversation. |
| `MISTRAL_EXPLANATION_MODEL` | `ministral-14b-latest` | Explain the last successful analysis. |
| `MISTRAL_FALLBACK_MODEL` | `ministral-14b-latest` | Fallback for Groq analysis/narration and Gemini memory. |
| `DATABUDDY_TIMEZONE` | `Asia/Kolkata` | Time zone for local-time answers. |
| `EXEC_TIMEOUT_SECONDS` | `5` | Calculation deadline, configurable from 1 to 30 seconds. The deployment uses 30. |
| `DEBUG` | `false` | Enable diagnostic logging. Keep disabled for normal demonstrations. |

These defaults come from `backend/core/config.py`. Provider access, model aliases and free quotas depend on your account. Each memory cycle folds six brief exchange notes into a rolling summary while retaining bounded recent exchanges and chart context. See [provider and memory behavior](docs/PROVIDERS_AND_MEMORY.md).

For hosted builds, set `VITE_API_URL` to the Render API origin and set `DATABUDDY_ORIGINS` on Render to the exact frontend origin. The current frontend origin is `https://databuddy-demo.pages.dev`. See [setup and deployment](docs/WEBAPP_SETUP.md).

---

## 🧩 Project Structure

```text
DataBuddy/
├── backend/
│   ├── api/                    # FastAPI sessions, datasets and streamed responses
│   ├── core/                   # Analysis, providers, memory and execution
│   │   └── prompts/            # Model prompt templates
│   ├── legacy/                 # Retained Streamlit UI and state adapters
│   └── cli.py                  # Terminal interface
├── frontend/
│   ├── src/                    # React/TypeScript chat UI and analysis panels
│   ├── public/                 # Static assets and Cloudflare headers
│   └── tests/                  # Browser-independent frontend tests
├── requirements/               # API, locked runtime, legacy and test dependencies
├── tests/                      # Offline Python regression tests
├── scripts/                    # Local fixtures and acceptance checks
├── docs/                       # Setup, architecture and verification records
├── examples/                   # Small demonstration dataset
├── app.py                      # Compatibility launcher for the terminal UI
├── web_app.py                  # Compatibility launcher for Streamlit
├── Dockerfile                  # Production API image
└── render.yaml                 # Render Free blueprint
```

---

## 🔐 Data and Privacy

Uploaded files are sent to the backend and parsed in memory. Dataset and conversation state are session-only, with no database or saved chat history. The browser stores a session token in tab-scoped session storage. Restart, inactivity expiry or service recycling can end a session and require a fresh upload. Closing the browser does not guarantee immediate deletion from server memory.

Provider prompts can contain column names, sample values, statistics, questions, conversation context, generated code and computed results. Exported charts contain plotted data. Use trusted, non-sensitive demonstration datasets and keep API keys private.

Generated calculations run with basic code checks, a child-process timeout and output limits. **These are not a hardened security sandbox for arbitrary public code execution.** See [security and privacy](docs/SECURITY_AND_PRIVACY.md).

---

## ⚠️ Limitations

| Area | Current limitation |
|---|---|
| Uploads | 20 MiB maximum, up to 250,000 rows and 200 columns, with further cell/profile/output bounds. |
| Excel formats | First-sheet `.xlsx` support. `.xls`, `.xlsm` and `.xlsb` are unsupported. |
| Chat entry | Model-backed conversation works before upload. Calculations and dataset charts require a loaded file or sample. |
| Session allowance | Starts at 15 messages and can be adjusted once under the usage policy. Clear/reset preserves it. |
| Persistence | Data and chat context live in memory and can be lost on expiry or restart. |
| Free hosting | Render can sleep or restart. CPU and memory limits affect processing time and which datasets fit. |
| Model availability | Responses depend on provider access, quotas and fallback availability. |
| Execution | Basic safeguards are intended for trusted personal demonstrations. |
| Hosted verification | See the dated acceptance record for the current release checks and remaining hosting limits. |

---

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| **React / TypeScript / Vite** | Frontend, typed UI state and production build |
| **Custom CSS / Tailwind / Streamdown** | Themes, progressive Markdown, math and diagrams |
| **FastAPI / Uvicorn** | Python HTTP API and streamed response delivery |
| **pandas / NumPy / openpyxl** | Dataset loading, profiling and calculations |
| **Plotly / react-plotly.js** | Interactive charts and chart exports |
| **Groq** | Analysis-code generation and result narration |
| **Gemini** | Primary conversation-memory summaries |
| **Mistral** | Routing, conversation, explanations and fallback |
| **Docker / Render** | Packaged Python backend and free API hosting |
| **Cloudflare Pages** | Free static frontend hosting |
| **pytest / Node test runner** | Offline backend and frontend regression checks |

---

## 📚 Further Reading

- [Documentation index](docs/README.md)
- [Setup and deployment](docs/WEBAPP_SETUP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Streaming and recovery](docs/STREAMING.md)
- [Provider and memory behavior](docs/PROVIDERS_AND_MEMORY.md)
- [Verification results](docs/WEBAPP_VERIFICATION.md)
- [Linux container and resource checks](docs/CONTAINER_VERIFICATION.md)
- [Security and privacy](docs/SECURITY_AND_PRIVACY.md)
- [Work log](docs/WORK_LOG.md)

---

## 👤 Maintainer

**Digvijay Singh Shekhawat**

[![GitHub](https://img.shields.io/badge/GitHub-@ShekhawaTTiku-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/ShekhawaTTiku)

---

<div align="center">

*Built with React, FastAPI, pandas, language models and Plotly.*

</div>
