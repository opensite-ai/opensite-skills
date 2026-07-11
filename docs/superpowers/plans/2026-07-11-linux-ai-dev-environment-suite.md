# Linux AI Dev Environment Suite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a 4-skill suite that gives an AI agent comprehensive tooling to plan and configure senior-level, AI-focused Linux development environments.

**Architecture:** Four independent, cross-linked Agent Skills in the `opensite-skills` repo root, each a directory with `SKILL.md` + `agents/openai.yaml` + `references/` + `templates/` + `examples/`. Two are advisory "planner" skills (emit instructions for a human); two are "configurator" skills (run commands on the machine). Content is grounded in the research findings in `.research-linux-ai/` (local scratch, gitignored).

**Tech Stack:** Markdown skills following the open Agent Skills standard; YAML frontmatter; validated by `scripts/validate_skills.py` (Python 3, pyyaml). No runtime code beyond optional config templates.

## Global Constraints

- **Skill names (kebab, = directory):** `linux-distro-selector`, `linux-install-planner`, `linux-dev-workstation`, `linux-ai-dev-stack`.
- **`SKILL.md` ≤ 500 lines each** — hard validator limit. Keep SKILL.md to procedure + compact overview; push all deep detail into `references/*.md`.
- **Frontmatter required keys:** `name` (must equal directory name), `description` (string, <1024 chars, no `<` or `>` characters), `compatibility` (non-empty string), `metadata` mapping containing `opensite-category`, `opensite-scope`, `opensite-visibility`. Also include `license: MIT`.
- **`metadata` values:** `opensite-scope: shared`, `opensite-visibility: public`; `opensite-category`: `setup` for skills 1–3, `ai` for skill 4.
- **`agents/openai.yaml`:** `interface.display_name`, `interface.short_description` (**25–64 characters, verify exact length**), `interface.default_prompt` (**must contain the literal `$<skill-name>`**); `policy.allow_implicit_invocation: true`.
- **`references/activation.md` required** for every skill (best-fit tasks, explicit-invocation example, when-NOT-to-use with sibling cross-refs, cross-agent notes).
- **Links:** any markdown link in `SKILL.md` that is not `http(s)://` or `/`-absolute must point to a file that exists in that skill dir. Reference sibling skills **by name in backticks** (e.g. `` `linux-install-planner` ``), never as a relative file link, to keep link validation self-contained.
- **Voice:** imperative. **No** hardcoded local machine paths, usernames, or `.bak`/`.tmp`/draft files.
- **Currency guardrail:** every skill instructs the agent to verify versions/model names with a web search at runtime; embedded version numbers are labeled "as of 2026-07 — verify."
- **Multi-vendor parity:** any GPU/accelerator content covers NVIDIA / AMD / Intel / Apple Silicon (Asahi) + CPU fallback.
- **Content source:** draw concrete facts, commands, and tables from the matching `.research-linux-ai/0N-*.md` file; do not invent version numbers.
- **Gate for every task:** `python3 scripts/validate_skills.py` prints "Validated N skills successfully." with no errors for the skill(s) touched.

---

## File Structure

```
linux-distro-selector/
├── SKILL.md
├── agents/openai.yaml
├── references/{activation,distro-matrix,hardware-compat-triage,atomic-vs-traditional}.md
├── templates/hardware-intake-worksheet.md
└── examples/nvidia-laptop-stability.md

linux-install-planner/
├── SKILL.md
├── agents/openai.yaml
├── references/{activation,bootable-media,uefi-secureboot,partitioning-encryption,first-boot-checklist,laptop-fixes}.md
├── templates/install-runbook.md
└── examples/dell-xps-full-wipe-ubuntu.md

linux-dev-workstation/
├── SKILL.md
├── agents/openai.yaml
├── references/{activation,gpu-drivers,shell-terminal,editors,language-toolchains,containers,reproducibility,security-hardening}.md
├── templates/{mise.toml,chezmoi-layout.md,ansible-workstation.yml,tmux.conf,devcontainer.json}
└── examples/fresh-ubuntu-to-senior-devbox.md

linux-ai-dev-stack/
├── SKILL.md
├── agents/openai.yaml
├── references/{activation,local-llm-inference,ai-coding-agents,mcp-servers,model-wiring,ml-frameworks,remote-gpu}.md
├── templates/{AGENTS.md,litellm-config.yaml,gpu-compose.yaml}
└── examples/24gb-nvidia-local-plus-cloud.md
```

