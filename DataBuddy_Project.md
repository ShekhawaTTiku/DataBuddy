# DataBuddy — Project Description

## 1. What this is

DataBuddy is a command-line tool that lets a user ask natural-language questions about a CSV or Excel file and get back real, computed answers — without writing any Python or SQL themselves.

The user loads a dataset once. Then, for each question, DataBuddy:

1. Describes the dataset to an LLM (Groq) as a compact text profile — never the raw data.
2. Asks Groq to write the pandas code needed to answer the question.
3. Runs that code locally, safely, against the real DataFrame.
4. Sends the actual result back to Groq, which turns it into a plain-language answer.

Each question is handled independently — there is no memory of earlier questions and no second LLM. This project is exactly that pipeline, done well.

### Example interaction

```
$ python app.py uploads/sales.csv
Loaded sales.csv — 15,000 rows, 8 columns.

> Which product generated the highest revenue?
Laptop generated the highest total revenue, ₹452,000, by summing revenue per product.

> What's the average discount given?
The average discount across all 15,000 orders is 4.8%.

> /quit
```

## 2. Why the LLM never computes the answer directly

If the LLM were asked "what's the average revenue?" directly, it would have to guess or hallucinate a number — it never sees the actual data. DataBuddy avoids this by splitting the work in two:

- **Groq's job:** understand the question and the dataset's shape, and write correct pandas code.
- **Python's job:** actually run that code against the real data and produce the real number.

Groq never sees more than a few sample rows, and it never executes anything itself. This keeps answers grounded in real computation, keeps the raw dataset local, and keeps every prompt small regardless of dataset size — a 500,000-row file and a 500-row file produce the same size profile.

## 3. Pipeline, in detail

```
CSV/Excel file
   │
   ▼
dataset_profiler.py         builds a compact text profile:
                             columns, dtypes, row count, missing
                             values, basic stats, a few sample rows
   │
   ▼
analyst.generate_code()     Groq call 1: profile + question → pandas code
   │
   ▼
executor.py                 validates the code, runs it on a COPY
                             of the DataFrame inside a timeout,
                             captures the value of `result`
   │
   ├── failed? ──► generate_code() is called again with the error
   │                attached (up to a fixed retry limit), then
   │                re-executed
   │
   ▼
analyst.write_answer()      Groq call 2: question + code + actual
                             result → natural-language answer
   │
   ▼
printed to the user
```

### Worked example

Question: *"Which product generated the highest revenue?"*

Groq (call 1) generates:
```python
result = (
    df.groupby("product")["revenue"]
    .sum()
    .sort_values(ascending=False)
    .head(1)
)
```

The executor runs this on the real DataFrame and gets:
```
product
Laptop    452000
Name: revenue, dtype: int64
```

That gets turned into compact text (`"Laptop: 452000"`) and sent to Groq (call 2), which replies:

> "Laptop generated the highest total revenue, ₹452,000, calculated by summing revenue for each product."

## 4. What is included

- Loading and profiling CSV and Excel files.
- One Groq call to turn a question into pandas code.
- Safe local execution of that code, with a bounded number of retries if it fails.
- One Groq call to turn the actual result into a natural-language answer.
- A terminal loop for asking questions one at a time.
- Basic execution safety: a restricted set of allowed operations, a timeout, and truncation of oversized results.

## 5. What is not included

- Remembering earlier questions, or answering follow-ups like "what about the second one?" or "why?" — every question is handled from scratch.
- Any LLM other than Groq.
- Charts, plots, or a graphical/web interface.
- Sandboxing beyond the basic safeguards in Section 9 — this is a local, single-user tool, not something exposed to other people.

## 6. Project structure

```
DataBuddy/
├── app.py                # entry point — the terminal loop
├── config.py             # settings and constants
├── llm_client.py         # the only file that talks to Groq
├── dataset_profiler.py   # loads a file and builds its text profile
├── analyst.py            # the two Groq steps: code generation, final answer
├── executor.py           # safely runs generated code
├── prompts/
│   ├── code_generation.txt
│   └── final_response.txt
├── uploads/               # sample datasets (git-ignored)
├── tests/                 # tests for executor.py and dataset_profiler.py
├── .env                   # GROQ_API_KEY (git-ignored)
├── .gitignore
└── requirements.txt
```

## 7. `config.py`

Loads `GROQ_API_KEY` from `.env` via `python-dotenv`, and defines the tunable constants:

