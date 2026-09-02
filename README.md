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
| — | `agentdojo/` also includes the **[AgentDyn](https://github.com/SaFo-Lab/AgentDyn)** dynamic suites (`shopping`, `github`, `dailylife`), integrated with Progent like the original four. |
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

## AgentDyn Suites (shopping / github / dailylife)

The [AgentDyn](https://github.com/SaFo-Lab/AgentDyn) dynamic suites are merged
into `agentdojo/src/agentdojo` — no extra install; the same CLI arguments and
`SECAGENT_*` variables apply, and their tools are privilege-controlled by
Progent exactly like the original suites (allowlists follow AgentDyn's official
Progent integration). Run them by overriding the suite list:

```bash
cd agentdojo
SUITES="shopping github dailylife" EXTRA_ARGS="--system-message-name agentdyn" ./run.sh
```

`--system-message-name agentdyn` selects AgentDyn's system message (it appends a
"complete tasks without asking for confirmation" line); omit it to keep the
AgentDojo default.

## ChatInject Attack

[ChatInject](https://github.com/hwanchang00/ChatInject) injects fake chat-template
turns (role-confusion) in the target model's tokenizer format. It is registered
as extra `--attack` options in AgentDojo:

| `--attack` | What it does |
| --- | --- |
| `chat_inject_qwen3` / `chat_inject_glm` | Single fake system+user+assistant turn in the Qwen3 / GLM-4.5 template. |
| `chat_inject_{qwen3,glm}_with_utility_system_multiturn_7` | Prepends a 7-turn "utility" dialogue reconstructed in that template. |
| `chat_inject_{qwen3,glm}_with_utility_authority_endorsement_system_multiturn_7` | Same, in the authority-endorsement persuasion style. |

```bash
cd agentdojo
python -m agentdojo.scripts.benchmark -s banking --model "$model" --attack chat_inject_qwen3
```

The multi-turn variants read pre-generated dialogues from
`src/agentdojo/attacks/chatinject_data/*.json`, keyed by exact injection-task
`GOAL`. That data covers **banking / slack / travel only**; an uncovered GOAL
(all of workspace/shopping, and one re-registered travel task) raises a
`ValueError`. The single-turn variants have no such restriction.

## Locally Served Models (vLLM)

`Qwen/Qwen3-30B-A3B-Instruct-2507`, `Qwen3.6-35B-A3B`, and
`meta-llama/Llama-3.3-70B-Instruct` are registered as local models. Tool calling
is done via prompting, so a plain `vllm serve` is enough (no server-side
tool-call parser needed):

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
# ASB -- Observation Prompt Injection (OPI) slice, on a locally-served model.
cd asb && pip install -r requirements-opi.txt
export MODEL=Qwen3.6-35B-A3B            # must match the vLLM --served-model-name
bash scripts/run_opi.sh progent         # Progent defense  (""=baseline, camel=CaMeL)

# Real-world agents: start the MCP server, then a framework driver
cd agentdojo-mcp && pip install -e . && export PYTHONPATH="$PWD/..:$PYTHONPATH" && python mcp_server.py
cd real-world-agents && pip install -r requirements.txt && export PYTHONPATH="$PWD/..:$PYTHONPATH" && ./run.sh
```

The `asb/` harness is the ASB **OPI slice** (from ASB, with a ReAct tool-calling
mode + AgentDojo-format output). `run_opi.sh` runs it on an OpenAI-compatible
endpoint (`LOCAL_BASE_URL`/`LOCAL_API_KEY`); pick the defense with its first
argument. **Progent** is wired as `--defense_type progent`: it builds a per-task
policy and blocks every tool call the policy disallows (incl. the injected
attacker tool) — `import secagent` resolves from the repo root, which the script
puts on `PYTHONPATH`. `--defense_type camel` (CaMeL) additionally needs the CaMeL
kernel (`src.camel`) from the camel-prompt-injection repo, so run CaMeL there;
Progent and the baseline run from this repo as-is. Per-task AgentDojo `TaskResults`
JSON (with the generated `security_policy`/`policy_trace`) lands under
`asb/logs/observation_prompt_injection/<model>/<defense>/json/...`.

## Logs

Results go to `logs/`, keyed by model basename + `+progent` (dropped for baselines):

```
# AgentDojo (incl. the AgentDyn suites): one JSON per task
logs/<model>+progent/<suite>/<user_task>/{none/none.json, <attack>/<injection>.json}
# ASB: under the injection method
logs/<injection_method>/<model>+progent/...
```
