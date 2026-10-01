import re
from pathlib import Path

import config
from llm_clients import call_analysis_llm
from executor import ExecutionResult

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_template(filename: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from the LLM reply, if present."""
    text = text.strip()
    # Match ```python ... ``` or ``` ... ```
    match = re.search(r"```(?:\w*)\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def generate_code(profile: str, question: str, previous_attempt: dict | None = None,
                  conversation_text: str = "None yet.") -> str:
    """Ask the LLM to generate pandas code that answers the user's question.

    Args:
        profile: The compact text profile of the dataset.
        question: The user's natural-language question.
        previous_attempt: If provided, a dict with keys 'code' and 'error'
                          from the previous failed attempt.

    Returns:
        The generated Python code as a string.
    """
    template = _load_template("code_generation.txt")

    if previous_attempt is not None:
        prev_text = (
            f"Code:\n{previous_attempt['code']}\n\n"
            f"Error:\n{previous_attempt['error']}"
        )
    else:
        prev_text = ""

    prompt = template.replace("{{profile}}", profile)
    prompt = prompt.replace("{{conversation}}", conversation_text)
    prompt = prompt.replace("{{previous_attempt}}", prev_text)
    prompt = prompt.replace("{{question}}", question)

    if config.DEBUG:
        print(f"\n[DEBUG] Code-generation prompt:\n{prompt}")
    response = call_analysis_llm(prompt)
    return _strip_code_fences(response)


def generate_chart_code(profile: str, question: str,
                        previous_attempt: dict | None = None,
                        conversation_text: str = "None yet.",
                        chart_context: str = "None yet.") -> str:
    """Ask the LLM to generate Plotly chart code.

    Args:
        profile: The compact text profile of the dataset.
        question: The user's natural-language question.
        previous_attempt: If provided, a dict with keys 'code' and 'error'
                          from the previous failed attempt.
        conversation_text: Recent analysis context.
        chart_context: Previous chart context for follow-up modifications.

    Returns:
        The generated Python code as a string.
    """
    template = _load_template("chart_generation.txt")

    if previous_attempt is not None:
        prev_text = (
            f"Code:\n{previous_attempt['code']}\n\n"
            f"Error:\n{previous_attempt['error']}"
        )
    else:
        prev_text = ""

    prompt = template.replace("{{profile}}", profile)
    prompt = prompt.replace("{{conversation}}", conversation_text)
    prompt = prompt.replace("{{chart_context}}", chart_context)
    prompt = prompt.replace("{{previous_attempt}}", prev_text)
    prompt = prompt.replace("{{question}}", question)

    if config.DEBUG:
        print(f"\n[DEBUG] Chart-generation prompt:\n{prompt}")
    response = call_analysis_llm(prompt)
    return _strip_code_fences(response)


def write_answer(profile: str, question: str, code: str, execution: ExecutionResult,
                 conversation_text: str = "None yet.") -> str:
    """Ask the LLM to explain the execution result in plain language.

    Args:
        profile: The compact text profile of the dataset.
        question: The user's natural-language question.
        code: The generated pandas code that was executed.
        execution: The ExecutionResult from executor.run_code().

    Returns:
        A plain-language answer as a string.
    """
    template = _load_template("final_response.txt")

    execution_status = "Success" if execution.ok else "Failed"
    result_text = execution.result_text if execution.result_text is not None else ""
    if not execution.ok and execution.error:
        result_text = execution.error

    prompt = template.replace("{{question}}", question)
    prompt = prompt.replace("{{profile}}", profile)
    prompt = prompt.replace("{{conversation}}", conversation_text)
    prompt = prompt.replace("{{code}}", code)
    prompt = prompt.replace("{{execution_status}}", execution_status)
    prompt = prompt.replace("{{result}}", result_text)

    if config.DEBUG:
        print(f"\n[DEBUG] Final-response prompt:\n{prompt}")
    return call_analysis_llm(prompt)


def write_chart_insight(profile: str, question: str, code: str,
                        execution: ExecutionResult) -> str:
    """Generate a brief narrative insight to accompany a chart.

    Args:
        profile: The compact text profile of the dataset.
        question: The user's natural-language question.
        code: The chart generation code that was executed.
        execution: The ExecutionResult with chart data.

    Returns:
        A brief narrative insight as a string.
    """
    template = _load_template("chart_insight.txt")

    chart_description = execution.chart_description or "Chart"
    result_text = execution.result_text if execution.result_text is not None else "N/A"

    prompt = template.replace("{{question}}", question)
    prompt = prompt.replace("{{profile}}", profile)
    prompt = prompt.replace("{{chart_description}}", chart_description)
    prompt = prompt.replace("{{code}}", code)
    prompt = prompt.replace("{{result}}", result_text)

    if config.DEBUG:
        print(f"\n[DEBUG] Chart-insight prompt:\n{prompt}")
    return call_analysis_llm(prompt)


def suggest_visualization(question: str, result_text: str,
                          columns: list[str]) -> str | None:
    """Suggest a follow-up visualization after a text-only analysis.

    Args:
        question: The user's original question.
        result_text: The analysis result text.
        columns: List of dataset column names.

    Returns:
        A suggestion string, or None if no suggestion is appropriate.
    """
    template = _load_template("chart_suggestion.txt")

    prompt = template.replace("{{question}}", question)
    prompt = prompt.replace("{{result}}", result_text or "")
    prompt = prompt.replace("{{columns}}", ", ".join(columns))

    if config.DEBUG:
        print(f"\n[DEBUG] Chart-suggestion prompt:\n{prompt}")
    try:
        response = call_analysis_llm(prompt)
        response = response.strip()
        if response == "NO_SUGGESTION" or not response:
            return None
        return response
    except Exception:
        return None

