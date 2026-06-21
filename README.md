# Progent: Securing AI Agents with Privilege Control

Check out our paper [here](https://arxiv.org/abs/2504.11703).

Progent secures LLM agents by enforcing **privilege control** over tool calls: it
generates and updates a per-task security policy and blocks any tool call the
policy does not allow. This repo contains the Progent library (`secagent`) plus
the experiment harnesses from the paper.

## Repository Layout

| Directory | What it is |
| --- | --- |
| `secagent/` | **The Progent library** — policy generation/update, the tool-call checker, and integrations (tool wrapper, OpenAI-agents wrapper, MCP proxy). Everything else depends on it. |
| `agentdojo/` | The **[AgentDojo](https://github.com/ethz-spylab/agentdojo) benchmark** + Progent. Runs the `banking`/`slack`/`travel`/`workspace` suites with and without prompt-injection attacks. Main benchmark for the paper. |
| `agentdojo-mcp/` | The same AgentDojo tasks exposed over **[MCP](https://modelcontextprotocol.io/)**. `mcp_server.py` serves the tools as MCP tools (it does *not* run an agent) — it is the tool/environment server that `real-world-agents/` connect to. |
| `real-world-agents/` | Drivers that run **real agent frameworks** (OpenAI Agents SDK, LangChain, OpenHands, AutoGen) against `agentdojo-mcp`, with Progent enforcing the same privilege control on off-the-shelf agents. |
| `asb/` | The **[Agent Security Bench (ASB)](https://github.com/agiresearch/ASB)** harness + Progent. A separate attack benchmark with its own agents and memory DB. |

`agentdojo-mcp/` (server) **+** `real-world-agents/` (agents) are two halves of
one MCP setup. `agentdojo/` and `asb/` are standalone benchmarks.

### Set up a virtual environment

```bash
# or with conda
conda create -n progent python=3.10 -y
conda activate progent
```


## Installation

`secagent` (this repo) is **not** installed as a package — install only its
dependencies and import it from the directory. The benchmark itself *is*
installed from its own directory.

```bash
pip install -r requirements.txt   # secagent deps (Python >= 3.9, a venv is recommended)
cd agentdojo && pip install -e .   # install the AgentDojo benchmark
```

`agentdojo/run.sh` adds the repo root to `PYTHONPATH` so `import secagent`
resolves to this directory — no install of `secagent` needed.

## Run (AgentDojo)

```bash
cd agentdojo
./run.sh        # edit the `model` line in run.sh to pick a model
```

`run.sh` runs all four suites with/without the `important_instructions` attack,
using the same model as the agent and as Progent's policy model. Set provider API
keys first: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `CO_API_KEY` (Cohere),
`GCP_PROJECT`/`GCP_LOCATION` (Vertex AI / Gemini), or `TOGETHER_API_KEY`.

## Locally Served Models (vLLM)

`Qwen/Qwen3-30B-A3B-Instruct-2507` and `meta-llama/Llama-3.3-70B-Instruct` are
registered as local models. Tool calling is done via prompting, so a plain
`vllm serve` is enough (no server-side tool-call parser needed):

```bash
# 1. Serve the model (adjust --tensor-parallel-size to your GPUs)
vllm serve Qwen/Qwen3-30B-A3B-Instruct-2507 --port 8000 --gpu-memory-utilization 0.95

# 2. Use it in agentdojo/run.sh (already the default there):
#    model="Qwen/Qwen3-30B-A3B-Instruct-2507"
#    (SECAGENT_POLICY_MODEL is set to the same model)
```

If the server is not on `localhost:8000`, set `LOCAL_MODEL_BASE_URL` (agent) and
`SECAGENT_POLICY_BASE_URL` (policy).

## Progent Settings

Configured via environment variables (see `agentdojo/run.sh` for typical values).
**Policy generation is ON by default** (`SECAGENT_GENERATE=True`); **policy
auto-update is OFF by default** in the AgentDojo benchmark — `run.sh` enables it
explicitly with `SECAGENT_UPDATE=True`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `SECAGENT_GENERATE` | `True` | Generate a security policy per task. `False` = plain baseline (no Progent). |
| `SECAGENT_UPDATE` | `False`* | Update the policy during a task. *The AgentDojo update gate defaults to off; `run.sh` sets it to `True`. |
| `SECAGENT_POLICY_MODEL` | `gpt-4o-2024-08-06` | Model used to generate/update the policy (hosted or local). |
| `SECAGENT_IGNORE_UPDATE_ERROR` | `False` | Keep running if a policy update fails to parse. |
| `SECAGENT_ONLY_ALLOW_NARROW` | `False` | Only allow narrowly-scoped (stricter) policies. |
| `LOCAL_MODEL_BASE_URL` | `http://localhost:8000/v1` | Local **agent** model endpoint. |
| `SECAGENT_POLICY_BASE_URL` | `http://127.0.0.1:8000/v1` | Local **policy** model endpoint. |

## Other Benchmarks

**ASB:**

```bash
cd asb
pip install -r requirements.txt
export PYTHONPATH="$PWD/..:$PYTHONPATH"   # make secagent importable
python scripts/agent_attack.py --cfg_path config/OPI.yml
```

**Real-world agents** (start the server, then the agent driver):

```bash
# terminal 1 — tool/environment server
cd agentdojo-mcp && pip install -e .
export PYTHONPATH="$PWD/..:$PYTHONPATH"
python mcp_server.py

# terminal 2 — real agent framework (set AGENT_TYPE in run.sh: openai/langchain/openhands/autogen)
cd real-world-agents && pip install -r requirements.txt
export PYTHONPATH="$PWD/..:$PYTHONPATH"
./run.sh
```

## Logs

AgentDojo and ASB write to `logs/` using the model basename with a `+progent`
suffix when Progent is enabled (dropped for baseline runs):

```
# AgentDojo: one JSON per task
logs/<model>+progent/<suite>/<user_task>/{none/none.json, <attack>/<injection>.json}

# ASB: results under the injection method
logs/<injection_method>/<model>+progent/...
```
