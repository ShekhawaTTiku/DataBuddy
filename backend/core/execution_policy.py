"""Shared basic checks for generated demo code, not an OS security sandbox."""
import ast

ALLOWED_IMPORTS = {
    "pandas", "numpy", "plotly.express", "plotly.graph_objects", "plotly.subplots",
}
_BLOCKED_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "input", "exit", "quit",
    "breakpoint", "getattr", "setattr", "delattr", "globals", "locals", "vars",
    "dir", "help", "memoryview", "os", "sys", "subprocess", "shutil", "pathlib",
    "socket", "http", "urllib", "requests", "ctypes", "importlib", "signal",
    "threading", "multiprocessing", "webbrowser", "pickle", "marshal", "builtins",
}
_BLOCKED_ATTRIBUTES = {
    "eval", "query", "exec", "compile", "open", "getattr", "setattr",
    "load", "loads", "loadtxt", "genfromtxt", "fromfile", "fromregex", "memmap",
    "save", "savez", "savez_compressed", "savetxt", "tofile", "dump", "dumps",
    "to_csv", "to_excel", "to_json", "to_html", "to_pickle", "to_parquet",
    "to_feather", "to_hdf", "to_sql", "to_stata", "to_orc", "to_xml",
    "to_clipboard", "ExcelWriter", "ExcelFile", "HDFStore", "show", "write_html",
    "write_image", "write_json", "read_json", "system", "popen", "get_handle",
    "io", "compat", "util", "core", "testing", "ctypes", "ctypeslib", "lib", "f2py", "distutils",
    "to_latex", "to_markdown", "to_gbq", "to_string", "set_option", "option_context",
}

def check_code(code: str, max_chars: int = 16000) -> str | None:
    if not isinstance(code, str) or not code.strip():
        return "No analysis code was generated. Please try rephrasing the question."
    if len(code) > max_chars:
        return f"Generated code exceeds the {max_chars:,}-character limit."
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError) as exc:
        return f"Invalid generated code: {getattr(exc, 'msg', type(exc).__name__)}."
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in ALLOWED_IMPORTS:
                    return f"Blocked import: '{alias.name}' is not supported."
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module not in ALLOWED_IMPORTS:
                return f"Blocked import: 'from {node.module}' is not supported."
            if any(alias.name == "*" or alias.name.startswith(("_", "read_", "write_"))
                   or alias.name in _BLOCKED_ATTRIBUTES for alias in node.names):
                return "Blocked import: private, wildcard, or I/O imports are not supported."
        elif isinstance(node, ast.Name):
            if node.id.startswith("_") or node.id in _BLOCKED_NAMES:
                return f"Blocked reference: '{node.id}' is not supported."
        elif isinstance(node, ast.Attribute):
            if (node.attr.startswith("_") or node.attr in _BLOCKED_ATTRIBUTES
                    or node.attr.startswith(("read_", "write_"))):
                return f"Blocked operation: '.{node.attr}' is not supported."
        elif isinstance(node, ast.keyword) and node.arg in {"buf", "path_or_buf", "path", "file", "filename", "storage_options"}:
            return f"Blocked file/output argument: '{node.arg}' is not supported."
    return None