---

## Task 1: `linux-distro-selector`

**Files:**
- Create: `linux-distro-selector/SKILL.md`
- Create: `linux-distro-selector/agents/openai.yaml`
- Create: `linux-distro-selector/references/activation.md`
- Create: `linux-distro-selector/references/distro-matrix.md`
- Create: `linux-distro-selector/references/hardware-compat-triage.md`
- Create: `linux-distro-selector/references/atomic-vs-traditional.md`
- Create: `linux-distro-selector/templates/hardware-intake-worksheet.md`
- Create: `linux-distro-selector/examples/nvidia-laptop-stability.md`
- Content source: `.research-linux-ai/01-distro-selection.md`

**Interfaces:**
- Produces: an advisory skill. Siblings reference it by name only.

- [ ] **Step 1: Write `SKILL.md` frontmatter**

```yaml
---
name: linux-distro-selector
description: >
  Choose the right Linux distribution for a developer or AI/ML workstation and
  confirm the hardware will work before installing. Use when someone asks which
  Linux distro to pick; is comparing Ubuntu, Fedora, Arch, NixOS, Pop!_OS, Mint,
  or atomic/immutable distros; is switching from Windows or macOS and unsure what
  to install; needs a distro matched to a use case (maximum stability,
  bleeding-edge GPU/AI work, reproducibility, laptop battery life, or a server);
  or wants to check whether a GPU, Wi-Fi chipset, or laptop is Linux-compatible.
  Advisory only: it produces a recommendation, not install commands.
license: MIT
compatibility: >
  Works on any agent platform. No machine access required; this skill produces a
  recommendation. A web search tool is recommended to verify current distro
  releases and hardware support at runtime.
metadata:
  opensite-category: setup
  opensite-scope: shared
  opensite-visibility: public
---
```

- [ ] **Step 2: Write `SKILL.md` body** (mode banner: "Advisory — output a recommendation, not commands"). Sections:
  - **Skill Resources** — bullet links to the four `references/*.md`, the template, and the example (use `[text](references/distro-matrix.md)` form; all must exist by end of task).
  - **How to use** — (1) elicit the user's *primary optimization* + constraints; (2) walk the decision tree; (3) return 1–2 recommendations with rationale + top trade-off + a pointer to `linux-install-planner` (by name).
  - **Decision tree** (from research §decision-tree): branch on never-breaks → atomic (Bluefin/Silverblue) or Ubuntu LTS; newest-driver-ASAP → CachyOS/Tumbleweed/Fedora; byte-reproducibility → NixOS; laptop-just-works → Fedora/Pop!_OS; Windows-switcher → Mint; server/homelab → Debian/uCore.
  - **Compact comparison matrix** (≤8 rows: distro | model | driver ease | stability | reproducibility | best for).
  - **Intake questions** — the 5–6 questions to ask the user.
  - **See also** — name-only refs to `linux-install-planner`, `linux-dev-workstation`, `linux-ai-dev-stack`.
  - Keep ≤ 500 lines (aim ≤ 200).

- [ ] **Step 3: Write `agents/openai.yaml`**

```yaml
interface:
  display_name: "Linux Distro Selector"
  short_description: "Pick a Linux distro and check hardware fit"
  default_prompt: "Use $linux-distro-selector when choosing a Linux distribution or checking whether a GPU, Wi-Fi chipset, or laptop will work, and to match a distro to a use case (stability, AI/GPU work, reproducibility, laptop, or server)."
policy:
  allow_implicit_invocation: true
```
(Verify `short_description` length is 25–64 chars: "Pick a Linux distro and check hardware fit" = 42.)

- [ ] **Step 4: Write the reference files** from `.research-linux-ai/01-distro-selection.md`:
  - `distro-matrix.md` — full families + 2026 flagships (Ubuntu 26.04 LTS, Debian 13, Fedora 44 + Silverblue/Kinoite, Universal Blue Bluefin/Aurora/Bazzite, Pop!_OS/COSMIC, Arch + CachyOS/EndeavourOS, NixOS 25.11, openSUSE Tumbleweed/Aeon, Mint 22.2) with per-distro ratings + notes.
  - `hardware-compat-triage.md` — GPU vendor implications, Wi-Fi pitfalls (Broadcom/some Realtek), NVIDIA Optimus, Secure Boot, fingerprint/webcam, HiDPI/Wayland readiness; a "will my hardware work?" checklist.
  - `atomic-vs-traditional.md` — immutable base + distrobox/toolbx dev; when a senior AI dev picks atomic; rolling vs LTS vs point-release.

