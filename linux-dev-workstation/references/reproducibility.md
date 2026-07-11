# Reproducibility / Declarative Setup

Blend a fast imperative layer with a declarative backbone so the next machine is
one command. Building blocks + a decision matrix. Versions "as of 2026-07 — verify."

## 1. Dotfiles: chezmoi vs Stow vs bare git

- **chezmoi** (Go, single binary, ~2.71.x) — **recommended for most.**
  Cross-machine templating (Go templates for OS/host differences), secrets via
  age/gpg or a password manager, `run_` setup scripts, file encryption. Bootstrap
  a fresh box in one line:
  ```bash
  sh -c "$(curl -fsLS https://get.chezmoi.io)" -- init --apply <github-user>
  chezmoi update    # pull + re-apply later
  ```
  See the recommended repo layout in
  [../templates/chezmoi-layout.md](../templates/chezmoi-layout.md).
- **GNU Stow** — dead-simple symlink farm; your repo mirrors `$HOME`,
  `stow <pkg>` symlinks it. No templating/secrets. Great when dotfiles are
  identical across machines and you want zero magic.
- **Bare git repo** (`git --git-dir=$HOME/.dotfiles --work-tree=$HOME`) — no
  extra tools, files live in place; no templating/secrets, easy to commit junk.
- **Recommendation:** chezmoi for a senior with multiple machines + secrets; Stow
  for the simplest transparent approach on homogeneous machines.

## 2. Ansible for machine provisioning

The best imperative-but-repeatable layer for installing packages, configuring the
OS, and bootstrapping a workstation across Ubuntu/Fedora/Arch. Idempotent,
agentless (SSH), readable YAML. Pairs perfectly with chezmoi (Ansible = system +
packages; chezmoi = user dotfiles). See
[../templates/ansible-workstation.yml](../templates/ansible-workstation.yml).

Recommended layout:

```
ansible/
  inventory.ini                 # localhost / remote hosts
  site.yml                      # top-level play, imports roles
  group_vars/all.yml            # package lists, versions, feature flags
  roles/
    base/       (build tools, git, curl, fonts, firewall)
    shell/      (zsh, starship, plugins, modern CLI set)
    dev/        (mise, uv, docker/podman, editors)
    security/   (ssh hardening, ufw/firewalld, auto-updates)
```

```bash
ansible-playbook -i inventory.ini site.yml --connection=local
```

Use `ansible.builtin.package` with per-distro vars, or `community.general`
modules (`flatpak`, `homebrew`, `pacman`, `dnf`).

## 3. Nix / home-manager / NixOS (the maximalist path)

Fully reproducible, pinned, rollback-able.

- **Nix on any distro** — install with the **Determinate Nix Installer**
  (`curl -fsSL https://install.determinate.systems/nix | sh -s -- install`):
  flakes on by default, reliable uninstall. (The upstream-Nix option was removed
  after Jan 1 2026; Determinate is the mainstream path.)
- **home-manager** — declarative **user environment** (dotfiles, shell, packages)
  as Nix. Works on non-NixOS Linux and macOS — declarative dotfiles + tools
  **without** replacing your distro. Track `release-26.05` or `master`.
  ```bash
  home-manager switch --flake .#youruser
  ```
- **NixOS** — the whole OS as one declarative config; atomic upgrades, rollbacks,
  strongest reproducibility (`nixos-rebuild switch --flake .`). Highest learning
  curve.
- **flakes** — pin all inputs (nixpkgs, home-manager) with `flake.lock` for
  bit-for-bit repro.

## 4. Per-project environments

- **direnv** — auto-loads/unloads env per directory via `.envrc`. Install
  regardless of stack (or use mise's native env loading).
- **mise + direnv** — lightweight, no containers, no Nix; pin a `mise.toml`.
- **devcontainers** — best for teams / mixed editors / CI parity; see
  [containers.md](containers.md).
- **Nix flakes (`nix develop`)** or **devenv.sh** — reproducible per-project
  shells for Nix users; pair with direnv (`use flake`).

## 5. Which path fits whom (recommendation matrix)

| User profile | Recommended path |
|---|---|
| Pragmatic senior, multiple machines, results fast | **chezmoi + Ansible + mise/uv** |
| Wants declarative but keeps their distro | **home-manager (flakes) + direnv** |
| Reproducibility/rollback purist | **NixOS + home-manager + flakes** |
| Team standardization / onboarding / CI parity | **devcontainers** (+ chezmoi personal layer) |
| ML researcher | **pixi** per-project + devcontainers/Docker for GPU + chezmoi dotfiles |

## Verify

```bash
chezmoi doctor
ansible --version
nix --version && home-manager --version   # if on the Nix path
direnv version
```
