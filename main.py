#!/usr/bin/env python
"""Unified entry point for the AgentDojo + Progent benchmark.

    # attacked run
    python main.py MODEL --run-attack --attack important_instructions \
        --suite banking slack travel workspace --defense progent

    # no-attack (utility) run
    python main.py MODEL --suite banking slack travel workspace --defense progent

MODEL is the served model id (positional; a ModelsEnum value like `Qwen3.6-35B-A3B`
or its enum name). `--defense` is `none` (baseline) or `progent` (passed to the
benchmark as `--defense progent`). Output goes under `logs/`. This script launches
one `agentdojo.scripts.benchmark` subprocess per suite and forwards the flags.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# AgentDyn's dynamic suites need AgentDyn's system message (adds the
# "act without asking for confirmation" line). Applied automatically unless the
# user passes --system-message-name.
AGENTDYN_SUITES = {"shopping", "github", "dailylife"}


def _resolve_model_name(model: str) -> str:
    """Map a model id to the token the benchmark's --model expects.

    agentdojo's --model is a click.Choice over ModelsEnum, matched by enum *name*
    (e.g. QWEN_3_6_35B_LOCAL), while users usually pass the value (Qwen3.6-35B-A3B).
    Accept either: pass an enum name through, else map a value to its unique name.
    Unknown ids pass through so the benchmark reports the error itself.
    """
    try:
        from agentdojo.models import ModelsEnum
    except Exception:
        return model
    members = ModelsEnum.__members__
    if model in members:
        return model
    by_value = [name for name, m in members.items() if str(m.value) == model]
    if len(by_value) == 1:
        return by_value[0]
    if len(by_value) > 1:
        print(f"[main] warning: {model!r} maps to several models {by_value}; using {by_value[0]}. "
              f"Pass the enum name to disambiguate.", file=sys.stderr)
        return by_value[0]
    return model


def main() -> int:
    p = argparse.ArgumentParser(
        prog="main.py",
        description="Run the AgentDojo + Progent benchmark (one subprocess per suite).",
    )
    p.add_argument("model", help="Served model id, e.g. Qwen3.6-35B-A3B or gpt-4o-2024-08-06.")
    p.add_argument("--suite", dest="suites", nargs="+", required=True, metavar="SUITE",
                   help="Suite(s) to run, space-separated (e.g. banking slack travel workspace).")
    p.add_argument("--defense", choices=["none", "progent"], default="none",
                   help="none = plain baseline; progent = Progent privilege control. Default none.")
    p.add_argument("--run-attack", action="store_true",
                   help="Run the attack pass. Without it, the no-attack (utility) pass is run.")
    p.add_argument("--attack", default="important_instructions",
                   help="Attack name used when --run-attack is set. Default important_instructions.")
    # Optional, unchanged:
    p.add_argument("--force_rerun", action="store_true",
                   help="Re-run tasks even if their trace already exists (default: resume).")
    p.add_argument("--html", action="store_true",
                   help="Also save a rendered <task>.html next to each <task>.json.")
    p.add_argument("--user-task", "-ut", dest="user_tasks", nargs="+", default=[], metavar="ID",
                   help="Restrict to these user task ids (only when a single suite is given).")
    p.add_argument("--injection-task", "-it", dest="injection_tasks", nargs="+", default=[], metavar="ID",
                   help="Restrict to these injection task ids (only when a single suite is given).")
    p.add_argument("--logdir", default="logs", help="Output directory. Default logs/.")
    p.add_argument("--system-message-name", default=None,
                   help="System message name (default: 'agentdyn' for shopping/github/dailylife).")
    p.add_argument("--max-workers", type=int, default=0,
                   help="Parallel suites. 0 (default) = all at once; 1 = sequential.")
    args = p.parse_args()

    if (args.user_tasks or args.injection_tasks) and len(args.suites) != 1:
        p.error("--user-task/--injection-task can only be used with a single --suite value.")

    # This script lives at the progent repo root, next to the `secagent` package.
    repo_root = Path(__file__).resolve().parent
    run_cwd = repo_root
    model_name = _resolve_model_name(args.model)

    # Base env: put the repo root on PYTHONPATH so `import secagent` resolves, and
    # set Progent's policy settings (secagent reads these). SECAGENT_POLICY_MODEL is
    # the served model *value*, i.e. what secagent sends to the policy LLM.
    base_env = dict(os.environ)
    base_env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{base_env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    base_env["COLUMNS"] = base_env.get("COLUMNS", "300")
    if args.defense == "progent":
        base_env["SECAGENT_GENERATE"] = "True"
        base_env["SECAGENT_POLICY_MODEL"] = args.model
        base_env.setdefault("SECAGENT_UPDATE", "True")
        base_env.setdefault("SECAGENT_IGNORE_UPDATE_ERROR", "True")

    if args.html:
        base_env["AGENTDOJO_SAVE_HTML"] = "1"

    # The benchmark's --defense is a Choice over the defense list (no "none"); omit
    # it for the baseline. Progent is `--defense progent`.
    common = ["--model", model_name, "--logdir", args.logdir]
    if args.defense == "progent":
        common += ["--defense", "progent"]
    if args.run_attack:
        common += ["--attack", args.attack]
    if args.force_rerun:
        common += ["--force-rerun"]
    if args.html:
        common += ["--html"]
    for ut in args.user_tasks:
        common += ["-ut", ut]
    for it in args.injection_tasks:
        common += ["-it", it]

    procs: list[tuple[str, subprocess.Popen]] = []
    rc = 0
    for suite in args.suites:
        env = dict(base_env)
        cmd = [sys.executable, "-m", "agentdojo.scripts.benchmark", "-s", suite, *common]
        sysmsg = args.system_message_name or ("agentdyn" if suite in AGENTDYN_SUITES else None)
        if sysmsg:
            cmd += ["--system-message-name", sysmsg]

        pass_label = f"attack={args.attack}" if args.run_attack else "no-attack"
        print(f"[main] launch: suite={suite} defense={args.defense} {pass_label}", flush=True)
        print("       " + " ".join(cmd), flush=True)

        if args.max_workers == 1:
            rc |= subprocess.run(cmd, env=env, cwd=run_cwd).returncode
        else:
            procs.append((suite, subprocess.Popen(cmd, env=env, cwd=run_cwd)))

    for suite, proc in procs:
        code = proc.wait()
        if code != 0:
            print(f"[main] suite {suite} exited with code {code}", file=sys.stderr)
            rc |= code

    print("[main] all done")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