- [ ] **Step 5: Write template + example**
  - `templates/hardware-intake-worksheet.md` — fields (CPU, GPU vendor+model, RAM, storage, laptop/desktop, Wi-Fi chipset, primary optimization, experience level) → maps to a recommendation.
  - `examples/nvidia-laptop-stability.md` — worked: "NVIDIA laptop, wants stability + recent CUDA" → recommendation walk-through.

- [ ] **Step 6: Write `references/activation.md`** — best-fit tasks, explicit invocation (`Use $linux-distro-selector to ...`), when NOT to use (already installing → `linux-install-planner`; already chose a distro → `linux-dev-workstation`), cross-agent notes.

- [ ] **Step 7: Validate**

Run: `python3 scripts/validate_skills.py`
Expected: no errors mentioning `linux-distro-selector`.

- [ ] **Step 8: Commit**

```bash
git add linux-distro-selector
git commit -m "feat(linux-distro-selector): add distro selection + hardware triage skill"
```

---

## Task 2: `linux-install-planner`

**Files:**
- Create: `linux-install-planner/SKILL.md`, `agents/openai.yaml`
- Create: `linux-install-planner/references/{activation,bootable-media,uefi-secureboot,partitioning-encryption,first-boot-checklist,laptop-fixes}.md`
- Create: `linux-install-planner/templates/install-runbook.md`
- Create: `linux-install-planner/examples/dell-xps-full-wipe-ubuntu.md`
- Content source: `.research-linux-ai/03-os-migration-install.md`

**Interfaces:**
- Produces: a planner skill that emits a human-followable runbook. Referenced by name from siblings.

- [ ] **Step 1: Frontmatter**

```yaml
---
name: linux-install-planner
description: >
  Generate a safe, step-by-step runbook for installing Linux on a physical
  machine (replacing Windows, dual-booting, or a clean install) for a human
  sitting at the computer. Use when someone needs instructions to wipe Windows
  and install Linux, create bootable USB media, enter UEFI/BIOS, disable Secure
  Boot or Fast Startup, handle BitLocker or Intel RST, partition and encrypt a
  disk with LUKS, walk through a distro installer, or finish first-boot setup
  (drivers, firmware, power management). It emits instructions for a person to
  follow; it does not perform the install itself.
license: MIT
compatibility: >
  Works on any agent platform. Produces instructions for a human at the target
  machine; does not require access to that machine. A web search tool is
  recommended to verify current installer/tool versions at runtime.
metadata:
  opensite-category: setup
  opensite-scope: shared
  opensite-visibility: public
---
```

- [ ] **Step 2: `SKILL.md` body** (mode banner: "Planner — you are NOT on the target machine; emit a numbered runbook for a human. Never assume you can run these commands yourself."). Sections:
  - Skill Resources (links to the 5 references + template + example).
  - **Danger checklist FIRST** (top-5 from research): verified backup incl. OEM recovery partition; suspend/decrypt BitLocker + save recovery key; Intel RST/VMD → AHCI caveat; disable Fast Startup (`powercfg /H off`) + true shutdown; confirm the correct target disk before flashing/wiping.
  - **The 8-phase playbook** (compact; each phase links to its reference): Phase 0 end-state → 1 pre-flight → 2 bootable media → 3 UEFI/BIOS + Windows prep → 4 partition/filesystem/LUKS → 5 installer walkthrough → 6 first-boot → 7 laptop fixes → 8 reversibility.
  - **How to produce the runbook** — gather the user's distro (from `linux-distro-selector`), machine, and wipe-vs-dual-boot choice; fill `templates/install-runbook.md`; hand it over phase by phase; tell them to return for `linux-dev-workstation` after first boot.
  - See also (name-only). ≤ 500 lines.

- [ ] **Step 3: `agents/openai.yaml`**

