---
name: linux-ai-dev-stack
description: >
  Install and wire the AI toolchain on a Linux dev machine: local LLM inference
  (Ollama, llama.cpp, vLLM, SGLang, TabbyAPI) with VRAM-based model selection, AI
  coding agents and CLIs (Claude Code, Codex, aider, OpenCode) with MCP servers,
  ML frameworks (PyTorch/JAX, Jupyter, HuggingFace) and GPU containers, and
  cloud/remote GPU workflows (RunPod, Vast.ai, Lambda, remote dev over SSH and
  Tailscale). Use when someone wants to run local models, set up or connect AI
  coding agents, configure MCP servers, route agents to local or cloud models,
  install an ML/GPU Python stack, or offload work to a rented GPU. It runs on the
  machine and assumes working GPU drivers.
license: MIT
compatibility: >
  Runs on the target Linux machine; needs shell access and, for local inference
  and ML frameworks, a working GPU driver/compute stack (configure that with the
  Linux dev workstation skill first). A web search tool is recommended to verify
  current engine, model, and package versions.
metadata:
  opensite-category: ai
  opensite-scope: shared
  opensite-visibility: public
---

# Linux AI Dev Stack

**Mode: Configurator — runs on the machine.** This is the AI-focused heart of the
Linux environment suite. It installs and wires local LLM inference, AI coding
agents, MCP servers, ML frameworks, and remote GPU workflows. It assumes GPU
drivers and the compute stack are already working — configure those first with
`linux-dev-workstation`.

> Currency guardrail: engine, model, and package versions move fast. Every version
> or model name embedded below is labeled "as of 2026-07 — verify." Confirm current
> values with a web search at runtime before you install or quote them.

## SAFETY PROTOCOL (read before running anything)

1. **Detect first.** Confirm GPU vendor + VRAM before choosing an engine or model
   (`nvidia-smi`, `rocm-smi`, `xpu-smi`, `system_profiler` on Asahi). Never assume.
2. **Assume drivers work; do not install them here.** If `nvidia-smi`/`rocm-smi`
   fails, stop and hand off to `linux-dev-workstation` for drivers/compute.
3. **Idempotent steps.** Re-running a step must be safe. Check for an existing
   install/service before creating one.
4. **Verify after each stage.** Curl the health endpoint, run `ollama ps`, or hit
   `/v1/models` before moving on.
5. **Confirm before destructive/irreversible actions.** Get explicit user approval
   before deleting model caches, replacing a systemd unit, opening a firewall port,
   or binding a server to `0.0.0.0`.
6. **Expose local servers on the LAN safely.** Bind to `0.0.0.0` only on a trusted
   network, always set an API key, and front with a reverse proxy or Tailscale.
   Never put a raw model port on the public internet unauthenticated. See
   [references/local-llm-inference.md](references/local-llm-inference.md).
7. **Treat every MCP server as untrusted code and a prompt-injection surface.**
   Least privilege, scoped tokens, no plaintext secrets. See
   [references/mcp-servers.md](references/mcp-servers.md).

## Skill Resources

- [references/activation.md](references/activation.md) — when to use this skill vs siblings; cross-agent notes.
- [references/local-llm-inference.md](references/local-llm-inference.md) — engine matrix, quantization, VRAM tiers, systemd, LAN exposure, tuning.
- [references/ai-coding-agents.md](references/ai-coding-agents.md) — Claude Code, Codex, aider, OpenCode, Gemini CLI; auth, config, sandboxing, worktrees.
- [references/mcp-servers.md](references/mcp-servers.md) — MCP explained; essential servers; scopes; prompt-injection/least-privilege security.
- [references/model-wiring.md](references/model-wiring.md) — cloud keys + local endpoints; LiteLLM proxy; cost/model routing.
- [references/ml-frameworks.md](references/ml-frameworks.md) — uv/pixi env; PyTorch/JAX/TF with CUDA/ROCm/XPU; Jupyter; HuggingFace; GPU containers.
- [references/remote-gpu.md](references/remote-gpu.md) — RunPod/Vast/Lambda/Modal; remote dev; sync; Tailscale/cloudflared; cost tips.
- [templates/AGENTS.md](templates/AGENTS.md) — starter cross-tool agent instructions (symlink `CLAUDE.md` → `AGENTS.md`).
- [templates/litellm-config.yaml](templates/litellm-config.yaml) — LiteLLM routing for local + cloud models.
- [templates/gpu-compose.yaml](templates/gpu-compose.yaml) — Docker Compose inference service with an NVIDIA GPU reservation.
- [examples/24gb-nvidia-local-plus-cloud.md](examples/24gb-nvidia-local-plus-cloud.md) — worked setup on a 24GB NVIDIA box.

## Preflight

Detect the accelerator and read its VRAM before anything else:

```bash
nvidia-smi --query-gpu=name,memory.total --format=csv   # NVIDIA
rocm-smi --showproductname --showmeminfo vram           # AMD ROCm
xpu-smi discovery                                        # Intel Arc / XPU
# Apple Silicon (Asahi): unified memory — check `free -h` / system RAM
```

If the query fails, the driver/compute stack is not ready: stop and run
`linux-dev-workstation` first. Once you have the VRAM number, pick a tier from the
table below and proceed in order.

## Wire-up order

Do these in sequence; each has a verify step and links to its reference.

1. **Local inference engine** — install Ollama (default), or llama.cpp / vLLM /
   SGLang / TabbyAPI per the matrix. Verify: `curl http://localhost:11434/v1/models`.
   → [references/local-llm-inference.md](references/local-llm-inference.md)
