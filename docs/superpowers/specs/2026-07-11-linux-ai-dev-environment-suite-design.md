# Design Spec — Linux AI Dev Environment Skill Suite

**Date:** 2026-07-11
**Status:** Approved for planning
**Author:** Claude (brainstorming session with jordan@dashtrack.com)

---

## 1. Goal

Ship a suite of Agent Skills (in the `opensite-skills` repo, following its conventions) that give an AI agent comprehensive tooling to help build **senior-level Linux development environments, optimized for AI developers**.

Two primary use cases:

1. **Remote planner / instruction generator (UC1).** A developer buys a Windows laptop and needs step-by-step instructions — starting from replacing the Windows OS with Linux, through all initial boot setup — that an *external* AI agent generates for a human sitting at the physical machine. The agent is not on the target box; it emits a runbook.
2. **On-machine configurator (UC2).** An AI agent running *on* a Linux machine uses the skill to fully configure advanced features, tooling, drivers, and the AI stack directly, executing commands with appropriate safety confirmations.

**Heavy emphasis:** building AI tooling into the Linux machine (local LLM inference, AI coding agents + MCP, ML frameworks, cloud/remote GPU).

## 2. Scope decisions (from brainstorming)

- **Packaging:** a suite of **4 topic-scoped skills** (Approach A).
- **AI capabilities:** all four areas — local LLM inference, AI coding agents/CLIs, AI/ML frameworks, cloud/remote GPU.
- **Hardware:** multi-vendor parity — NVIDIA, AMD, Apple Silicon, Intel — everywhere GPUs/accelerators appear.
- **Reproducibility:** both imperative (step-by-step) and declarative (chezmoi/Ansible/Nix) paths.
- **Added on approval:** language toolchains (Rust, Python, Ruby, JS/TS) with install/update/manage depth; Docker/containers; advanced editor config (Vim/Neovim, tmux, VS Code, Zed).

