# Progent: Securing AI Agents with Privilege Control

Check out our paper [here](https://arxiv.org/abs/2504.11703).

Progent secures LLM agents by enforcing **privilege control** over tool calls: it
generates and updates a per-task security policy and blocks any tool call the
policy does not allow. This repo contains the Progent library (`secagent`) plus
the experiment harnesses from the paper.

## Repository Layout

| Directory | What it is |
| --- | --- |
| `secagent/` | The **Progent library** — policy generation/update, tool-call checker, integrations. Everything depends on it. |
| `agentdojo/` | The **[AgentDojo](https://github.com/ethz-spylab/agentdojo) benchmark** + Progent (main benchmark). |
| `agentdojo-mcp/` | AgentDojo tasks served over **[MCP](https://modelcontextprotocol.io/)** (`mcp_server.py`); the tool server for `real-world-agents/`. |
| `real-world-agents/` | Drivers running **real frameworks** (OpenAI Agents SDK, LangChain, OpenHands, AutoGen) against `agentdojo-mcp`, with Progent. |
| `asb/` | The **[Agent Security Bench](https://github.com/agiresearch/ASB)** harness + Progent (separate benchmark). |

## Install & Run (AgentDojo)

`secagent` is **not** installed as a package — only its deps are; it's imported
from the repo root (`run.sh` puts it on `PYTHONPATH`). The benchmark *is* installed.

```bash
pip install -r requirements.txt    # secagent deps (use a venv / conda env, Python >= 3.9)
cd agentdojo && pip install -e .    # install the AgentDojo benchmark
./run.sh                            # edit the `model` line to pick a model; prints results at the end
```

`run.sh` runs all four suites with/without the `important_instructions` attack,
using one model for both the agent and Progent's policy. Set the relevant API key
first (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `CO_API_KEY`, `GCP_PROJECT`/`GCP_LOCATION`).

## Locally Served Models (vLLM)

`Qwen/Qwen3-30B-A3B-Instruct-2507`, `Qwen3.6-35B-A3B`, and
`meta-llama/Llama-3.3-70B-Instruct` are registered as local models. Tool calling is done via prompting, so a plain
`vllm serve` is enough (no server-side tool-call parser needed):

```bash
# 1. Serve the model (adjust --tensor-parallel-size to your GPUs)
vllm serve Qwen/Qwen3-30B-A3B-Instruct-2507 --port 8000 --gpu-memory-utilization 0.95
```

The agent uses `LOCAL_BASE_URL` and the policy uses `SECAGENT_POLICY_BASE_URL`
(both default to `localhost:8000`), so one server serves both.

## Progent Settings (env vars)

Privilege control is **on by default**; `run.sh` shows typical values.

| Variable | Default | Meaning |
| --- | --- | --- |
| `SECAGENT_GENERATE` | `True` | Generate a per-task policy. `False` = plain baseline. |
| `SECAGENT_UPDATE` | `False` | Update the policy during a task. `run.sh` sets `True` (the benchmark gate defaults off). |
| `SECAGENT_POLICY_MODEL` | `gpt-4o-2024-08-06` | Model used to generate/update the policy. |
| `LOCAL_BASE_URL` / `SECAGENT_POLICY_BASE_URL` | `localhost:8000` | Local agent / policy endpoints. |

## Other Benchmarks

```bash
# ASB
cd asb && pip install -r requirements.txt
export PYTHONPATH="$PWD/..:$PYTHONPATH"
python scripts/agent_attack.py --cfg_path config/OPI.yml

# Real-world agents: start the MCP server, then a framework driver
cd agentdojo-mcp && pip install -e . && export PYTHONPATH="$PWD/..:$PYTHONPATH" && python mcp_server.py
cd real-world-agents && pip install -r requirements.txt && export PYTHONPATH="$PWD/..:$PYTHONPATH" && ./run.sh
```

For ASB, list a served model under `llms:` in the config; non gpt/gemini/claude/ollama
names use the `local` backend (OpenAI-compatible, `LOCAL_BASE_URL`).

## Logs

Results go to `logs/`, keyed by model basename + `+progent` (dropped for baselines):

```
# AgentDojo: one JSON per task
logs/<model>+progent/<suite>/<user_task>/{none/none.json, <attack>/<injection>.json}
# ASB: under the injection method
logs/<injection_method>/<model>+progent/...
```