2. **Model selection by VRAM tier** — pull a model that fits (see tier table).
   Verify: `ollama ps` shows `100% GPU` (or an acceptable split).
3. **AI coding agents + MCP** — install Claude Code / Codex / aider; add MCP
   servers with least privilege. Verify: agent starts, `claude mcp list` is clean.
   → [references/ai-coding-agents.md](references/ai-coding-agents.md),
   [references/mcp-servers.md](references/mcp-servers.md)
4. **Local/cloud model wiring** — point OpenAI-shaped tools at `/v1`; run a LiteLLM
   proxy for Anthropic-API tools. Verify: a test completion returns.
   → [references/model-wiring.md](references/model-wiring.md)
5. **ML frameworks** — create a uv/pixi env; install PyTorch/JAX for your compute
   platform; set up Jupyter + HuggingFace; enable GPU containers. Verify:
   `python -c "import torch; print(torch.cuda.is_available())"`.
   → [references/ml-frameworks.md](references/ml-frameworks.md)
6. **Optional remote GPU** — when local VRAM is not enough, rent a GPU and set up
   remote dev + sync + private networking.
   → [references/remote-gpu.md](references/remote-gpu.md)

## Engine selection matrix

Compact picks (full matrix in [references/local-llm-inference.md](references/local-llm-inference.md);
all names as of 2026-07 — verify):

| Engine | Best for | Hardware |
|---|---|---|
| **Ollama** | fastest "it works", model manager, agents, auto CPU/GPU split | NVIDIA / AMD / Apple |
| **llama.cpp / `llama-server`** | max control, any GGUF, laptops, MoE-on-CPU, exotic HW | CUDA/ROCm/Vulkan/SYCL/Metal/CPU |
| **vLLM** | high-throughput fleet/agent serving on a capable GPU | NVIDIA / AMD / TPU |
| **SGLang** | agent / shared-prefix traffic (RadixAttention), day-0 models | NVIDIA / AMD / Intel |
| **ExLlamaV3 + TabbyAPI** | best quality-per-VRAM in 24–48GB consumer VRAM | NVIDIA |
| **LM Studio** | GUI users / zero-config desktop server | NVIDIA / AMD / Apple |

Decision flow: want it working / manage models → **Ollama** (or **LM Studio** GUI).
Need control / weird HW / huge-model-on-small-VRAM → **llama.cpp**. Serving many
users/agents → **vLLM** (raw QPS) or **SGLang** (shared prefixes / newest models).
Cram the biggest best model into consumer VRAM → **ExLlamaV3 + TabbyAPI (EXL3)**.
Front several engines / team keys / cost tracking / cloud fallback → add **LiteLLM**.

## VRAM sizing rule

Weights: `VRAM_GB ≈ params_B × (bits_per_weight / 8) × 1.2`, **plus** KV cache for
your context length. At the everyday `Q4_K_M` (~4.8 bpw) that is **~0.6 GB per
billion params** before context. Shortcut: **GGUF file size on disk ≈ weight VRAM**;
add headroom + KV cache. Long context — not weights — is what usually OOMs you, so
cap `--ctx-size`/`--max-model-len` and quantize the KV cache (`q8_0` ≈ half, ~no
quality loss). Details in [references/local-llm-inference.md](references/local-llm-inference.md).

### VRAM tier → what runs well (Q4 unless noted; as of 2026-07 — verify)

| GPU VRAM | Sweet spot | Example models |
|---|---|---|
| **8 GB** | 3–8B @ Q4, short ctx | Qwen3-4B/8B, Gemma 3 4B, Llama 3.x 8B, Phi-4-mini |
| **16 GB** | 14B comfy / 24–32B @ Q3–Q4 tight | Qwen3-14B, Mistral Small, gpt-oss-20B (offload MoE) |
| **24 GB** | 24–32B @ Q4–Q5 | Qwen3-32B, Gemma 3 27B, gpt-oss-20B full |
| **48 GB** | 70B @ Q4 (EXL3), 32B @ Q6/Q8 | Llama 3.3 70B, Qwen3-32B high-quality |
| **80GB+ / multi-GPU** | 70B fp8/awq serving, 120B MoE | gpt-oss-120B, Nemotron 3 Super, large MoE |
| **CPU-only / big RAM** | MoE with active-expert offload | gpt-oss, Qwen3-MoE via `-ncmoe` / ik_llama.cpp |

## Local-model wiring gist

- **OpenAI-shaped tools** (aider, Continue, OpenCode, Codex compat profiles): point
  `base_url` at the engine's `/v1` and use a dummy key —
  Ollama `http://localhost:11434/v1`, llama-server `:8080/v1`, vLLM `:8000/v1`.
- **Anthropic-API tools** (Claude Code) speak the Anthropic Messages API, not
  OpenAI Chat Completions. Run a **LiteLLM proxy**, name a model after a real
  Anthropic model, then set `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` at it.
  See [references/model-wiring.md](references/model-wiring.md) and
  [templates/litellm-config.yaml](templates/litellm-config.yaml).

## See also

- `linux-distro-selector` — choosing a distro and verifying hardware first.
- `linux-install-planner` — installing Linux on the machine (runbook for a human).
- `linux-dev-workstation` — GPU drivers, shell, editors, language toolchains,
  containers, reproducibility, and security. **Run it before this skill** — this
  skill assumes a working driver/compute stack.