```yaml
interface:
  display_name: "Linux Install Planner"
  short_description: "Step-by-step Linux install and boot setup"
  default_prompt: "Use $linux-install-planner to produce a safe, ordered runbook for installing Linux on a physical machine — bootable media, UEFI/Secure Boot, BitLocker/Intel RST handling, partitioning and LUKS encryption, the installer, and first-boot setup — for a human at the computer."
policy:
  allow_implicit_invocation: true
```
(short_description "Step-by-step Linux install and boot setup" = 41 chars.)

- [ ] **Step 4: Reference files** from `03-os-migration-install.md`: `bootable-media.md` (Ventoy/Rufus/Etcher/dd + checksum/GPG verify), `uefi-secureboot.md` (firmware entry, Secure Boot keep-vs-disable, Fast Startup, Intel RST/VMD, TPM, BitLocker), `partitioning-encryption.md` (GPT/ESP/root/home, ext4/btrfs/zfs, swap/zram, LUKS2, snapshots), `first-boot-checklist.md` (update, drivers, fwupd/LVFS, flatpak/RPM Fusion, one power manager, hostname, fingerprint), `laptop-fixes.md` (NVIDIA Optimus/PRIME, Wi-Fi firmware, battery, S3-vs-s2idle, HiDPI/Wayland).

- [ ] **Step 5: Template + example** — `templates/install-runbook.md` (fill-in personalized runbook skeleton across all 8 phases); `examples/dell-xps-full-wipe-ubuntu.md` (worked full runbook).

- [ ] **Step 6: `references/activation.md`** — best-fit, explicit invocation, when NOT to use (choosing distro → `linux-distro-selector`; post-boot config → `linux-dev-workstation`), cross-agent notes.

- [ ] **Step 7: Validate** — `python3 scripts/validate_skills.py`, no `linux-install-planner` errors.

- [ ] **Step 8: Commit**

```bash
git add linux-install-planner
git commit -m "feat(linux-install-planner): add Windows-to-Linux install runbook skill"
```

---

## Task 3: `linux-dev-workstation`

**Files:**
- Create: `linux-dev-workstation/SKILL.md`, `agents/openai.yaml`
- Create: `linux-dev-workstation/references/{activation,gpu-drivers,shell-terminal,editors,language-toolchains,containers,reproducibility,security-hardening}.md`
- Create: `linux-dev-workstation/templates/{mise.toml,chezmoi-layout.md,ansible-workstation.yml,tmux.conf,devcontainer.json}`
- Create: `linux-dev-workstation/examples/fresh-ubuntu-to-senior-devbox.md`
- Content source: `.research-linux-ai/02-hardware-gpu-drivers.md` (drivers) + `06-dev-tooling-reproducibility.md` (everything else)

**Interfaces:**
- Consumes (by name): none required; defers AI layer to `linux-ai-dev-stack`.
- Produces: configurator skill; sibling of the others.

- [ ] **Step 1: Frontmatter**

```yaml
---
name: linux-dev-workstation
description: >
  Configure a senior-grade Linux development environment on the machine: GPU
  drivers and compute stacks (NVIDIA CUDA, AMD ROCm, Intel XPU, Apple
  Silicon/Asahi), shell and terminal (zsh/fish, starship, modern CLI tools,
  tmux/zellij), advanced editor setup (Neovim/Vim, VS Code, Zed), language
  toolchains for Rust, Python, Ruby, and JavaScript/TypeScript via mise/uv/pixi,
  Docker/Podman containers, reproducible declarative setup (chezmoi, Ansible,
  Nix/home-manager), and security hardening (SSH keys, commit signing, secrets,
  firewall, backups). Use when setting up or upgrading a Linux dev box,
  installing GPU drivers, managing language versions and updates, configuring
  editors or dotfiles, or making a workstation reproducible. It runs commands on
  the machine.
license: MIT
compatibility: >
  Runs on the target Linux machine and needs shell access plus the distro's
  package manager (apt/dnf/pacman/etc.). Some steps need sudo. A web search tool
  is recommended to verify current driver, toolchain, and package versions.
metadata:
  opensite-category: setup
  opensite-scope: shared
  opensite-visibility: public
---
```

