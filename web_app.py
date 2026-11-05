"""Compatibility entry point for the retained Streamlit interface."""
import runpy

runpy.run_module("backend.legacy.web_app", run_name="__main__")
