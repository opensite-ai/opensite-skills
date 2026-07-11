# Activation Guide

## Best-Fit Tasks
- Producing a safe, ordered runbook to **replace Windows with Linux**, **dual-boot**, or do a **clean install** on a physical machine, for a human sitting at the computer.
- Walking someone through **bootable USB media** creation with ISO checksum + GPG verification (Ventoy / Rufus / balenaEtcher / `dd`).
- Firmware/Windows prep: entering **UEFI/BIOS**, keeping-or-disabling **Secure Boot**, disabling **Fast Startup**, handling **BitLocker**, and the **Intel RST/VMD → AHCI** switch.
- **Partitioning and encryption** planning: GPT/ESP/root/home, ext4 vs btrfs vs zfs, swap vs zram, **LUKS2**, and btrfs snapshots.
- **First-boot** setup and common **laptop fixes** (NVIDIA Optimus, Wi-Fi firmware, suspend, HiDPI).
- Best trigger phrases: "give me step-by-step instructions to install Linux on my laptop", "how do I wipe Windows and put Ubuntu on this machine", "make a bootable USB and walk me through the installer".

## Explicit Invocation
- `Use $linux-install-planner to produce a full runbook to wipe Windows and install Ubuntu 26.04 LTS with LUKS on my Dell laptop — bootable media, UEFI/Secure Boot, partitioning, the installer, and first boot.`

## When NOT to Use
- The user has **not chosen a distro** or is unsure their **hardware will work** → use `linux-distro-selector` first; feed its recommendation into Phase 0 here.
- The OS is **already installed** and the user wants to configure drivers, shell, editors, language toolchains, containers, or security → use `linux-dev-workstation`.
- The user wants the **AI toolchain** (local LLM inference, AI coding agents, MCP, ML frameworks, remote GPU) → use `linux-ai-dev-stack`.
- This skill is **planner-only**: it never runs the install. If an agent is actually **on the target machine** executing commands, that is the configurator skills' territory, not this one.

## Cross-Agent Notes
- **Mode discipline is load-bearing:** this skill emits instructions for a human. An agent using it is not on the target box and must never phrase steps as if it can run them, flash a USB, or reboot the machine.
- Start with `SKILL.md` (danger checklist + 8-phase overview), then load only the phase reference the user is on. Fill `templates/install-runbook.md` and hand it over phase by phase.
- The **currency guardrail** applies: web-search the current distro release and writer-tool version before finalizing; embedded numbers are labeled "as of 2026-07 — verify."
- The standard metadata and this guide are portable across skills-compatible agents; any Claude-specific frontmatter is optional and should degrade cleanly elsewhere.
- Natural chain: `linux-distro-selector` → `linux-install-planner` → `linux-dev-workstation` → `linux-ai-dev-stack`.
