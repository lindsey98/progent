#!/bin/bash
# Install first:  cd agentdojo && pip install -e .   (and  pip install -r ../requirements.txt)
# This script adds the repo root to PYTHONPATH so `import secagent` resolves to it.
export PYTHONPATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd):$PYTHONPATH"

log_dir="logs"
mkdir -p $log_dir
export COLUMNS=300

# Agent model. For a locally served model, start it first, e.g.:
#   vllm serve Qwen/Qwen3-30B-A3B-Instruct-2507 --port 8000
# (set LOCAL_MODEL_BASE_URL / SECAGENT_POLICY_BASE_URL if not on localhost:8000)
model="Qwen/Qwen3-30B-A3B-Instruct-2507"
# model="gpt-4o-2024-08-06"
# model="meta-llama/Llama-3.3-70B-Instruct"

# Use the same model for the agent and for Progent's policy generation/update.
export SECAGENT_POLICY_MODEL="$model"

# Progent privilege control (SECAGENT_GENERATE) and policy auto-update
# (SECAGENT_UPDATE) are ON by default -> logs go to logs/<model>+progent/...
# Set SECAGENT_GENERATE=False for a plain baseline (logs to logs/<model>/...).
export SECAGENT_IGNORE_UPDATE_ERROR="True"

for suite in banking slack travel workspace; do
    SECAGENT_SUITE=$suite nohup python -m agentdojo.scripts.benchmark -s $suite --model "$model" --logdir $log_dir > $log_dir/$suite-no-attack.log 2>&1 &
    SECAGENT_SUITE=$suite nohup python -m agentdojo.scripts.benchmark -s $suite --model "$model" --attack important_instructions --logdir $log_dir > $log_dir/$suite-attack.log 2>&1 &
done

echo "started"