- [ ] **Step 2: `SKILL.md` body** (mode banner: "Configurator — runs on the machine. Follow the SAFETY PROTOCOL: detect first; make steps idempotent; verify after each; require explicit user confirmation before any destructive/irreversible action — disk ops, driver swaps, firewall changes, `rm`."). Sections:
  - Skill Resources (links to all 7 references + 5 templates + example).
  - **Detection step** — identify distro/package manager, GPU vendor(s), desktop + Wayland/X11, laptop/desktop; branch accordingly.
  - **Ordered bring-up** (each stage links to its reference and states verify command): drivers → shell/terminal → editors → language toolchains → containers → reproducibility → security. Then "hand off to `linux-ai-dev-stack` for the AI toolchain."
  - **Language toolchains quick map** (compact table: language → manager → install → **update** command): Rust/rustup, Python/uv, Ruby/mise, Node/mise, with `mise` as meta.
  - **Reproducibility decision** — imperative vs chezmoi+Ansible vs Nix/home-manager, one-liner each + who picks which.
  - See also (name-only). **Watch the 500-line cap** — keep this SKILL.md lean; depth belongs in references.

- [ ] **Step 3: `agents/openai.yaml`**

```yaml
interface:
  display_name: "Linux Dev Workstation"
  short_description: "Configure a senior Linux dev workstation"
  default_prompt: "Use $linux-dev-workstation to configure a Linux dev machine: GPU drivers (NVIDIA/AMD/Intel/Apple), shell and terminal, editors, Rust/Python/Ruby/JS-TS toolchains via mise/uv, Docker/Podman, reproducible dotfiles (chezmoi/Ansible/Nix), and security hardening."
policy:
  allow_implicit_invocation: true
```
(short_description "Configure a senior Linux dev workstation" = 40 chars.)

- [ ] **Step 4: Reference files**
  - `gpu-drivers.md` (from `02-hardware-gpu-drivers.md`) — per-vendor, per-distro install + verify + gotchas: NVIDIA (`nvidia-open`, 580 LTSB / feature branches, CUDA 13.x + cuDNN 9.x, DKMS + Secure Boot MOK, nvidia-container-toolkit, Wayland explicit sync, nouveau conflict), AMD (ROCm 7.2.x, amdgpu, `HSA_OVERRIDE_GFX_VERSION`, PyTorch ROCm wheels), Apple Silicon (Fedora Asahi Remix, M1/M2 only, Vulkan/llama.cpp, no CUDA/ROCm), Intel (Arc/Core Ultra, upstream PyTorch XPU wheels, NPU via linux-npu-driver + OpenVINO), CPU fallback. VRAM sizing pointer to `linux-ai-dev-stack`.
  - `shell-terminal.md` — zsh/fish + starship; modern CLI set; terminal emulators (Ghostty/Kitty/WezTerm/Alacritty); **tmux (tpm, sessionizer, config) vs Zellij**.
  - `editors.md` — Neovim/Vim (kickstart→LazyVim, LSP, treesitter), VS Code (settings-sync, Remote-SSH, devcontainers, keybindings), Zed.
  - `language-toolchains.md` — mise meta; Rust (rustup, cargo, cargo-binstall, clippy, rustfmt, rust-analyzer, `rustup update`); Python (uv envs/tools/`uv python install`/`uv self update`, pixi for ML, ruff, basedpyright); Ruby (mise/ruby-install, bundler, ruby-lsp, rubocop); JS/TS (Node via mise/fnm, pnpm/npm/yarn/bun, tsc, biome/eslint+prettier, typescript-language-server); per-project pinning, update cadence + safety; from `06-dev-tooling-reproducibility.md`.
  - `containers.md` — Docker Engine vs Podman (rootless), Compose v2, image hygiene, devcontainers; GPU passthrough → cross-ref `linux-ai-dev-stack` by name.
  - `reproducibility.md` — chezmoi vs Stow vs bare git; Ansible workstation playbook; Nix/home-manager/flakes/devenv + direnv; NixOS; recommendation matrix.
  - `security-hardening.md` — ed25519/FIDO2 SSH keys, SSH-based commit signing, secrets (age+sops / 1Password CLI / pass), ufw/firewalld default-deny, auto security updates, restic/borg + btrfs/zfs snapshots.

- [ ] **Step 5: Templates + example**
  - `templates/mise.toml` — pins Rust, Python, Ruby, Node (valid TOML).
  - `templates/chezmoi-layout.md` — recommended dotfiles repo layout.
  - `templates/ansible-workstation.yml` — valid YAML playbook skeleton (roles: base-packages, shell, languages, containers, security).
  - `templates/tmux.conf` — sensible senior defaults (prefix, mouse, vi copy, tpm block).
  - `templates/devcontainer.json` — valid JSON dev container sample.
  - `examples/fresh-ubuntu-to-senior-devbox.md` — worked transcript.

