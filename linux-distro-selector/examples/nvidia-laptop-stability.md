# Worked Example — NVIDIA Laptop, Wants Stability + Recent CUDA

A worked walk-through of the advisory flow. Versions are **as of 2026-07 — verify**
at runtime before presenting them to the user.

---

## User request

> "I just got a Lenovo Legion laptop with an RTX 4070 (mobile). I'm an AI/ML
> engineer. I want the machine to be **stable and low-maintenance**, but I also
> need **reasonably recent CUDA and PyTorch**. What Linux distro should I install?"

## Step 1 — Elicit primary optimization + constraints

Filled from [../templates/hardware-intake-worksheet.md](../templates/hardware-intake-worksheet.md):

- **Primary optimization:** never-breaks / low-maintenance — but with a hard secondary
  requirement for recent CUDA/PyTorch. Tie-break axis leans toward *stability*, with
  freshness delivered through tools, not the OS.
- **GPU:** NVIDIA RTX 4070 mobile (Ada / Ampere-successor, i.e. **Turing+** → open kernel
  modules are the default). Compute needed (CUDA + PyTorch).
- **Form factor:** laptop, almost certainly **NVIDIA Optimus** hybrid (Intel iGPU + NVIDIA dGPU).
- **Wi-Fi:** Intel AX-series (smooth, in-kernel) — no wired-install flag.
- **Secure Boot:** user wants to keep it on, does not want to manage keys.
- **Container comfort:** yes, comfortable doing dev in containers.

## Step 2 — Triage the hardware

Against [../references/hardware-compat-triage.md](../references/hardware-compat-triage.md):

- **NVIDIA laptop → Optimus/PRIME handling required.** Favor a distro that smooths this over.
- **Secure Boot on + no key management → out-of-box shim distro** (rules out Arch/CachyOS
  unless they accept `sbctl`).
- **Turing+ GPU** → open kernel modules; Wayland + NVIDIA is daily-usable on the 5xx/59x driver
  series. No X11-only pro tools mentioned, so Wayland is fine.
- Wi-Fi and battery: `power-profiles-daemon`/`tuned` available on the leading candidates.

## Step 3 — Walk the decision tree

From SKILL.md: "never break" + "NVIDIA laptop" + "comfortable with containers" points to two
branches — the **atomic** path and the **stable-LTS-with-fresh-tools** path. Both satisfy
"stable host, recent CUDA via tools/containers."

## Step 4 — Recommendation

**Primary pick: Bluefin (Universal Blue, NVIDIA image)** — atomic Fedora-based dev workstation.
- **Rationale:** immutable host that can't be broken by a bad driver/update (roll back at boot in
  seconds), NVIDIA + Optimus handled by the dedicated ublue nvidia image, Secure Boot works out of
  the box, and all bleeding-edge CUDA/PyTorch work happens in **distrobox** (e.g. a CUDA container)
  so the host stays pristine. Best "stable + fresh dev" combination for this user.
- **Biggest trade-off:** you do GPU/ML dev inside containers, not on the bare host — a small
  mental-model shift, and occasional friction with tools that expect a mutable FHS root.

**Alternative: Ubuntu 26.04 LTS** — traditional mutable system.
- **When to prefer it:** if the user wants a conventional, widely-documented system that matches
  cloud/CI images, or dislikes container-first dev. Ubuntu 26.04 now ships **NVIDIA CUDA natively
  in its repos** with signed Secure Boot support and `ubuntu-drivers`, so recent CUDA is one command
  away; pull newer PyTorch via `uv`/`pixi` or containers. Trade-off: a mutable host is easier to
  break than an atomic one, and you handle Optimus via `prime-select` yourself.

Also viable: **Pop!_OS 24.04** (System76-tuned NVIDIA + tiling) or **Bazzite** (NVIDIA + Mesa
pre-installed) if the user wants the absolute least NVIDIA setup effort.

## Step 5 — Verify + hand off

- **Verify** the current Bluefin nvidia image tag, Ubuntu 26.04 support window, and the current
  NVIDIA driver series for the RTX 4070 with a quick web search before finalizing.
- **Next step:** hand the confirmed hardware profile (NVIDIA RTX 4070 mobile, Optimus, Intel Wi-Fi,
  Secure Boot on) to the `linux-install-planner` skill to generate the install runbook, then use
  `linux-dev-workstation` to configure the NVIDIA/PRIME drivers, and `linux-ai-dev-stack` for the
  local + cloud AI toolchain.