| Constant | Purpose | Suggested default |
|---|---|---|
| `MODEL_NAME` | Groq model to use | a current Groq-hosted model |
| `MAX_CODE_RETRIES` | max correction attempts after a failed execution | 2 |
| `EXEC_TIMEOUT_SECONDS` | hard timeout for running generated code | 5 |
| `SAMPLE_ROWS` | sample rows included in the profile | 3 |
| `MAX_RESULT_ROWS` | rows of a Series/DataFrame result sent back to the LLM | 20 |
| `MAX_RESULT_CHARS` | hard cap on the size of the result text | 2000 |
| `DEBUG` | if true, print the prompts, generated code, and raw result at each step | `False` |

No other file should hard-code a constant that belongs here.

## 8. `dataset_profiler.py`

**Job:** turn a file into (a) an in-memory DataFrame and (b) a compact text description of it.

Suggested interface:
```python
class DatasetProfile:
    filename: str
    df: pd.DataFrame
    text: str            # the compact profile sent to the LLM

def load_and_profile(path: str) -> DatasetProfile: ...
```

The profile text should include:
- filename, row count, column count
- each column's name and dtype
- missing-value counts per column
- for numeric columns: min, max, mean
- for low-cardinality text columns (e.g. under ~15 unique values): the actual values
- for date columns: the min and max date
- up to `SAMPLE_ROWS` example rows, rendered compactly

Example profile text:
```
Dataset: sales.csv
Rows: 15000, Columns: 8

Columns:
- product (string) — 12 unique values: Laptop, Phone, Tablet, ...
- quantity (int)
- price (float) — min 9.99, max 2499.00, mean 341.25
- date (datetime) — range 2023-01-01 to 2024-12-31
- region (string) — 4 unique values: East, West, North, South
- revenue (float) — min 9.99, max 12500.00, mean 615.80
- discount (float) — 23 missing values
- customer_id (string)

Sample rows:
product=Laptop, quantity=1, price=899.0, region=East, revenue=899.0, date=2024-03-14
...
```

Correctness here matters most: if a column type or name is wrong in the profile, every downstream answer is affected.

## 9. `executor.py`

**Job:** run LLM-generated code without trusting it.

Suggested interface:
```python
@dataclass
class ExecutionResult:
    ok: bool
    result_text: str | None
    error: str | None

def run_code(code: str, df: pd.DataFrame) -> ExecutionResult: ...
```

Safety measures, applied in this order:

1. **Static check before running.** Parse the code with `ast` and reject it if it contains: imports outside `pandas`/`numpy`, `open`, `exec`, `eval`, `compile`, `__import__`, dunder attribute access, or any OS/network/subprocess reference.
2. **Restricted execution namespace.** Only `df` (a `.copy()` of the real DataFrame), `pd`, and `np` are available; builtins are limited to a safe subset (no `open`, `input`, `__import__`, etc.).
3. **Hard timeout.** Run the code in a separate process (`multiprocessing`) so it can be killed if it runs past `EXEC_TIMEOUT_SECONDS` — a plain in-process timeout cannot stop CPU-bound pandas code.
4. **Result extraction.** The answer must be in a variable named `result`. Convert it to compact text: round floats, cap a Series/DataFrame at `MAX_RESULT_ROWS` rows, and cap the whole string at `MAX_RESULT_CHARS`.
5. **Error capture.** On any exception, return `ok=False` with the exception type and message (not a full traceback) as `error`.