### Out of scope (YAGNI)
- GUI-only click-through installers (we describe them, don't script them).
- Exhaustive per-distro package name catalogs (agent verifies at runtime).
- Non-dev desktop tuning (gaming, media center, theming beyond dev ergonomics).
- Windows/macOS-native environments (this suite is Linux-target).
- An umbrella/orchestrator skill (cross-linking instead — matches repo).

## 3. Suite decomposition

| # | Skill (kebab-case) | Primary use case | Runs where | One-line purpose |
|---|--------------------|------------------|-----------|------------------|
| 1 | `linux-distro-selector` | UC1 | Remote/advisory | Choose the right distro + verify hardware/GPU compatibility |
| 2 | `linux-install-planner` | UC1 | Remote/advisory | Generate an ordered Windows→Linux replace/dual-boot + first-boot runbook |
| 3 | `linux-dev-workstation` | UC2 | On-machine | Configure the base senior dev environment (drivers, shell, editors, languages, containers, reproducibility, security) |
| 4 | `linux-ai-dev-stack` | UC2 | On-machine | Install + wire the AI toolchain (local LLM, AI agents + MCP, ML frameworks, remote GPU) |

**Chaining:** selector → install-planner → dev-workstation → ai-dev-stack. Each `SKILL.md` has a "See also" section pointing to siblings so an agent walks the sequence naturally. No orchestrator skill.

## 4. Cross-cutting design principles

1. **Two-mode discipline.** Skills 1–2 *emit instructions for a human* (planner mode). Skills 3–4 *execute on the machine with confirmation* (configurator mode). Each `SKILL.md` states its mode in the opening lines so an agent never runs destructive commands when it should be writing a runbook.
2. **Safety protocol on on-machine skills.** Destructive/irreversible actions (disk ops, driver swaps, `rm`, partition changes, firewall lockouts) require explicit user confirmation; steps must be idempotent and verified after each stage. Install-planner carries a prominent **danger checklist**.
3. **Multi-vendor parity.** Any GPU/accelerator content covers NVIDIA / AMD / Apple Silicon (Asahi) / Intel, plus CPU-only fallback.
4. **Currency guardrail.** Distro, driver, and model facts move fast. Each skill instructs the agent to **verify versions with a web search at runtime**. Embedded numbers are labeled "as of 2026-07 — verify." Skills should degrade gracefully as versions advance.
5. **Detect-before-act.** On-machine skills begin with a detection step (distro/package manager, GPU vendor, desktop/Wayland-vs-X11, laptop-vs-desktop) and branch from there.
6. **Progressive disclosure.** `SKILL.md` holds the decision procedure + a compact overview; deep, copy-pasteable detail lives in `references/*.md` loaded on demand.
7. **Portability + validator compliance.** MIT license; `metadata: opensite-category / opensite-scope / opensite-visibility`; imperative voice; no hardcoded local paths; each skill ships `agents/openai.yaml` and `references/activation.md`; must pass `scripts/validate_skills.py`.

## 5. Per-skill specification

Each skill directory:
```
<skill-name>/
├── SKILL.md                  # required — frontmatter + core procedure
├── agents/openai.yaml        # required — Codex/OpenAI interface metadata
├── references/
│   ├── activation.md         # required — platform activation + when-not-to-use + cross-agent notes
│   └── <topic>.md            # progressive-disclosure detail files
├── templates/                # fill-in artifacts (runbooks, configs)
└── examples/                 # 1+ worked end-to-end example
```

Frontmatter fields (all skills): `name`, `description` (what + when, <1024 chars, no `<>`), `license: MIT`, `compatibility`, `metadata`.

### 5.1 `linux-distro-selector`

- **Mode:** advisory (UC1). Safe to run anywhere; produces a recommendation, not commands.
- **SKILL.md:** a decision procedure — gather the user's *primary optimization* (never-breaks / bleeding-edge GPU / byte-reproducibility / laptop-just-works / Windows-switcher / homelab-server), constraints (hardware, GPU vendor, experience), then walk a decision tree to 1–2 recommended distros with rationale and the top trade-off. Compact comparison matrix inline.
- **references/**
  - `distro-matrix.md` — families & 2026 flagships (Ubuntu 26.04 LTS, Debian 13, Fedora 44 + atomic Silverblue/Kinoite, Universal Blue Bluefin/Aurora/Bazzite, Pop!_OS/COSMIC, Arch + CachyOS/EndeavourOS, NixOS 25.11, openSUSE Tumbleweed/Aeon, Linux Mint 22.2), each with driver-support/stability/reproducibility ratings.
  - `hardware-compat-triage.md` — "will my hardware work?": GPU vendor implications, WiFi chipset pitfalls (Broadcom/some Realtek), NVIDIA Optimus laptops, Secure Boot, fingerprint/webcam, HiDPI/Wayland readiness.
  - `atomic-vs-traditional.md` — immutable/atomic base + containerized dev (distrobox/toolbx); when a senior AI dev should choose atomic; rolling vs LTS vs point-release trade-offs.
- **templates/** `hardware-intake-worksheet.md` (inputs → recommendation).
- **examples/** one worked recommendation (e.g. "NVIDIA laptop, wants stability + recent CUDA").

### 5.2 `linux-install-planner`

- **Mode:** planner (UC1). **Emits a runbook for a human at the machine.** Never assumes it is on the target box.
- **SKILL.md:** the 8-phase playbook with a **danger checklist up front**:
  - Phase 0 end-state decision (wipe vs dual-boot, encryption, distro) →
  - Phase 1 pre-flight (verified backup, product key, hardware recon, firmware update) →
  - Phase 2 bootable media (Ventoy/Rufus/Etcher/dd + ISO checksum/GPG verify) →
  - Phase 3 UEFI/BIOS + Windows prep (Fast Startup off, BitLocker, Secure Boot, Intel RST→AHCI/VMD, TPM) →
  - Phase 4 partitioning & filesystems (GPT/ESP/root/home, ext4/btrfs/zfs, swap/zram, LUKS2, snapshots) →
  - Phase 5 installer walkthrough (Ubuntu/Fedora/Pop!_OS graphical + Arch `archinstall`) →
  - Phase 6 first-boot checklist (update, drivers, fwupd/LVFS, flatpak/RPM Fusion, one power manager, hostname, fingerprint) →
  - Phase 7 laptop pain points (NVIDIA Optimus/PRIME, WiFi firmware, battery, S3-vs-s2idle, HiDPI) →
  - Phase 8 reversibility (Windows recovery media, LUKS header backup, rescue USB).
  - **Top-5 danger callouts:** verified backup (incl. OEM recovery partition), BitLocker suspend/decrypt, Intel RST/VMD, Fast Startup + true shutdown, right-disk when flashing.
- **references/** `bootable-media.md`, `uefi-secureboot.md`, `partitioning-encryption.md`, `first-boot-checklist.md`, `laptop-fixes.md`.
- **templates/** `install-runbook.md` (fill-in-the-blanks personalized runbook the agent hands to the user).
- **examples/** one worked runbook (e.g. "Dell XPS, full wipe, Ubuntu LTS, LUKS").

### 5.3 `linux-dev-workstation`

- **Mode:** configurator (UC2). Executes with the safety protocol; starts with detect-distro/detect-GPU.
- **SKILL.md:** ordered bring-up — detect → drivers → shell/terminal → editors → language toolchains → containers → reproducibility → security — each stage idempotent and verified. Points to `linux-ai-dev-stack` for the AI layer.
- **references/**
  - `gpu-drivers.md` — NVIDIA (`nvidia-open` default, 580 LTSB / feature branches, CUDA 13.x + cuDNN 9.x, DKMS + Secure Boot MOK, nvidia-container-toolkit, Wayland explicit-sync), AMD (ROCm 7.2.x, amdgpu, `HSA_OVERRIDE_GFX_VERSION` for unlisted consumer GPUs, PyTorch ROCm wheels), Apple Silicon (Fedora Asahi Remix, M1/M2 only, Vulkan/llama.cpp, no CUDA/ROCm), Intel (Arc/Core Ultra, upstream PyTorch XPU wheels since IPEX deprecation, NPU via linux-npu-driver + OpenVINO), CPU-only fallback; per-distro commands + verification.
  - `shell-terminal.md` — zsh vs fish + starship; modern CLI set (eza, bat, fd, ripgrep, zoxide, fzf, delta, dust, procs, btop); terminal emulators (Ghostty/Kitty/WezTerm/Alacritty); **multiplexers: tmux (tpm plugins, sessionizer, config) vs Zellij**.
  - `editors.md` — **advanced editor config:** Neovim/Vim (kickstart → LazyVim, LSP, treesitter, key plugins), VS Code (settings-sync, Remote-SSH, devcontainers, keybindings, extensions), Zed (native speed + AI panel). Baseline + power-user config.
  - `language-toolchains.md` — **`mise` as meta version-manager**, then per-language install/**update**/manage:
    - **Rust:** rustup, toolchains, cargo, cargo-binstall, clippy, rustfmt, rust-analyzer; `rustup update`.
    - **Python:** `uv` as default (envs, tools, `uv python install`, `uv self update`), pixi/conda for ML/scientific; ruff, pyright/basedpyright.
    - **Ruby:** mise/ruby-install/rbenv, bundler, updating rubies + gems; ruby-lsp, rubocop.
    - **JS/TS:** Node via mise/fnm, package managers (pnpm/npm/yarn/bun) + when to use each, tsc, biome/eslint+prettier, typescript-language-server; updating Node + globals.
    - Cross-cutting: LSP/linter/formatter table, per-project pinning via `mise`/`.tool-versions`, upgrade cadence + safety.
  - `containers.md` — Docker Engine vs Podman (rootless), Compose v2, image hygiene, devcontainers/Dev Container spec; GPU passthrough cross-linked to `linux-ai-dev-stack`.
  - `reproducibility.md` — imperative↔declarative: chezmoi (dotfiles) vs GNU Stow vs bare git; Ansible workstation playbook structure; Nix / home-manager / flakes / devenv + direnv; NixOS whole-system; recommendation matrix by user type.
  - `security-hardening.md` — ed25519 (FIDO2) SSH keys, SSH-based commit signing, secrets (age+sops or 1Password CLI or `pass`), firewall (ufw/firewalld default-deny), auto security updates, backups (restic/borg off-host + btrfs/zfs snapshots).
- **templates/** `mise.toml` (pins Rust/Python/Ruby/Node), `chezmoi` dotfiles layout skeleton, `ansible-workstation.yml` playbook skeleton, `tmux.conf` starter, `devcontainer.json` sample.
- **examples/** one worked "fresh Ubuntu → configured senior dev box" transcript.

### 5.4 `linux-ai-dev-stack`

- **Mode:** configurator (UC2). Gated on a working GPU stack — defers to `linux-dev-workstation` for drivers.
- **SKILL.md:** install-and-wire procedure — confirm GPU/VRAM → local inference engine → model selection by VRAM tier → AI coding agents + MCP → local/cloud model wiring → ML frameworks → optional remote GPU. Prominent AI emphasis (this is the heart of the suite).
- **references/**
  - `local-llm-inference.md` — engine selection (Ollama default; llama.cpp/llama-server; vLLM; SGLang; ExLlamaV3+TabbyAPI; LM Studio; mlc-llm) + VRAM sizing rule (`~0.6 GB/B params @ Q4` + KV cache) + tiered model recommendations (8/16/24/48/80GB+) + quantization formats + systemd service + safe LAN exposure + tuning (flash-attn, KV quant, offload, speculative decoding).
  - `ai-coding-agents.md` — Claude Code (primary), Codex CLI, aider/OpenCode, Gemini CLI; editor AI (VS Code Copilot agent mode, Zed, Neovim avante/copilot); install/auth/config; sandboxing + git worktrees for parallel agents; permission modes.
  - `mcp-servers.md` — what MCP is (2026), essential servers (filesystem, git, github, context7, playwright, memory, fetch, sequential-thinking), scopes (`.mcp.json` committed vs user config), prompt-injection / least-privilege security.
  - `model-wiring.md` — wire agents to **both** cloud (Anthropic/OpenAI/Google keys, secure storage) and **local** models; Ollama OpenAI-compatible `/v1`; **LiteLLM proxy** for Anthropic-API tools (`ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN`); cost/model routing (triage→build→review).
  - `ml-frameworks.md` — Python env via uv/pixi; PyTorch/JAX/TensorFlow install with CUDA/ROCm/XPU; Jupyter/JupyterLab; HuggingFace stack (transformers/datasets/accelerate/hf CLI); reproducible GPU containers (Docker/Podman + NVIDIA Container Toolkit, rootless, CDI).
  - `remote-gpu.md` — when local isn't enough; providers (RunPod default, Vast.ai cheapest, Lambda multi-GPU training, Modal serverless); remote dev (VS Code Remote-SSH, Zed remote, mosh, tmux); code/data sync (mutagen live + rsync datasets); private networking (Tailscale, cloudflared); cost tips.
- **templates/** `AGENTS.md` starter (+ note to symlink `CLAUDE.md`→`AGENTS.md`), `litellm-config.yaml`, `gpu-compose.yaml`.
- **examples/** one worked "configure local + cloud AI dev stack on a 24GB NVIDIA box" transcript.

## 6. Conventions & quality gates

- Each `SKILL.md` frontmatter validated: kebab `name` = directory, `description` <1024 chars with no `<>`, covers what + when, `license: MIT`, only official top-level fields.
- `agents/openai.yaml`: `interface.display_name`, `short_description`, `default_prompt`; `policy.allow_implicit_invocation: true`.
- `references/activation.md`: best-fit tasks, explicit-invocation example, when-NOT-to-use (incl. cross-references to sibling skills), cross-agent notes.
- No hardcoded machine paths; imperative voice; no `.bak`/`.tmp`/draft files.
- Final gate: `python3 scripts/validate_skills.py` passes for all four skills.
- Research source material lives in `.research-linux-ai/` (gitignored scratch; not shipped). Cleaned up or left untracked before PR.

## 7. Build sequence (for the implementation plan)

1. Scaffold all four skill directories with required files.
2. Author skill #1 `linux-distro-selector` (SKILL.md + references + template + example + agents/activation), validate.
3. Author skill #2 `linux-install-planner`, validate.
4. Author skill #3 `linux-dev-workstation` (largest), validate.
5. Author skill #4 `linux-ai-dev-stack`, validate.
6. Add cross-links ("See also") across all four.
7. Run `scripts/validate_skills.py`; fix any failures.
8. Update repo `README.md` skill index to list the new suite (`AGENTS.md` is gitignored/local-only, so updating it is optional and won't be committed).
9. Commit on a `feat/linux-ai-dev-environment-suite` branch; open PR per repo conventions.

## 8. Success criteria

- Given "help me switch this Windows laptop to Linux for AI dev," an agent selects a distro (#1) and produces a safe, ordered install runbook (#2).
- Given a fresh Linux box, an agent configures a senior dev environment incl. GPU drivers, Rust/Python/Ruby/JS-TS toolchains, Docker, tmux/Neovim/VS Code (#3), then installs a working local + cloud AI stack with agents + MCP (#4).
- Multi-vendor GPU guidance present throughout; both imperative and declarative reproducibility paths offered.
- All four skills pass the repo validator and follow the open Agent Skills standard.
