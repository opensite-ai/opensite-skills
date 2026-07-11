# Worked Example — Local + Cloud AI Dev Stack on a 24GB NVIDIA Box

Scenario: a developer has a fresh senior dev workstation (drivers already installed
via `linux-dev-workstation`) with a **24GB NVIDIA GPU** (e.g. RTX 4090). They want a
local model for high-frequency low-stakes work, cloud models for hard tasks, Claude
Code + Codex + aider wired up, essential MCP servers, and an ML env for PyTorch. All
versions/model names below are **as of 2026-07 — verify.**

This is a configurator run, so the agent follows the SAFETY PROTOCOL: detect first,
keep steps idempotent, verify each stage, and confirm before anything destructive.

## Step 0 — Preflight (detect GPU + VRAM)

```bash
nvidia-smi --query-gpu=name,memory.total --format=csv
# NVIDIA GeForce RTX 4090, 24564 MiB   → 24GB tier
```
Driver query succeeds, so the compute stack is ready. 24GB tier → sweet spot is
**24–32B @ Q4–Q5** (e.g. Qwen3-32B, gpt-oss-20B full).

## Step 1 — Local inference engine (Ollama)

```bash
curl -fsSL https://ollama.com/install.sh | sh    # installs a systemd service
```
Tune it as a service (KV cache quant + larger context):
```bash
sudo systemctl edit ollama.service
# [Service]
# Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
# Environment="OLLAMA_FLASH_ATTENTION=1"
# Environment="OLLAMA_CONTEXT_LENGTH=8192"
sudo systemctl daemon-reload && sudo systemctl restart ollama
```
Verify: `curl -s http://localhost:11434/v1/models`. Keep it bound to localhost —
no LAN exposure requested, so no `0.0.0.0` and no open port.

## Step 2 — Model selection for the 24GB tier

```bash
ollama pull qwen2.5-coder:14b     # fast everyday coder, fits comfortably at Q4
ollama pull qwen3:32b             # bigger reasoning model, ~Q4 fits 24GB
ollama ps                         # expect 100% GPU
```
Sizing sanity check: 32B @ Q4_K_M ≈ 32 × 0.6 ≈ 19GB weights; cap context and use q8
KV so it fits 24GB. 14B ≈ 8GB leaves room for a longer context.

## Step 3 — AI coding agents + MCP

```bash
curl -fsSL https://claude.ai/install.sh | bash            # Claude Code (primary)
curl -fsSL https://chatgpt.com/codex/install.sh | sh     # Codex CLI (second opinion)
python -m pip install aider-install && aider-install      # aider (local-model wildcard)
```
Add essential MCP servers with least privilege (secrets from the environment):
```bash
claude mcp add --scope project filesystem -- npx -y @modelcontextprotocol/server-filesystem ./
claude mcp add --scope project git -- npx -y mcp-server-git
claude mcp add --scope user context7 -- npx -y @upstash/context7-mcp --api-key ${CONTEXT7_API_KEY}
claude mcp add --transport http github https://api.githubcopilot.com/mcp/
claude mcp add --scope project playwright -- npx -y @playwright/mcp
```
Set safety defaults in `~/.claude/settings.json`: enable the sandbox and
`permissions.deny` for `Read(./.env)`, `Read(./secrets/**)`, `Bash(curl *)`.
Verify: `claude mcp list` shows the servers healthy.

## Step 4 — Local/cloud model wiring

aider talks to the local model directly (OpenAI-compatible):
```bash
export OLLAMA_API_BASE=http://127.0.0.1:11434
aider --model ollama_chat/qwen2.5-coder:14b     # set num_ctx: 32768 in .aider.model.settings.yml
```
Claude Code needs a translation layer for local models — run a LiteLLM proxy using
`../templates/litellm-config.yaml`, then:
```bash
pipx install 'litellm[proxy]'
op run -- litellm --config litellm-config.yaml   # keys injected, none on disk
export ANTHROPIC_BASE_URL="http://localhost:4000"
export ANTHROPIC_AUTH_TOKEN="sk-litellm-key"
claude    # now Claude Code can hit the local alias; unset the vars to go back to cloud
```
Routing plan: Haiku/local triages → Sonnet builds → Opus reviews. Autocomplete +
trivial transforms go to the local Qwen model (zero cloud spend).

## Step 5 — ML frameworks (PyTorch in a uv env)

```bash
uv init ml-lab && cd ml-lab
uv add torch torchvision --index-url https://download.pytorch.org/whl/cu128
uv run python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# True NVIDIA GeForce RTX 4090
uv add jupyterlab transformers datasets accelerate
uv tool install "huggingface_hub[cli]" && hf auth login
```
For a containerized GPU service, bring up `../templates/gpu-compose.yaml`
(`docker compose -f gpu-compose.yaml up -d`) after installing the NVIDIA Container
Toolkit.

## Step 6 — Remote GPU (deferred)

24GB is plenty for this developer's local work, so remote GPU is not needed now. If a
70B-at-quality or multi-GPU training job comes up later, rent a RunPod pod, connect
over Tailscale, and use mutagen for live sync (see `references/remote-gpu.md`).

## Result

- Local: Ollama serving `qwen2.5-coder:14b` + `qwen3:32b`, tuned KV cache, localhost-only.
- Agents: Claude Code + Codex + aider, sandboxed, with 5 least-privilege MCP servers.
- Wiring: aider → local directly; Claude Code → local via LiteLLM, cloud by default.
- ML: uv env with CUDA PyTorch + Jupyter + HuggingFace verified on the GPU.
- Every stage verified; nothing exposed to the LAN; no secrets on disk.