`result = None` is a valid, successful outcome — it means no computation was needed (e.g. the question can't be answered from this dataset).

## 10. `llm_client.py`

**Job:** the single point of contact with Groq.

```python
def call_llm(prompt: str, temperature: float = 0.2) -> str: ...
```

- Wraps the Groq SDK call using `config.MODEL_NAME` and `config.GROQ_API_KEY`.
- Retries a small, fixed number of times on transient errors (rate limits, timeouts, 5xx) with a short backoff, then raises a clear exception.
- Knows nothing about datasets, prompts' meaning, or code — it only sends text and returns text.

## 11. `analyst.py`

**Job:** build the two prompts and call `llm_client.call_llm()`.

```python
def generate_code(profile: str, question: str, previous_attempt: dict | None = None) -> str: ...
def write_answer(profile: str, question: str, code: str, execution: ExecutionResult) -> str: ...
```

`previous_attempt`, when present, holds the failed `code` and its `error`, so a retry can be included in the prompt.

Both functions load their template from `prompts/`, replace placeholders with `str.replace` (not `str.format` — the templates contain code and braces), call the LLM, and (for `generate_code`) strip markdown code fences from the reply before returning it.

### `prompts/code_generation.txt`

```
You are DataBuddy's data-analysis code generator.

A pandas DataFrame named `df` is already loaded. `pd` and `np` are already imported.

DATASET:
{{profile}}

PREVIOUS ATTEMPT (empty unless the last attempt failed):
{{previous_attempt}}

QUESTION:
{{question}}

RULES:
- Use exactly the column names shown above.
- Store the final answer in a variable named `result` — a number, string, Series, or small DataFrame. Return aggregates or top-N rows, never the whole dataset.
- Do not modify `df` in place. Do not read or write files. Do not access the network. Do not create plots.
- If the question needs no computation, set `result = None`.
- If the question cannot be answered from this dataset, set `result` to a one-sentence explanation why.
- Never fabricate numbers.

Return only the Python code in a single code block, with no explanation.
```

### `prompts/final_response.txt`

```
You are DataBuddy, explaining a data analysis result to a non-technical user.

QUESTION:
{{question}}

CODE THAT WAS RUN:
{{code}}

EXECUTION STATUS: {{execution_status}}
RESULT:
{{result}}

Explain the result in one or two plain-language sentences.
Use only the numbers shown above — never invent or estimate a number.
Briefly mention what was computed (e.g. the metric and how it was grouped or filtered).
If execution failed, say so honestly and suggest how the question could be rephrased — do not guess an answer.
```

## 12. `app.py`

The user-facing loop:

```
python app.py uploads/sales.csv
```

- Loads and profiles the file once via `dataset_profiler.load_and_profile()`.
- Prints a one-line dataset summary.
- Loops: read a question from the terminal → run the pipeline (`analyst.generate_code` → `executor.run_code`, retrying on failure up to `MAX_CODE_RETRIES` → `analyst.write_answer`) → print the answer.
- `/quit` exits. If `config.DEBUG` is true, prints the prompt sent, the code generated, and the raw execution result at each step — useful while developing.

This file contains no analysis or LLM logic itself; it only calls the other modules in order.

## 13. Error-handling flow

```
generate_code()
     │
     ▼
run_code() ──ok──► write_answer() ──► done
     │
    fail
     │
     ▼
attempts used < MAX_CODE_RETRIES?
     │                     │
    yes                    no
     │                     │
     ▼                     ▼
generate_code()      write_answer() is still called,
(with error attached)  with the failure passed in, so
     │                 the user gets an honest message
     ▼
run_code() again
```

## 14. Testing

`tests/` should cover the two modules that need no API key:

- **`executor.py`:** feed it hand-written code strings — a correct one, one with a `KeyError`, one that imports `os`, one with an infinite loop — and check the result matches expectations for each.
- **`dataset_profiler.py`:** run it against a small fixed CSV and check the profile text contains the right row count, column names, and missing-value counts.

Testing `analyst.py` and `llm_client.py` requires a real Groq call, so those are checked manually while building, by turning on `DEBUG` and inspecting the output for a handful of representative questions (average, top-N, group-by, a date filter, a question about missing values, and one about a column that doesn't exist).

## 15. Environment and dependencies

`.env`:
```
GROQ_API_KEY=...
```

`requirements.txt`:
```
pandas
numpy
openpyxl
python-dotenv
groq
```

`.gitignore` must include `.env` and `uploads/`.

## 16. Build order

Each step should be working and tested before moving to the next.

1. `config.py`, `.env`, `requirements.txt`.
2. `dataset_profiler.py` — verify by printing the profile for a sample CSV and an Excel file.
3. `llm_client.py` — verify with one hello-world call.
4. `executor.py` — verify with hand-written code strings, no LLM involved yet.
5. `prompts/code_generation.txt` + `analyst.generate_code()` — inspect the code Groq produces for a few questions.
6. `prompts/final_response.txt` + `analyst.write_answer()`.
7. `app.py` — wire everything into the terminal loop, including the retry logic.

## 17. Acceptance criteria

- Answers to at least five varied questions (average, top-N, group-by, a date filter, and a missing-values question) match a manual pandas calculation.
- A question about a column that doesn't exist gets an honest answer, not a crash or an invented number.
- Code that imports a disallowed module, opens a file, or loops forever is caught — rejected outright or stopped by the timeout — and never silently runs.
- With `DEBUG` on, the printed prompts confirm that only the profile, the question, the code, and the truncated result ever reach Groq — never the raw dataset.
- The profile stays a similar size whether the file has 500 rows or 500,000.

## 18. How to work through this

Build one file at a time, in the order in Section 16. Explain each new concept briefly before writing its code, and get each piece working before moving on to the next — don't jump ahead.
