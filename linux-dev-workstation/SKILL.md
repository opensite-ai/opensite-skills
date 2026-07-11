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

# Linux Dev Workstation

Configure a senior-grade Linux development environment directly on the machine —
GPU drivers, shell, editors, language toolchains, containers, reproducibility,
and security.

> **Mode: Configurator — this skill runs commands on the machine.** Follow the
> SAFETY PROTOCOL below on every stage.

## ⚠️ SAFETY PROTOCOL (read first, applies to every step)

1. **Detect first.** Never assume the distro, package manager, GPU vendor, or
   desktop. Run the detection step and branch from what you find.
2. **Make steps idempotent.** Prefer commands that are safe to re-run
   (`mise use`, `apt install`, checking "already installed" before acting).
3. **Verify after each stage.** Every stage below states a verify command. Run
   it and confirm success before moving on.
4. **Confirm before destructive/irreversible actions.** Require an explicit
   user "yes" before: disk/partition ops, driver swaps or removals, blacklisting
   kernel modules, firewall enable/rule changes (risk of locking out SSH),
   `chsh` (default-shell change), and any `rm`. State exactly what will change
   and how to undo it.
5. **Never paste secrets into the shell history or logs.** Use the secrets tools
   in [security-hardening.md](references/security-hardening.md).
6. **Currency guardrail.** Embedded version numbers are labeled
   "as of 2026-07 — verify." Verify current driver, toolchain, and package
   versions with a web search before installing.

## Skill Resources

References (load on demand for copy-pasteable depth):

- [references/activation.md](references/activation.md) — when to use this skill vs siblings.
- [references/gpu-drivers.md](references/gpu-drivers.md) — NVIDIA/AMD/Intel/Apple/CPU per-distro install + verify.
- [references/shell-terminal.md](references/shell-terminal.md) — zsh/fish, starship, modern CLI, terminals, tmux/Zellij.
- [references/editors.md](references/editors.md) — Neovim/Vim, VS Code, Zed advanced config.
- [references/language-toolchains.md](references/language-toolchains.md) — Rust/Python/Ruby/JS-TS install, pin, update, LSP.
- [references/containers.md](references/containers.md) — Docker, Podman rootless, Compose, devcontainers.
- [references/reproducibility.md](references/reproducibility.md) — chezmoi, Ansible, Nix/home-manager, decision matrix.
- [references/security-hardening.md](references/security-hardening.md) — SSH keys, commit signing, secrets, firewall, backups.

Templates:

- [templates/mise.toml](templates/mise.toml) — pins Rust/Python/Ruby/Node for a project.
- [templates/chezmoi-layout.md](templates/chezmoi-layout.md) — dotfiles repo layout.
- [templates/ansible-workstation.yml](templates/ansible-workstation.yml) — workstation provisioning playbook.
- [templates/tmux.conf](templates/tmux.conf) — senior tmux defaults.
- [templates/devcontainer.json](templates/devcontainer.json) — Dev Container sample.

Example:

- [examples/fresh-ubuntu-to-senior-devbox.md](examples/fresh-ubuntu-to-senior-devbox.md) — worked transcript.

## Step 1 — Detection (always first)

Gather the facts that drive every branch. Do not edit anything yet.

```bash
# Distro + package manager
. /etc/os-release && echo "$PRETTY_NAME"
command -v apt dnf pacman zypper 2>/dev/null   # which package manager

# GPU vendor(s)
lspci | grep -Ei 'vga|3d|display'

# Desktop session type (Wayland vs X11) and form factor
echo "$XDG_SESSION_TYPE"
ls /sys/class/power_supply/ | grep -qi bat && echo "laptop" || echo "desktop"

# Kernel + Secure Boot state (affects out-of-tree driver signing)
uname -r
mokutil --sb-state 2>/dev/null || echo "Secure Boot state unknown"
```

Record: distro/package manager, GPU vendor(s), Wayland/X11, laptop/desktop,
Secure Boot on/off. Every later stage branches on these.

