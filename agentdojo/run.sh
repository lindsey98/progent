#!/bin/bash
export PYTHONPATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd):$PYTHONPATH"

log_dir="logs"
mkdir -p $log_dir
export COLUMNS=300

#model="Qwen3-30B-A3B-Instruct-2507"
 model="Qwen3.6-35B-A3B"
# model="gpt-4o-2024-08-06"
# model="meta-llama/Llama-3.3-70B-Instruct"

export SECAGENT_POLICY_MODEL="$model"

# Progent privilege control (SECAGENT_GENERATE) is ON by default -> logs go to
# logs/<model>+progent/... Set SECAGENT_GENERATE=False for a plain baseline.
# Policy auto-update must be enabled explicitly: the benchmark's update gate
# (agent_pipeline/tool_execution.py) defaults to off.
export SECAGENT_UPDATE="True"
export SECAGENT_IGNORE_UPDATE_ERROR="True"

# AgentDojo suites (default). For the AgentDyn dynamic suites use:
#   suites="shopping github dailylife"; extra_args="--system-message-name agentdyn"
suites="${SUITES:-banking slack travel workspace shopping github dailylife}"
extra_args="${EXTRA_ARGS:-}"

for suite in $suites; do
    SECAGENT_SUITE=$suite python -m agentdojo.scripts.benchmark -s $suite --model "$model" $extra_args --logdir $log_dir &
    SECAGENT_SUITE=$suite python -m agentdojo.scripts.benchmark -s $suite --model "$model" $extra_args --attack important_instructions --logdir $log_dir &
done
wait

echo "all done"

# Print utility/security for both the no-attack and important_instructions runs.
python print_results.py --model "$model" --log-dir "$log_dir" --suites $suites
