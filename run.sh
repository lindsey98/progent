#!/bin/bash
# Batch runner: no-attack + important_instructions passes over the chosen suites,
# via the unified main.py entry point. Override MODEL / SUITES / DEFENSE / ATTACK
# with env vars, e.g.  MODEL=gpt-4o-2024-08-06 DEFENSE=none ./run.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

MODEL="${MODEL:-Qwen3.6-35B-A3B}"
DEFENSE="${DEFENSE:-progent}"                 # none | progent
ATTACK="${ATTACK:-important_instructions}"
SUITES="${SUITES:-banking slack travel workspace shopping github dailylife}"
EXTRA_ARGS="${EXTRA_ARGS:-}"                  # e.g. --html --force_rerun

# No-attack (utility) pass, then the attacked pass. main.py runs one process per
# suite with the right SECAGENT_* env; the AgentDyn suites get --system-message-name
# agentdyn automatically. Output goes under logs/<model>[+progent]/...
python main.py "$MODEL" --suites $SUITES --defense "$DEFENSE" $EXTRA_ARGS
python main.py "$MODEL" --suites $SUITES --defense "$DEFENSE" --run-attack --attack "$ATTACK" $EXTRA_ARGS

echo "all done"

# Print utility/security for both passes.
python print_results.py --model "$MODEL" --defense "$DEFENSE" --attack "$ATTACK" --log-dir logs --suites $SUITES
