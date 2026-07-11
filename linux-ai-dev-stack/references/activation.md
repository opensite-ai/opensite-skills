# Activation Guide — linux-ai-dev-stack

## Best-fit tasks

Use this skill when an agent is on a Linux machine (with working GPU drivers) and
the user wants to:

- Run local LLMs — install Ollama / llama.cpp / vLLM / SGLang / TabbyAPI / LM Studio,
  pick a model that fits VRAM, expose it safely on the LAN, or tune throughput.
- Install or connect AI coding agents — Claude Code, Codex CLI, aider, OpenCode,
  Gemini CLI — including auth, config files, sandboxing, and git worktrees.
- Configure MCP servers (filesystem, git, github, context7, playwright, memory,
  fetch, sequential-thinking) with correct scopes and least-privilege security.
- Wire agents to both cloud and local models, including a LiteLLM proxy and
  cost/model routing (triage → build → review).
- Install an ML/GPU Python stack — uv/pixi env, PyTorch/JAX/TensorFlow with
  CUDA/ROCm/XPU, Jupyter, the HuggingFace stack, and GPU containers.
- Offload work to a rented GPU (RunPod, Vast.ai, Lambda, Modal) with remote dev,
  code/data sync, and private networking.

## Explicit invocation

- "Use `$linux-ai-dev-stack` to set up a local model server and point Claude Code at it."
- "Use `$linux-ai-dev-stack` to install PyTorch with CUDA and run it in a GPU container."
- "Use `$linux-ai-dev-stack` to add the essential MCP servers to my project safely."
- "Use `$linux-ai-dev-stack` to rent a RunPod GPU and iterate on it over Tailscale."

## When NOT to use (hand off to a sibling)

- **No GPU drivers / `nvidia-smi` fails** → use `linux-dev-workstation` first to
  install drivers and the compute stack. This skill assumes they already work.
- **Base dev environment not set up** (shell, editors, language toolchains,
  containers, security) → use `linux-dev-workstation`. GPU container passthrough
  (NVIDIA Container Toolkit / rootless / CDI) is shared with that skill.
- **Choosing a distro or checking hardware compatibility** → use
  `linux-distro-selector`.
- **Installing Linux on the machine** (bootable media, partitioning, first boot)
  → use `linux-install-planner`.

## Cross-agent notes

- **Modes / permissions differ per agent.** Claude Code uses OS-level sandboxed
  Bash + allow/ask/deny rules; Codex uses landlock/seccomp with an approval ×
  sandbox matrix. Respect the host agent's confirmation flow — never auto-run
  destructive commands (cache deletion, unit replacement, firewall/port changes).
- **This skill runs on the machine.** It is a configurator, not a planner: it
  executes and verifies commands rather than emitting a runbook for a human. The
  two planner siblings (`linux-distro-selector`, `linux-install-planner`) do the
  opposite.
- **Currency:** always verify engine/model/package versions with a web search at
  runtime; embedded numbers are labeled "as of 2026-07 — verify."
- **Portability:** `AGENTS.md` is the cross-tool convention; symlink `CLAUDE.md` →
  `AGENTS.md` so every agent reads one source of truth.