- [ ] **Step 6: `references/activation.md`** — best-fit, explicit invocation, when NOT to use (choosing distro → `linux-distro-selector`; installing the OS → `linux-install-planner`; AI/LLM stack → `linux-ai-dev-stack`), cross-agent notes.

- [ ] **Step 7: Validate** — `python3 scripts/validate_skills.py`; confirm `SKILL.md` under 500 lines (`wc -l linux-dev-workstation/SKILL.md`).

- [ ] **Step 8: Commit**

```bash
git add linux-dev-workstation
git commit -m "feat(linux-dev-workstation): add on-machine dev environment configurator skill"
```

---

## Task 4: `linux-ai-dev-stack`

**Files:**
- Create: `linux-ai-dev-stack/SKILL.md`, `agents/openai.yaml`
- Create: `linux-ai-dev-stack/references/{activation,local-llm-inference,ai-coding-agents,mcp-servers,model-wiring,ml-frameworks,remote-gpu}.md`
- Create: `linux-ai-dev-stack/templates/{AGENTS.md,litellm-config.yaml,gpu-compose.yaml}`
- Create: `linux-ai-dev-stack/examples/24gb-nvidia-local-plus-cloud.md`
- Content source: `.research-linux-ai/04-local-llm-inference.md`, `05-ai-coding-agents.md`, `06-dev-tooling-reproducibility.md` (remote GPU + ML frameworks)

**Interfaces:**
- Consumes (by name): `linux-dev-workstation` for GPU drivers (assumes a working driver/compute stack).

- [ ] **Step 1: Frontmatter**

```yaml
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
```

- [ ] **Step 2: `SKILL.md` body** (mode banner: "Configurator — runs on the machine; same SAFETY PROTOCOL as the workstation skill. Assumes GPU drivers are already working (`linux-dev-workstation`)."). Sections:
  - Skill Resources (links to 6 references + 3 templates + example).
  - **Preflight** — confirm GPU vendor + VRAM (`nvidia-smi` / `rocm-smi` / `xpu-smi`); pick the VRAM tier.
  - **Wire-up order** (each links its reference + verify): local inference engine → model selection by VRAM tier → AI coding agents + MCP → local/cloud model wiring → ML frameworks → optional remote GPU.
  - **Engine selection matrix** (compact: engine → best for → hardware) and **VRAM sizing rule** (`VRAM_GB ≈ params_B × bpw/8 × 1.2` + KV cache; ~0.6 GB/B at Q4; tiers 8/16/24/48/80GB+).
  - **Local-model wiring gist** — Ollama `/v1` for OpenAI-shaped tools; LiteLLM proxy + `ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN` for Anthropic-API tools.
  - See also (name-only). ≤ 500 lines.

- [ ] **Step 3: `agents/openai.yaml`**

```yaml
interface:
  display_name: "Linux AI Dev Stack"
  short_description: "Install the local and cloud AI dev stack"
  default_prompt: "Use $linux-ai-dev-stack to install and wire the AI toolchain on Linux: local LLM inference (Ollama/llama.cpp/vLLM) with VRAM-based model choice, AI coding agents plus MCP servers, ML frameworks and GPU containers, and cloud/remote GPU workflows."
policy:
  allow_implicit_invocation: true
```
(short_description "Install the local and cloud AI dev stack" = 40 chars.)

- [ ] **Step 4: Reference files**
  - `local-llm-inference.md` (from `04-local-llm-inference.md`) — engine picks (Ollama/llama.cpp/vLLM/SGLang/ExLlamaV3+TabbyAPI/LM Studio/mlc-llm), quantization formats, model-size→VRAM table + tiered model recs, systemd service, safe LAN exposure, tuning (flash-attn, KV quant, offload, speculative decoding), tok/s ballparks.
  - `ai-coding-agents.md` (from `05-ai-coding-agents.md`) — Claude Code/Codex/aider/OpenCode/Gemini CLI install+auth+config; editor AI; sandboxing + git worktrees; permission modes; `AGENTS.md` standard (+ `CLAUDE.md` symlink).
  - `mcp-servers.md` — MCP explained; essentials (filesystem, git, github, context7, playwright, memory, fetch, sequential-thinking); scopes (`.mcp.json` vs user config); prompt-injection/least-privilege security.
  - `model-wiring.md` — cloud keys (secure storage) + local endpoints; LiteLLM proxy config; cost/model routing (triage→build→review).
  - `ml-frameworks.md` — uv/pixi Python env; PyTorch/JAX/TF with CUDA/ROCm/XPU; Jupyter; HuggingFace stack; GPU containers (NVIDIA Container Toolkit, rootless, CDI).
  - `remote-gpu.md` — providers (RunPod/Vast/Lambda/Modal), remote dev (VS Code Remote-SSH, Zed remote, mosh, tmux), sync (mutagen + rsync), networking (Tailscale/cloudflared), cost tips.

