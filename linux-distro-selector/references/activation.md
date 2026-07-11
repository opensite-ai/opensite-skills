# Activation Guide — linux-distro-selector

## Best-Fit Tasks

Use this skill when the goal is to **decide which Linux distribution to install**
and to **confirm the target hardware will work** — before any installer runs:

- "Which Linux distro should I use for AI/ML development?"
- Comparing Ubuntu vs Fedora vs Arch vs NixOS vs Pop!_OS vs Mint vs atomic/immutable distros.
- Switching from Windows or macOS and unsure what to install.
- Matching a distro to a use case: maximum stability, bleeding-edge GPU/AI work,
  byte-for-byte reproducibility, laptop battery life, or a homelab/server.
- "Will my GPU / Wi-Fi chipset / laptop work on Linux?" hardware-compatibility triage.
- Deciding between rolling, LTS/point-release, and atomic/immutable models.

This is an **advisory** skill: it outputs a recommendation with rationale and the
top trade-off. It does not create bootable media, partition disks, or install anything.

## Explicit Invocation

### Claude Code
```
/linux-distro-selector help me pick a distro for an RTX 4090 desktop, I want the newest CUDA
```
```
@linux-distro-selector will a Broadcom Wi-Fi ThinkPad work on Fedora?
```

### Codex
```
Use $linux-distro-selector to choose a distro for a reproducible fleet of dev laptops
```

### Cursor / Copilot / OpenCode
```
/linux-distro-selector
```
Then describe the hardware, primary optimization, and constraints on the next line.

### Perplexity Computer / Claude Desktop (cloud skills)
Upload this skill to the platform's skills page. Once active, prompts like
"which Linux distro should I install", "compare Ubuntu and Fedora for AI dev", or
"will my GPU work on Linux" auto-activate it (implicit invocation is enabled).

## When NOT to Use — hand off to a sibling

- **The distro is already chosen and the user needs to install it** →
  use `linux-install-planner` (bootable media, UEFI/Secure Boot, BitLocker/Intel RST,
  partitioning + LUKS, installer walkthrough, first boot).
- **Linux is already installed and needs configuring** (GPU drivers, shell,
  editors, language toolchains, containers, security) → use `linux-dev-workstation`.
- **The base dev box exists and the user wants the AI toolchain** (local LLM
  inference, AI coding agents + MCP, ML frameworks, remote GPU) → use `linux-ai-dev-stack`.
- **The target is not Linux** (Windows/macOS-native setup) → out of scope for this suite.

## Cross-Agent Notes

- Works with no machine access — it is safe to run from any agent, including
  cloud assistants, because it only produces a recommendation.
- A **web search tool is strongly recommended**: distro releases, support windows,
  and GPU/kernel support change frequently. Verify embedded version numbers
  (labeled "as of 2026-07 — verify") before presenting them as current.
- Deterministic output: return a primary pick + one alternative, each with a
  one-line rationale and the single biggest trade-off, then point to
  `linux-install-planner` for next steps.