## Step 2 — Ordered bring-up

Run in order; each stage is idempotent and ends with a verify command. Confirm
the verify passes before continuing.

| # | Stage | Reference | Verify command |
|---|-------|-----------|----------------|
| 1 | GPU drivers + compute | [gpu-drivers.md](references/gpu-drivers.md) | `nvidia-smi` / `rocm-smi` / `xpu-smi discovery` / `glxinfo -B` |
| 2 | Shell + terminal | [shell-terminal.md](references/shell-terminal.md) | `echo $SHELL`; `starship --version`; `rg --version` |
| 3 | Editors | [editors.md](references/editors.md) | `nvim --version`; `code --version`; `zed --version` |
| 4 | Language toolchains | [language-toolchains.md](references/language-toolchains.md) | `mise ls`; `rustc -V`; `uv --version`; `ruby -v`; `node -v` |
| 5 | Containers | [containers.md](references/containers.md) | `docker run --rm hello-world` or `podman run --rm hello-world` |
| 6 | Reproducibility | [reproducibility.md](references/reproducibility.md) | `chezmoi doctor`; `ansible --version` |
| 7 | Security hardening | [security-hardening.md](references/security-hardening.md) | `ssh-add -l`; `sudo ufw status` / `firewall-cmd --state` |

**Driver stage is the only one that is potentially destructive** (module
blacklist, DKMS, Secure Boot MOK enrollment, reboot). Treat it under the SAFETY
PROTOCOL: confirm before acting, keep X11 as a fallback, verify with `nvidia-smi`
before rebooting into a possibly-black-screen session.

After stage 7, **hand off to the `linux-ai-dev-stack` skill** for local LLM
inference, AI coding agents, MCP servers, ML frameworks, and remote GPU. This
skill only builds the base; the AI toolchain lives there and assumes the working
driver stack you just installed.

## Language toolchains quick map

Use `mise` as the meta version-manager for everything except Rust (rustup) and
Python (let `uv` own Python + envs). Full depth, LSP, and linters are in
[language-toolchains.md](references/language-toolchains.md).
Versions as of 2026-07 — verify.

| Language | Manager | Install | Per-project pin | Update |
|----------|---------|---------|-----------------|--------|
| Rust | rustup | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` | `rust-toolchain.toml` or `mise.toml` | `rustup update` |
| Python | uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `uv python pin 3.13` + `uv.lock` | `uv self update`; `uv lock --upgrade` |
| Ruby | mise | `mise use ruby@3.4` | `.tool-versions` / `mise.toml` | `mise upgrade ruby`; `bundle update` |
| Node/TS | mise | `mise use node@lts` | `.tool-versions` / `mise.toml` | `mise upgrade node`; `pnpm up` |
| (meta) | mise | `curl https://mise.run \| sh` | `mise.toml` (see template) | `mise self-update`; `mise upgrade` |

## Reproducibility decision (pick one backbone)

Capture the machine so the next one is one command. Detail + matrix in
[reproducibility.md](references/reproducibility.md).

- **Pragmatic senior, multiple machines** → **chezmoi + Ansible + mise/uv**
  (imperative-repeatable). One-liner: `sh -c "$(curl -fsLS https://get.chezmoi.io)" -- init --apply <github-user>`.
- **Declarative but keep your distro** → **home-manager (flakes) + direnv**.
  One-liner: install Determinate Nix, then `home-manager switch --flake .`.
- **Reproducibility/rollback purist** → **NixOS + home-manager + flakes**
  (`nixos-rebuild switch --flake .`).
- **Team parity / onboarding / CI** → **devcontainers** (see
  [templates/devcontainer.json](templates/devcontainer.json)) plus chezmoi for
  the personal layer.

## See also

- `linux-distro-selector` — if the distro is not chosen yet.
- `linux-install-planner` — if the OS is not installed yet (Windows→Linux).
- `linux-ai-dev-stack` — the AI toolchain (local LLM, agents, MCP, remote GPU);
  run it after this skill's driver stage succeeds.
