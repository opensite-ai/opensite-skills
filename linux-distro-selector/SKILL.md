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
# Linux Distro Selector

> **Mode: Advisory — output a recommendation, not commands.** This skill never
> flashes media, partitions disks, or runs installers. It gathers requirements,
> walks a decision tree, and returns 1–2 recommended distributions with the
> rationale and top trade-off. When the user is ready to install, hand off to the
> `linux-install-planner` skill.

> **Currency guardrail:** Distro releases and hardware support move fast. Embedded
> versions are labeled "as of 2026-07 — verify." Before committing the user to a
> distro, run a web search to confirm the current stable release, its support
> window, and GPU/kernel support for their exact hardware.

## Skill Resources
- Activation, explicit invocation, and cross-agent notes: [references/activation.md](references/activation.md)
- Full distro matrix with per-distro ratings: [references/distro-matrix.md](references/distro-matrix.md)
- "Will my hardware work?" triage (GPU/Wi-Fi/Secure Boot/Wayland): [references/hardware-compat-triage.md](references/hardware-compat-triage.md)
- Atomic vs traditional, rolling vs LTS trade-offs: [references/atomic-vs-traditional.md](references/atomic-vs-traditional.md)
- Intake worksheet (inputs → recommendation): [templates/hardware-intake-worksheet.md](templates/hardware-intake-worksheet.md)
- Worked example (NVIDIA laptop, wants stability + recent CUDA): [examples/nvidia-laptop-stability.md](examples/nvidia-laptop-stability.md)

## How to use

1. **Elicit the primary optimization + constraints.** Ask the intake questions
   below (or fill [templates/hardware-intake-worksheet.md](templates/hardware-intake-worksheet.md)).
   The single most important axis is: *how much does the user value newest
   toolchains/GPU drivers vs. how much do they value never spending time on
   maintenance?* In 2026 atomic-plus-containers lets them get much of both.
2. **Triage the hardware.** Check GPU vendor, Wi-Fi chipset, laptop vs desktop,
   and Secure Boot needs against [references/hardware-compat-triage.md](references/hardware-compat-triage.md).
   Flag anything (Broadcom Wi-Fi, very new laptop silicon, NVIDIA Optimus) that
   should push the choice.
3. **Walk the decision tree** (below) to 1–2 candidate distros.
4. **Return the recommendation.** Give a primary pick + one alternative, each
   with a one-line rationale and the single biggest trade-off. Then point the
   user to the `linux-install-planner` skill to generate the install runbook, and
   to `linux-dev-workstation` once the OS is up.

Verify current releases with a web search before finalizing — do not present an
embedded version number as authoritative.

## Decision tree

```
START: What do you optimize for?
│
├─ "It must never break; I don't want to think about my OS"
│   ├─ Comfortable doing dev inside containers (distrobox/toolbx)?
│   │        └─ YES → Bluefin / Aurora / Fedora Silverblue-Kinoite (atomic) + distrobox
│   └─ Want a traditional mutable system? → Ubuntu 26.04 LTS  (Debian 13 for servers)
│
├─ "I need the newest kernel / GPU driver / CUDA ASAP"
│   ├─ Want a rollback safety net + a tuned fast kernel? → CachyOS (Btrfs + Snapper)
│   ├─ Want openQA-tested rolling?                       → openSUSE Tumbleweed
│   ├─ Want near-vanilla Arch?                           → EndeavourOS / Arch
│   └─ Fresh but on a 6-month tested cycle?              → Fedora Workstation
│
├─ "Every machine must be byte-identical / reproducible"
│   ├─ Whole OS declarative (accept the steep curve)?    → NixOS
│   └─ Just reproducible dev envs?                       → Fedora atomic + distrobox / devcontainers
│
├─ "It's a laptop; battery + hardware just working matters most"
│   ├─ Latest Intel/AMD silicon?                         → Fedora Workstation  (or Bluefin)
│   └─ NVIDIA laptop?                                    → Pop!_OS / Bazzite / Bluefin-nvidia
│
├─ "I'm switching from Windows / want low friction"       → Linux Mint  (alt: Pop!_OS, Aurora)
│
└─ "Server / homelab / self-hosted models"
    ├─ Maximum stability & minimalism?                   → Debian 13
    ├─ Cloud/CI parity?                                  → Ubuntu Server LTS
    └─ Atomic/container host?                            → uCore / Fedora CoreOS  (Proxmox to virtualize)
```

## Compact comparison matrix

Versions as of 2026-07 — verify. Full ratings and notes:
[references/distro-matrix.md](references/distro-matrix.md).

| Distro | Model | Driver/GPU ease | Stability | Reproducibility | Best for |
|---|---|---|---|---|---|
| Ubuntu 26.04 LTS | Point/LTS | Easy (native CUDA/ROCm, signed) | High | Low | Production parity, AI infra, teams |
| Debian 13 | Point/LTS | Medium (non-free repo) | Highest | Low | Servers, homelab, minimalists |
| Fedora Workstation | Point | Medium (RPM Fusion akmod) | High | Low | Laptops, upstream dev, Wayland |
| Bluefin / Aurora (Universal Blue) | Atomic | Easy (nvidia images) | Highest (rollback) | High (image + containers) | "Just works" dev host |
| CachyOS | Rolling | Easy (DKMS + tooling) | Medium (Snapper) | Low | Bleeding-edge AI/GPU power users |
| NixOS | Declarative/atomic | Medium (config option) | Highest (reproducible) | Highest | Fleets, reproducibility obsessives |
| openSUSE Tumbleweed | Rolling | Medium | High (openQA + Snapper) | Low | Sane rolling |
| Linux Mint | Point/LTS | Easy (Driver Manager) | High | Low | Windows switchers, beginners |

## Intake questions

Ask these (or use [templates/hardware-intake-worksheet.md](templates/hardware-intake-worksheet.md)):

1. **Primary optimization?** never-breaks / bleeding-edge GPU-AI / byte-reproducibility / laptop-just-works / Windows-switcher / homelab-server.
2. **GPU vendor + model?** NVIDIA (which series), AMD, Intel Arc, Apple Silicon, or integrated/CPU-only. This is often the deciding factor — see [references/hardware-compat-triage.md](references/hardware-compat-triage.md).
3. **Laptop or desktop?** If laptop: make/model, and is it a hybrid NVIDIA Optimus setup? Very new silicon needs a recent kernel.
4. **Wi-Fi chipset?** Broadcom and some Realtek parts need out-of-tree firmware — flag early.
5. **Experience level + tolerance for maintenance?** Comfortable in a terminal / doing dev inside containers / willing to learn Nix?
6. **Constraints?** Secure Boot must stay on, production/cloud parity required, multiple machines to keep identical, offline install, etc.

## See also

- `linux-install-planner` — once a distro is chosen, generates the safe Windows→Linux install + first-boot runbook.
- `linux-dev-workstation` — after first boot, configures GPU drivers, shell, editors, language toolchains, containers, and security.
- `linux-ai-dev-stack` — installs the AI toolchain (local LLM inference, AI coding agents + MCP, ML frameworks, remote GPU).