- [ ] **Step 5: Templates + example**
  - `templates/AGENTS.md` — starter cross-tool agent instructions + a comment noting `ln -s AGENTS.md CLAUDE.md`.
  - `templates/litellm-config.yaml` — valid YAML routing local + cloud models (Anthropic-named alias → local).
  - `templates/gpu-compose.yaml` — valid Compose file with NVIDIA GPU reservation for an inference service.
  - `examples/24gb-nvidia-local-plus-cloud.md` — worked setup on a 24GB NVIDIA box.

- [ ] **Step 6: `references/activation.md`** — best-fit, explicit invocation, when NOT to use (no drivers yet → `linux-dev-workstation`; picking a distro → `linux-distro-selector`), cross-agent notes.

- [ ] **Step 7: Validate** — `python3 scripts/validate_skills.py`; confirm SKILL.md < 500 lines.

- [ ] **Step 8: Commit**

```bash
git add linux-ai-dev-stack
git commit -m "feat(linux-ai-dev-stack): add AI toolchain (local LLM, agents, MCP, remote GPU) skill"
```

---

## Task 5: Integrate — cross-links, README index, full validation

**Files:**
- Modify: `README.md` (skill index/table — add the 4 new skills)
- Verify: all four skills cross-reference siblings by name in `SKILL.md` "See also" + `references/activation.md` "when NOT to use".

- [ ] **Step 1:** Confirm each SKILL.md "See also" and each activation.md name-references the other three siblings (grep for the names). Fix any missing.

- [ ] **Step 2:** Add the suite to `README.md` in the same style as existing entries (name, one-line description, when-to-use). Group them as "Linux Environment" if the README uses category groupings.

- [ ] **Step 3: Full validation**

Run: `python3 scripts/validate_skills.py`
Expected: "Validated N skills successfully." (N = prior count + 4), zero errors.

- [ ] **Step 4: Line-count + hygiene check**

Run: `for s in linux-distro-selector linux-install-planner linux-dev-workstation linux-ai-dev-stack; do wc -l "$s/SKILL.md"; done`
Expected: each ≤ 500. Also `grep -rn "TODO\|TBD\|FIXME" linux-*/` returns nothing; no `.bak`/`.tmp` files; no hardcoded home paths (`grep -rn "/Users/\|/home/[a-z]" linux-*/ || true` — only generic examples, no real usernames).

- [ ] **Step 5: Commit**

```bash
git add README.md linux-distro-selector linux-install-planner linux-dev-workstation linux-ai-dev-stack
git commit -m "feat(linux-ai-dev-environment): cross-link suite and add to README index"
```

---

## Self-Review (completed during planning)

- **Spec coverage:** Every spec §5 skill and reference file maps to a task step above (Tasks 1–4). Cross-cutting principles (§4) encoded in Global Constraints + each SKILL.md mode banner/safety protocol. §6 conventions → Global Constraints + validate gate. §7 build sequence → Tasks 1–5. §8 success criteria → the four skills' How-to sections + examples.
- **Added requirements** (Rust/Python/Ruby/JS-TS toolchains, Docker, advanced editor config) → Task 3 `language-toolchains.md`, `containers.md`, `editors.md`, and `mise.toml`/`tmux.conf`/`devcontainer.json` templates.
- **Placeholder scan:** frontmatter + openai.yaml given verbatim; reference files specified by concrete section + sourced facts (content is prose authored from the research files, not code). No "TBD".
- **Consistency:** skill names identical across all tasks and cross-refs; `opensite-category` = `setup` (1–3) / `ai` (4); every `short_description` length pre-verified 25–64; every `default_prompt` contains its `$name`.
