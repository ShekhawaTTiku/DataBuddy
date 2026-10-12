<div align="center">

# 🤖 DataBuddy

### Ask Questions About Your CSV and Excel Data

*A conversational data analyst that turns plain-language questions into locally executed pandas analysis, then explains the computed results and can suggest visualizations.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Web%20App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![LLM APIs](https://img.shields.io/badge/LLM-Groq%20%7C%20Mistral%20%7C%20Gemini-6C63FF?style=for-the-badge)](#-provider-configuration)

**[Live Demo](https://databuddyy.streamlit.app/) · [Overview](#-overview) · [How It Works](#-how-it-works) · [Setup](#-installation) · [Privacy](#-data-and-privacy)**

</div>

---

<div align="center">

### 🌐 Live Demo

**[Try DataBuddy on Streamlit → databuddyy.streamlit.app](https://databuddyy.streamlit.app/)**

[![Live Demo](https://img.shields.io/badge/Live_Demo-Open_App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://databuddyy.streamlit.app/)

</div>

---

## ✨ Overview

**DataBuddy** lets you explore a local CSV or Excel dataset by asking questions in natural language. It profiles the file, routes each message to analysis or conversation handling, asks an LLM to create pandas code for analysis, runs that code in a bounded local executor, and sends the computed result to an LLM for a plain-language explanation.

The repository includes both a **Streamlit web interface** and a **terminal chat interface**. The web app supports file upload, dataset preview, conversational analysis, and interactive charts. Conversation state and chart context are managed per session in the web UI; the CLI also saves conversation state locally for later runs of the same dataset path.

| 📁 Input | 💬 Questions | 🧮 Analysis | 📊 Output |
|:---:|:---:|:---:|:---:|
| CSV and Excel workbooks | Natural-language questions and follow-ups | Generated pandas code run on the loaded DataFrame | Answers, visualization suggestions, and charts |

---

## 🚀 Features

- 📂 Load a local dataset from the terminal or upload one through Streamlit.
- 📄 Support CSV and Excel formats: `.xlsx`, `.xls`, `.xlsm`, and `.xlsb` (reader engine availability may vary).
- 🔎 Build a compact dataset profile with columns, types, sample values, missing-value counts, and preview rows.
- 🧠 Route analysis questions, ordinary conversation, local-time questions, and “explain the last analysis” requests.
- 🐼 Generate pandas code, execute it locally with checks, a time limit, and result-size limits, then explain the computed result.
- 📈 Suggest and render Plotly charts in the web app when a result supports a visualization.
- 🗂️ Keep conversation context, summarize older turns, and support `/state`, `/reset`, and `/quit` in the CLI.
- 🔁 Use Mistral for routing/chat/explanations, Groq for analysis, and configured fallback or memory providers when enabled.

---

## 🔄 How It Works

```text
Load CSV or Excel file
        │
        ▼
Profile columns, types, missing values, and sample rows
        │
        ▼
Route the user's message
        │
        ├── Conversation / time / explain-last-analysis
        │
        └── Data-analysis question
                  │
                  ▼
          Generate pandas code
                  │
                  ▼
         Run against local DataFrame
         with checks and limits
                  │
                  ▼
     Send compact result for explanation
                  │
                  ▼
       Answer and optional chart suggestion
```

The DataFrame is loaded into the application process, and generated analysis code runs there. Model providers receive prompts and derived context needed for the requested feature; see [Data and Privacy](#-data-and-privacy) before using sensitive data.

---

## ⚙️ Requirements

- Python **3.10 or newer**.
- API keys for the providers used by the configured routing and analysis flow.
- Network access to those provider APIs.
- Enough memory to load the selected dataset into pandas.

Dependencies are listed in `requirements.txt` and include pandas, NumPy, openpyxl, Streamlit, Plotly, and the Groq, Mistral, and Google GenAI clients.

---

## 📦 Installation

### 1. Clone the Repository and Install Dependencies

```bash
git clone https://github.com/ShekhawaTTiku/DataBuddy.git
cd DataBuddy
python -m venv .venv
```

Activate the environment, then install the project requirements:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For Windows PowerShell, activate with:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Configure Provider Keys

Create a private `.env` file for local runs. Keep it out of Git.

```dotenv
GROQ_API_KEY=your-groq-key
MISTRAL_API_KEY=your-mistral-key
GEMINI_API_KEY=your-gemini-key
```

Groq handles pandas-code generation and analysis answers. Mistral routes messages and handles ordinary conversation, analysis explanations, and fallback analysis calls. Gemini is used to fold older CLI conversation turns into a summary. The Gemini key is needed when that memory-summary path is used. Model names and limits can be overridden through environment variables; defaults are defined in `config.py`.

For Streamlit Community Cloud, configure these values in **Settings → Secrets** instead of committing a `.env` file.

---

## ▶️ Usage

### Streamlit Web App

Use the hosted app at **[databuddyy.streamlit.app](https://databuddyy.streamlit.app/)**, or run it locally:

```bash
streamlit run web_app.py
```

Upload a CSV or Excel file (maximum upload size is configured as 50 MB), inspect the detected columns and preview, and ask a question in the chat. For questions with a useful visualization, DataBuddy can render an interactive Plotly chart and provide a suggestion.

### Terminal Chat

Pass a dataset path to the CLI:

```bash
python app.py path/to/data.csv
```

Example:

```bash
python app.py uploads/sales.csv
```

Useful CLI commands:

| Command | Action |
|---|---|
| `/state` | Display the current conversation summary and recent turns. |
| `/reset` | Clear the saved conversation state for the current dataset path. |
| `/quit` | Exit the session; saved state remains on disk. |

Example questions:

- “Which region has the highest total sales?”
- “Show monthly revenue as a line chart.”
- “Filter to 2025 and compare the average order value by category.”
- “How did you calculate the previous result?”

---

## 🧠 Provider Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GROQ_API_KEY` | — | Authenticate analysis-code and final-answer calls. |
| `ANALYSIS_MODEL` | `openai/gpt-oss-120b` | Groq-hosted analysis model. |
| `MISTRAL_API_KEY` | — | Authenticate routing, conversation, explanation, and fallback calls. |
| `MISTRAL_CHAT_MODEL` | `ministral-8b-latest` | Route messages and answer ordinary conversation. |
| `MISTRAL_EXPLANATION_MODEL` | `ministral-14b-latest` | Explain the last successful analysis. |
| `MISTRAL_FALLBACK_MODEL` | `mistral-medium-latest` | Analysis fallback after a recognized Groq rate limit or temporary failure. |
| `GEMINI_API_KEY` | — | Authenticate older-turn summaries when the memory fold runs. |
| `MEMORY_MODEL` | `gemini-3.6-flash` | Model for conversation summaries. |
| `DATABUDDY_TIMEZONE` | `Asia/Kolkata` | Time zone for local clock answers. |
| `DEBUG` | `false` | Print prompts, generated code, and intermediate results. |

Additional execution, sampling, result-size, and conversation settings are documented in `PROJECT_DOCUMENTATION.md` and `config.py`. Model aliases ending in `latest` can change at the provider.

---

## 🧩 Project Structure

```text
DataBuddy/
├── web_app.py                 # Streamlit upload, chat, and chart interface
├── app.py                      # Terminal chat entry point
├── databuddy.py                # Request orchestration
├── dataset_profiler.py         # CSV/Excel loading and dataset profile
├── dataset_state.py            # Dataset state interface
├── message_handler.py          # Message routing and conversation replies
├── analyst.py                  # Analysis code and answer prompts
├── executor.py                 # Checked, time-bounded local execution
├── llm_clients.py              # Provider API clients and retries
├── conversation_state.py       # CLI conversation memory persistence
├── config.py                   # Environment-backed settings
├── prompts/                    # Prompt templates by request type
├── requirements.txt
└── PROJECT_DOCUMENTATION.md    # Detailed architecture and configuration notes
```

---

## 🔐 Data and Privacy

DataBuddy loads the full file into the local application process and does not upload the original dataset file to an LLM provider. However, provider prompts can include dataset-derived information such as column names, sample values, the current question, conversation context, generated pandas code, and compact computed results. Conversation summaries may also include older turns.

Use only data you are permitted to process with the configured providers. Keep `.env` and `.databuddy_state/` private. `DEBUG=true` can print samples, prompts, conversation context, generated code, and results to local logs. The executor includes code checks and time/result limits, but should not be treated as a security boundary for untrusted environments.

---

## ⚠️ Limitations

| Area | Current limitation |
|---|---|
| Dataset size | The complete file is loaded into memory; this is intended for datasets that fit comfortably in RAM. |
| Excel formats | `.xlsx` is supported by the listed openpyxl dependency; other Excel formats may need an additional pandas engine. |
| API availability | Analysis can fall back from recognized temporary Groq errors to Mistral, but all provider calls still depend on API availability, quotas, and model access. |
| Generated code | Static checks and execution limits reduce the allowed behavior but do not make generated code a hardened sandbox. |
| Privacy | Dataset samples, results, prompts, and conversation context may be sent to external LLM providers. |
| Charts | Interactive chart rendering is available in the Streamlit UI; the CLI prints a notice to view charts in the web app. |
| Conversation state | CLI memory is saved locally by dataset path and can contain user-provided facts and analysis details. |

---

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| **Python** | Application, routing, and analysis workflow |
| **pandas / NumPy** | Dataset loading and computation |
| **Streamlit** | Web-based upload and chat interface |
| **Plotly** | Interactive chart rendering |
| **Groq** | Data-analysis code generation and result explanation |
| **Mistral** | Routing, conversation, explanation, and analysis fallback |
| **Google GenAI** | Optional conversation-summary folding |
| **python-dotenv** | Local environment configuration |

---

## 📚 Further Reading

- [Detailed project guide](PROJECT_DOCUMENTATION.md)
- [Original project description](DataBuddy_Project.md)
- [Groq API documentation](https://console.groq.com/docs)
- [Mistral API documentation](https://docs.mistral.ai/)
- [Google GenAI SDK documentation](https://ai.google.dev/gemini-api/docs)

---

## 👤 Maintainer

**Digvijay Singh Shekhawat**

[![GitHub](https://img.shields.io/badge/GitHub-@ShekhawaTTiku-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/ShekhawaTTiku)

---

<div align="center">

*Built with 🐼 pandas, 🤖 language models, and 📊 Streamlit.*

</div><div align="center">

# 🤖 DataBuddy

### Ask Questions About Your CSV and Excel Data

*A conversational data analyst that turns plain-language questions into locally executed pandas analysis, then explains the computed results and can suggest visualizations.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Web%20App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![LLM APIs](https://img.shields.io/badge/LLM-Groq%20%7C%20Mistral%20%7C%20Gemini-6C63FF?style=for-the-badge)](#-provider-configuration)

**[Live Demo](https://databuddyy.streamlit.app/) · [Overview](#-overview) · [How It Works](#-how-it-works) · [Setup](#-installation) · [Privacy](#-data-and-privacy)**

</div>

---

<div align="center">

### 🌐 Live Demo

**[Try DataBuddy on Streamlit → databuddyy.streamlit.app](https://databuddyy.streamlit.app/)**

[![Live Demo](https://img.shields.io/badge/Live_Demo-Open_App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://databuddyy.streamlit.app/)

</div>

---

## ✨ Overview

**DataBuddy** lets you explore a local CSV or Excel dataset by asking questions in natural language. It profiles the file, routes each message to analysis or conversation handling, asks an LLM to create pandas code for analysis, runs that code in a bounded local executor, and sends the computed result to an LLM for a plain-language explanation.

The repository includes both a **Streamlit web interface** and a **terminal chat interface**. The web app supports file upload, dataset preview, conversational analysis, and interactive charts. Conversation state and chart context are managed per session in the web UI; the CLI also saves conversation state locally for later runs of the same dataset path.

| 📁 Input | 💬 Questions | 🧮 Analysis | 📊 Output |
|:---:|:---:|:---:|:---:|
| CSV and Excel workbooks | Natural-language questions and follow-ups | Generated pandas code run on the loaded DataFrame | Answers, visualization suggestions, and charts |

---

## 🚀 Features

- 📂 Load a local dataset from the terminal or upload one through Streamlit.
- 📄 Support CSV and Excel formats: `.xlsx`, `.xls`, `.xlsm`, and `.xlsb` (reader engine availability may vary).
- 🔎 Build a compact dataset profile with columns, types, sample values, missing-value counts, and preview rows.
- 🧠 Route analysis questions, ordinary conversation, local-time questions, and “explain the last analysis” requests.
- 🐼 Generate pandas code, execute it locally with checks, a time limit, and result-size limits, then explain the computed result.
- 📈 Suggest and render Plotly charts in the web app when a result supports a visualization.
- 🗂️ Keep conversation context, summarize older turns, and support `/state`, `/reset`, and `/quit` in the CLI.
- 🔁 Use Mistral for routing/chat/explanations, Groq for analysis, and configured fallback or memory providers when enabled.

---

## 🔄 How It Works

```text
Load CSV or Excel file
        │
        ▼
Profile columns, types, missing values, and sample rows
        │
        ▼
Route the user's message
        │
        ├── Conversation / time / explain-last-analysis
        │
        └── Data-analysis question
                  │
                  ▼
          Generate pandas code
                  │
                  ▼
         Run against local DataFrame
         with checks and limits
                  │
                  ▼
     Send compact result for explanation
                  │
                  ▼
       Answer and optional chart suggestion
```

The DataFrame is loaded into the application process, and generated analysis code runs there. Model providers receive prompts and derived context needed for the requested feature; see [Data and Privacy](#-data-and-privacy) before using sensitive data.

---

## ⚙️ Requirements

- Python **3.10 or newer**.
- API keys for the providers used by the configured routing and analysis flow.
- Network access to those provider APIs.
- Enough memory to load the selected dataset into pandas.

Dependencies are listed in `requirements.txt` and include pandas, NumPy, openpyxl, Streamlit, Plotly, and the Groq, Mistral, and Google GenAI clients.

---

## 📦 Installation

### 1. Clone the Repository and Install Dependencies

```bash
git clone https://github.com/ShekhawaTTiku/DataBuddy.git
cd DataBuddy
python -m venv .venv
```

Activate the environment, then install the project requirements:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For Windows PowerShell, activate with:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Configure Provider Keys

Create a private `.env` file for local runs. Keep it out of Git.

```dotenv
GROQ_API_KEY=your-groq-key
MISTRAL_API_KEY=your-mistral-key
GEMINI_API_KEY=your-gemini-key
```

Groq handles pandas-code generation and analysis answers. Mistral routes messages and handles ordinary conversation, analysis explanations, and fallback analysis calls. Gemini is used to fold older CLI conversation turns into a summary. The Gemini key is needed when that memory-summary path is used. Model names and limits can be overridden through environment variables; defaults are defined in `config.py`.

For Streamlit Community Cloud, configure these values in **Settings → Secrets** instead of committing a `.env` file.

---

## ▶️ Usage

### Streamlit Web App

Use the hosted app at **[databuddyy.streamlit.app](https://databuddyy.streamlit.app/)**, or run it locally:

```bash
streamlit run web_app.py
```

Upload a CSV or Excel file (maximum upload size is configured as 50 MB), inspect the detected columns and preview, and ask a question in the chat. For questions with a useful visualization, DataBuddy can render an interactive Plotly chart and provide a suggestion.

### Terminal Chat

Pass a dataset path to the CLI:

```bash
python app.py path/to/data.csv
```

Example:

```bash
python app.py uploads/sales.csv
```

Useful CLI commands:

| Command | Action |
|---|---|
| `/state` | Display the current conversation summary and recent turns. |
| `/reset` | Clear the saved conversation state for the current dataset path. |
| `/quit` | Exit the session; saved state remains on disk. |

Example questions:

- “Which region has the highest total sales?”
- “Show monthly revenue as a line chart.”
- “Filter to 2025 and compare the average order value by category.”
- “How did you calculate the previous result?”

---

## 🧠 Provider Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GROQ_API_KEY` | — | Authenticate analysis-code and final-answer calls. |
| `ANALYSIS_MODEL` | `openai/gpt-oss-120b` | Groq-hosted analysis model. |
| `MISTRAL_API_KEY` | — | Authenticate routing, conversation, explanation, and fallback calls. |
| `MISTRAL_CHAT_MODEL` | `ministral-8b-latest` | Route messages and answer ordinary conversation. |
| `MISTRAL_EXPLANATION_MODEL` | `ministral-14b-latest` | Explain the last successful analysis. |
| `MISTRAL_FALLBACK_MODEL` | `mistral-medium-latest` | Analysis fallback after a recognized Groq rate limit or temporary failure. |
| `GEMINI_API_KEY` | — | Authenticate older-turn summaries when the memory fold runs. |
| `MEMORY_MODEL` | `gemini-3.6-flash` | Model for conversation summaries. |
| `DATABUDDY_TIMEZONE` | `Asia/Kolkata` | Time zone for local clock answers. |
| `DEBUG` | `false` | Print prompts, generated code, and intermediate results. |

Additional execution, sampling, result-size, and conversation settings are documented in `PROJECT_DOCUMENTATION.md` and `config.py`. Model aliases ending in `latest` can change at the provider.

---

## 🧩 Project Structure

```text
DataBuddy/
├── web_app.py                 # Streamlit upload, chat, and chart interface
├── app.py                      # Terminal chat entry point
├── databuddy.py                # Request orchestration
├── dataset_profiler.py         # CSV/Excel loading and dataset profile
├── dataset_state.py            # Dataset state interface
├── message_handler.py          # Message routing and conversation replies
├── analyst.py                  # Analysis code and answer prompts
├── executor.py                 # Checked, time-bounded local execution
├── llm_clients.py              # Provider API clients and retries
├── conversation_state.py       # CLI conversation memory persistence
├── config.py                   # Environment-backed settings
├── prompts/                    # Prompt templates by request type
├── requirements.txt
└── PROJECT_DOCUMENTATION.md    # Detailed architecture and configuration notes
```

---

## 🔐 Data and Privacy

DataBuddy loads the full file into the local application process and does not upload the original dataset file to an LLM provider. However, provider prompts can include dataset-derived information such as column names, sample values, the current question, conversation context, generated pandas code, and compact computed results. Conversation summaries may also include older turns.

Use only data you are permitted to process with the configured providers. Keep `.env` and `.databuddy_state/` private. `DEBUG=true` can print samples, prompts, conversation context, generated code, and results to local logs. The executor includes code checks and time/result limits, but should not be treated as a security boundary for untrusted environments.

---

## ⚠️ Limitations

| Area | Current limitation |
|---|---|
| Dataset size | The complete file is loaded into memory; this is intended for datasets that fit comfortably in RAM. |
| Excel formats | `.xlsx` is supported by the listed openpyxl dependency; other Excel formats may need an additional pandas engine. |
| API availability | Analysis can fall back from recognized temporary Groq errors to Mistral, but all provider calls still depend on API availability, quotas, and model access. |
| Generated code | Static checks and execution limits reduce the allowed behavior but do not make generated code a hardened sandbox. |
| Privacy | Dataset samples, results, prompts, and conversation context may be sent to external LLM providers. |
| Charts | Interactive chart rendering is available in the Streamlit UI; the CLI prints a notice to view charts in the web app. |
| Conversation state | CLI memory is saved locally by dataset path and can contain user-provided facts and analysis details. |

---

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| **Python** | Application, routing, and analysis workflow |
| **pandas / NumPy** | Dataset loading and computation |
| **Streamlit** | Web-based upload and chat interface |
| **Plotly** | Interactive chart rendering |
| **Groq** | Data-analysis code generation and result explanation |
| **Mistral** | Routing, conversation, explanation, and analysis fallback |
| **Google GenAI** | Optional conversation-summary folding |
| **python-dotenv** | Local environment configuration |

---

## 📚 Further Reading

- [Detailed project guide](PROJECT_DOCUMENTATION.md)
- [Original project description](DataBuddy_Project.md)
- [Groq API documentation](https://console.groq.com/docs)
- [Mistral API documentation](https://docs.mistral.ai/)
- [Google GenAI SDK documentation](https://ai.google.dev/gemini-api/docs)

---

## 👤 Maintainer

**Digvijay Singh Shekhawat**

[![GitHub](https://img.shields.io/badge/GitHub-@ShekhawaTTiku-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/ShekhawaTTiku)

---

<div align="center">

*Built with 🐼 pandas, 🤖 language models, and 📊 Streamlit.*

</div>
