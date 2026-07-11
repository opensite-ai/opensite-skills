# Activation Guide — linux-dev-workstation

## Best-fit tasks

Use this skill when an agent is running **on a Linux machine** and the user wants
to build or upgrade a senior developer environment. Concretely:

- Install or fix GPU drivers and the compute stack (NVIDIA CUDA, AMD ROCm, Intel
  XPU/oneAPI/NPU, Apple Silicon/Asahi, or a CPU-only box).
- Set up the shell and terminal: zsh/fish, starship, the modern CLI set
  (ripgrep, fd, bat, eza, zoxide, fzf, delta, btop), and tmux or Zellij.
- Configure editors at a power-user level: Neovim/Vim (LSP, treesitter), VS Code
  (Remote-SSH, Dev Containers, settings sync), or Zed.
- Install and manage language toolchains for Rust, Python, Ruby, and JS/TS —
  including per-project version pinning and explicit upgrade workflows.
- Stand up containers: Docker Engine or rootless Podman, Compose v2, and
  devcontainers.
- Make the machine reproducible with chezmoi, Ansible, or Nix/home-manager.
- Harden the box: SSH keys, signed commits, secrets management, firewall, auto
  security updates, and backups.

## Explicit invocation

> Use `$linux-dev-workstation` to configure this Linux dev box — install the GPU
> driver stack, set up zsh + starship + tmux, install Rust/Python/Ruby/Node via
> mise/uv, enable rootless Podman, and harden SSH and the firewall.

The skill runs commands on the machine, so it always begins with the detection
step and follows the SAFETY PROTOCOL (confirm before anything destructive).

## When NOT to use (route to a sibling instead)

- **The distro is not chosen yet** → use `linux-distro-selector` to pick a distro
  and confirm hardware compatibility first.
- **Linux is not installed yet** (replacing Windows, dual-boot, clean install)
  → use `linux-install-planner` to generate the install runbook; return here
  after first boot.
- **The user wants the AI/LLM toolchain** (local inference, AI coding agents,
  MCP servers, ML frameworks, remote GPU) → use `linux-ai-dev-stack`. This skill
  installs the base and GPU drivers that stack depends on; run it first, then
  hand off.

## Cross-agent notes

- This is a **configurator** skill: it executes on the target machine. If an
  agent is *not* on the machine (advisory/remote context), it should produce
  instructions and prefer `linux-install-planner` / `linux-distro-selector`
  instead of pretending to run these commands.
- Portable across agent platforms that expose a shell tool. `agents/openai.yaml`
  enables implicit invocation for Codex/OpenAI-style hosts.
- Every embedded version is labeled "as of 2026-07 — verify"; agents with a web
  search tool should confirm current driver, toolchain, and package versions at
  runtime before installing.
