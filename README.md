# Progent: Securing AI Agents with Privilege Control

Check out our paper [here](https://arxiv.org/abs/2504.11703).

Progent secures LLM agents by enforcing **privilege control** over the tool
calls an agent is allowed to make. It generates and updates a security policy
for each task, and intercepts tool calls so that only calls permitted by the
policy are executed. This repository contains the Progent library
(`secagent`) together with the experiment harnesses used in the paper
(AgentDojo, ASB, and a real-world MCP-based agent suite).

---

## Table of Contents
- [Requirements](#requirements)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
  - [Model provider credentials](#model-provider-credentials)
  - [Progent / policy settings](#progent--policy-settings)
  - [Locally served models](#locally-served-models)
- [Using Locally Served Models](#using-locally-served-models)
  - [Qwen3-30B-A3B-Instruct-2507](#qwen3-30b-a3b-instruct-2507-local)
  - [Llama-3.3-70B-Instruct](#llama-33-70b-instruct-local)
- [Experiments in the Paper](#experiments-in-the-paper)
  - [AgentDojo](#agentdojo)
  - [ASB](#asb)
  - [Real-world Agents](#real-world-agents)

---

## Requirements

- Python `>= 3.9` (a clean virtual environment is strongly recommended)
- API keys for any hosted model providers you intend to use (OpenAI,
  Anthropic, Google Vertex AI, Cohere, Together, …)
- For locally served open-weight models (Qwen3, Llama-3.3): a machine with
  enough GPU memory and [vLLM](https://docs.vllm.ai/) installed

### Set up a virtual environment

```bash
# with venv
python -m venv .venv
source .venv/bin/activate

# or with conda
conda create -n progent python=3.10 -y
conda activate progent
```

---

## Installation

Install the core Progent library from the repository root:

```bash
pip install -e .
```

Each experiment harness has its own additional dependencies; see
[Experiments in the Paper](#experiments-in-the-paper) for per-harness
installation steps.

---

## Environment Variables

Progent and the experiment harnesses are configured through environment
variables. Export them in your shell (or place them in a `.env` /
`run.sh`) before launching an experiment.

### Model provider credentials

These are read by the underlying SDKs and are only needed for the providers
you actually use.

| Variable | Used for | Notes |
| --- | --- | --- |
| `OPENAI_API_KEY` | OpenAI models (`gpt-4o`, `gpt-4.1`, …) | Required for OpenAI. |
| `ANTHROPIC_API_KEY` | Anthropic models (`claude-*`) | Required for Anthropic. |
| `TOGETHER_API_KEY` | Together-hosted models (e.g. Mixtral, Llama-3) | Required for the `together` providers. |
| `CO_API_KEY` | Cohere models (`command-r*`) | Required for Cohere. |
| `GCP_PROJECT` / `GCP_LOCATION` | Google Vertex AI (`gemini-*`) | Used to init Vertex AI; also run `gcloud auth application-default login`. |

### Progent / policy settings

These control Progent's privilege-control behaviour. They are honoured by
the AgentDojo and real-world-agent harnesses.

| Variable | Default | Meaning |
| --- | --- | --- |
| `ENABLE_SECAGENT` | `False` | Master switch that turns Progent's privilege control on. |
| `SECAGENT_POLICY_MODEL` | `gpt-4o-2024-08-06` | Model used to **generate / update** the security policy. Can be a hosted model or a locally served one (see below). |
| `SECAGENT_GENERATE` | `True` | Whether to auto-generate the security policy for each task. |
| `SECAGENT_UPDATE` | `True` | Whether to allow the policy to be updated during a task. |
| `SECAGENT_IGNORE_UPDATE_ERROR` | `False` | Continue running if a policy update fails to parse. |
| `SECAGENT_ONLY_ALLOW_NARROW` | `False` | Only allow narrowly-scoped (more restrictive) policies. |
| `SECAGENT_TASK_TYPE` | `general` | Task type hint used during policy generation. |
| `SECAGENT_SUITE` | – | Which benchmark suite is being run (`banking`, `slack`, `travel`, `workspace`). |

### Locally served models

When the **agent** model or the **policy** model is served locally through
an OpenAI-compatible endpoint (e.g. vLLM), the endpoint is configurable:

| Variable | Default | Applies to |
| --- | --- | --- |
| `LOCAL_MODEL_BASE_URL` | `http://localhost:8000/v1` | The **agent** model endpoint (AgentDojo / real-world agents). |
| `LOCAL_MODEL_API_KEY` | `EMPTY` | API key for the agent endpoint (vLLM ignores it). |
| `SECAGENT_POLICY_BASE_URL` | `http://127.0.0.1:8000/v1` | The **policy** model endpoint (when `SECAGENT_POLICY_MODEL` is a local `meta-llama/*` or `Qwen/*` model). |
| `SECAGENT_POLICY_API_KEY` | `EMPTY` | API key for the policy endpoint. |

> **Tip:** if the agent model and the policy model are served by *different*
> vLLM instances, give each its own port and point `LOCAL_MODEL_BASE_URL`
> and `SECAGENT_POLICY_BASE_URL` at the respective ports.

---

## Using Locally Served Models

Progent supports running both the **agent** and the **policy** on
open-weight models served locally with an OpenAI-compatible API. The
following models are registered out of the box:

| Model id | Role | Provider |
| --- | --- | --- |
| `Qwen/Qwen3-30B-A3B-Instruct-2507` | agent and/or policy | local (vLLM) |
| `meta-llama/Llama-3.3-70B-Instruct` | agent and/or policy | local (vLLM) |

Tool calling for locally served models is implemented through prompting, so
**no server-side tool-call parser is required** — a vanilla `vllm serve`
launch is sufficient.

### Qwen3-30B-A3B-Instruct-2507 (local)

1. Serve the model with vLLM (adjust `--tensor-parallel-size` to your GPUs):

   ```bash
   vllm serve Qwen/Qwen3-30B-A3B-Instruct-2507 \
     --tensor-parallel-size 2 \
     --port 8000 \
     --gpu-memory-utilization 0.95
   ```

2. Point Progent at it and run, e.g. for AgentDojo:

   ```bash
   export LOCAL_MODEL_BASE_URL="http://localhost:8000/v1"
   cd agentdojo
   python -m agentdojo.scripts.benchmark -s banking \
     --model "Qwen/Qwen3-30B-A3B-Instruct-2507"
   ```

   To also use it as the **policy** model:

   ```bash
   export SECAGENT_POLICY_MODEL="Qwen/Qwen3-30B-A3B-Instruct-2507"
   export SECAGENT_POLICY_BASE_URL="http://127.0.0.1:8000/v1"
   ```

### Llama-3.3-70B-Instruct (local)

1. Serve the model with vLLM:

   ```bash
   vllm serve meta-llama/Llama-3.3-70B-Instruct \
     --tensor-parallel-size 4 \
     --port 8000 \
     --gpu-memory-utilization 0.95
   ```

2. Run with it as the agent model:

   ```bash
   export LOCAL_MODEL_BASE_URL="http://localhost:8000/v1"
   cd agentdojo
   python -m agentdojo.scripts.benchmark -s banking \
     --model "meta-llama/Llama-3.3-70B-Instruct"
   ```

   And/or as the policy model:

   ```bash
   export SECAGENT_POLICY_MODEL="meta-llama/Llama-3.3-70B-Instruct"
   export SECAGENT_POLICY_BASE_URL="http://127.0.0.1:8000/v1"
   ```

---

## Experiments in the Paper

### AgentDojo

```bash
cd agentdojo
pip install -e .   # install agentdojo
cd ..
pip install -e .   # install progent
cd agentdojo
./run.sh
```

`run.sh` sets the agent model (`--model`), the policy model
(`SECAGENT_POLICY_MODEL`), and Progent options, then launches the benchmark
across the `banking`, `slack`, `travel`, and `workspace` suites with and
without the `important_instructions` attack. To use a local model, edit the
`model` / `SECAGENT_POLICY_MODEL` lines to one of the local model ids above
and start the corresponding vLLM server (see
[Using Locally Served Models](#using-locally-served-models)).

Check out more in [agentdojo/README.md](agentdojo/README.md).

### ASB

```bash
cd asb
pip install -r requirements.txt   # install asb
cd ..
pip install -e .                  # install progent
cd asb
python scripts/agent_attack.py --cfg_path config/OPI.yml
```

The model(s) to evaluate are listed under `llms:` in the chosen config file
(e.g. `config/OPI.yml`). ASB can drive locally deployed models through its
`vllm`/`ollama` backends. Check out more in [asb/README.md](asb/README.md).

### Real-world Agents

```bash
cd agentdojo-mcp
pip install -e .       # install agentdojo-mcp
python mcp_server.py   # start the mcp server
cd ..
pip install -e .       # install progent
cd real-world-agents
pip install -r requirements.txt
./run.sh
```

`run.sh` selects the agent framework via `AGENT_TYPE`
(`openai`, `langchain`, `openhands`, or `autogen`) and configures Progent
through the `SECAGENT_*` variables described above.
