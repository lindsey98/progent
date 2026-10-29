"""Auto-imported at interpreter startup (Python's `site` imports `sitecustomize` from sys.path).

progent/main.py runs the real benchmark in a SUBPROCESS (`python -m agentdojo.scripts.benchmark ...`) with
the repo root on PYTHONPATH, so this file is imported there and installs per-record token accounting into
that subprocess -- the agent turns and Progent's policy-LLM calls all get counted and written into each
record's prompt_tokens/completion_tokens/total_tokens (Progent logs none otherwise). See token_meter.py.

Installing from main.py would NOT reach the subprocess, which is why this lives in sitecustomize.
"""

try:
    import token_meter

    token_meter.install()
except Exception:  # noqa: BLE001 -- never let accounting break interpreter startup
    pass
