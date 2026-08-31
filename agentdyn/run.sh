#!/bin/bash
# AgentDyn + Progent. Install first:  cd agentdyn && pip install -e .
# (AgentDyn's package is also named `agentdojo`, so installing it replaces an
#  editable install of ../agentdojo — reinstall whichever benchmark you run.)
# Progent is wired in via AgentDyn's built-in `--defense progent`, which imports
# `secagent` from this repository root automatically.

log_dir="logs"
mkdir -p $log_dir
export COLUMNS=300

# --model takes the ModelsEnum member NAME (click >= 8.2 matches enums by name);
# `model` is the served model id, used for the policy endpoint and log naming.
model_arg="QWEN_3_6_35B_LOCAL"
model="Qwen3.6-35B-A3B"
# model_arg="QWEN_3_30B_LOCAL";  model="Qwen3-30B-A3B-Instruct-2507"
# model_arg="GPT_4O_2024_08_06"; model="gpt-4o-2024-08-06"

# Use the same model for the agent and for Progent's policy generation/update.
export SECAGENT_POLICY_MODEL="$model"
export SECAGENT_UPDATE="True"
export SECAGENT_IGNORE_UPDATE_ERROR="True"

# AgentDyn's dynamic suites. Append banking/slack/travel/workspace to also run
# the original AgentDojo suites from this checkout.
for suite in shopping github dailylife; do
    python -m agentdojo.scripts.benchmark -s $suite --model "$model_arg" --defense progent --logdir $log_dir &
    python -m agentdojo.scripts.benchmark -s $suite --model "$model_arg" --defense progent --attack important_instructions --logdir $log_dir &
done
wait

echo "all done"

# Print utility/security for both the no-attack and important_instructions runs.
python print_results.py --model "$model" --log-dir "$log_dir"
