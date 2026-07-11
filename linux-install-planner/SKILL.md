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
# Linux Install Planner

> **MODE — PLANNER (you are NOT on the target machine).** Emit a numbered
> runbook for a human sitting at the computer. You cannot see their disks, run
> `lsblk`, flash a USB, or reboot for them. Never phrase a step as if you will
> run it — write "You will…", "Confirm that…", "Type this at the machine…".
> Every destructive step (flash, wipe, partition, RST/AHCI switch) must tell the
> human exactly what to verify with their own eyes before they proceed.

> **CURRENCY GUARDRAIL.** Distro releases and tool versions move fast. Every
> version in this skill is labeled "as of 2026-07 — verify." Before handing over
> a runbook, web-search the current stable release of the chosen distro and the
> current version of the writer tool, and correct any drift.

## Skill Resources
- Activation, when-NOT-to-use, cross-agent notes: [references/activation.md](references/activation.md)
- Phase 2 — bootable media, checksum + GPG verify: [references/bootable-media.md](references/bootable-media.md)
- Phase 3 — UEFI, Secure Boot, Fast Startup, BitLocker, Intel RST, TPM: [references/uefi-secureboot.md](references/uefi-secureboot.md)
- Phase 4 — GPT layout, filesystems, swap, LUKS2, snapshots: [references/partitioning-encryption.md](references/partitioning-encryption.md)
- Phase 6 — first-boot checklist: [references/first-boot-checklist.md](references/first-boot-checklist.md)
- Phase 7 — laptop pain points and fixes: [references/laptop-fixes.md](references/laptop-fixes.md)
- Fill-in runbook skeleton to hand the user: [templates/install-runbook.md](templates/install-runbook.md)
- Worked end-to-end example: [examples/dell-xps-full-wipe-ubuntu.md](examples/dell-xps-full-wipe-ubuntu.md)

---

## ⚠️ DANGER CHECKLIST — put these AT THE TOP of every runbook you emit

State these five before any other step. Each one, done wrong, causes permanent
data loss or an unbootable machine. Do not let the human skip them.

1. **Verified backup, including the OEM recovery partition.** A full wipe (and
   even a dual-boot resize) can destroy every file plus the hidden factory
   recovery partition. Copy personal data to an external drive **and** cloud,
   then open the copy and confirm the files are really there. Also create
   **Windows recovery media** first (`Settings → System → Recovery`, or search
   "recovery drive"; needs a 16–32 GB USB) if Windows might ever be wanted back.
2. **BitLocker: suspend or decrypt, and save the recovery key.** Windows 11
   often enables device encryption by default. An encrypted disk looks like
   random noise, so "Install alongside Windows" cannot safely resize it. For
   dual-boot, turn BitLocker off (`Control Panel → BitLocker → Turn off`, full
   decrypt is safest) first. **Always** save the recovery key (Microsoft account
   or printout) — changing Secure Boot/TPM can trigger a recovery prompt.
3. **Intel RST / RAID / "VMD" storage mode → AHCI caveat.** If the installer
   shows **no disks**, the SATA/NVMe controller is in RST/RAID/VMD mode. Modern
   kernels usually detect NVMe under VMD — try first. If you must switch to
   AHCI while **keeping** Windows, do the `bcdedit /set {current} safeboot
   minimal` → switch → boot → `bcdedit /deletevalue {current} safeboot` dance,
   or Windows blue-screens `INACCESSIBLE_BOOT_DEVICE`. Full wipe: switch freely.
4. **Disable Fast Startup, then truly Shut Down (not Restart).** In an admin
   prompt: `powercfg /H off` (disables Fast Startup and hibernation). Then pick
   **Shut down** — a Restart does **not** clear the hibernated/"dirty" state that
   corrupts shared filesystems and breaks dual-boot.
5. **Confirm the correct target disk before flashing or wiping.** `dd
   of=/dev/sdX` or a writer pointed at the internal disk is instant catastrophe.
   Have the human run `lsblk` (Linux/macOS) and match size/model **before** they
   confirm, and remind them `/dev/sdX` here is a placeholder they must replace.

Honorable mentions to carry into the runbook: NVIDIA + Secure Boot needs a blue
**MOK enrollment** screen on next boot; never run two power managers at once;
s2idle "hot bag" battery drain is usually fixed by a BIOS update; back up the
**LUKS header** — a corrupted header means unrecoverable data.

---

## The 8-phase playbook

Build the runbook in this order. Each phase links to the reference that carries
the exact commands and per-installer notes. Keep the numbering in the handed-over
runbook so the human never loses their place.

- **Phase 0 — Decide the end state.** Full wipe (Linux only) vs dual-boot;
  encryption yes/no (default **yes** on laptops); which distro (pull from the
  `linux-distro-selector` skill's recommendation). Full wipe avoids ~80% of the
  footguns below — recommend it unless there is a hard Windows dependency.
- **Phase 1 — Pre-flight.** Verified backup + Windows recovery media (Danger #1);
  record the OEM product key (`(Get-CimInstance -ClassName
  SoftwareLicensingService).OA3xOriginalProductKey`; blank = digital license,
  normal); hardware recon from inside Windows (`msinfo32`, Device Manager — note
  dual GPUs, Wi-Fi chipset, storage soldered vs M.2, RST-vs-AHCI, fingerprint/IR
  webcam); update BIOS/UEFI from the vendor tool **while still on Windows**.
- **Phase 2 — Bootable media.** Verify the ISO first (checksum **and** GPG),
  then write it. Default to Ventoy; balenaEtcher for the simplest path; Rufus for
  Windows-only control; `dd` for terminal users. See
  [references/bootable-media.md](references/bootable-media.md).
- **Phase 3 — UEFI/BIOS + Windows prep (highest-footgun phase).** Fast Startup
  off + true shutdown; BitLocker suspend/decrypt + key saved; enter firmware
  (F2/Del/F10/Esc, varies); Secure Boot keep-vs-disable; Intel RST/VMD → AHCI;
  leave TPM 2.0 on. See [references/uefi-secureboot.md](references/uefi-secureboot.md).
- **Phase 4 — Partitioning, filesystems, LUKS.** GPT with ESP + root (+ optional
  `/home`); ext4 (simple) vs btrfs (snapshots — recommended for a dev box) vs zfs
  (advanced); zram vs swap partition (swap ≥ RAM only if hibernating); LUKS2
  full-disk encryption; btrfs snapshot setup. See
  [references/partitioning-encryption.md](references/partitioning-encryption.md).
- **Phase 5 — Installer walkthrough.** Boot the USB via the one-time boot menu →
  **Try** the live session first to sanity-check Wi-Fi/trackpad/display →
  connect network → language/keyboard/timezone → check "third-party software"
  (Ubuntu) or plan RPM Fusion (Fedora) → pick install type (Erase / Alongside /
  Manual) with Encrypt → set a **real hostname** → install → remove USB → reboot.
  Arch uses `archinstall` (mention only; not a first migration).
- **Phase 6 — First-boot checklist.** Full update; trigger driver install;
  `fwupdmgr` firmware; Flatpak/Flathub (+ RPM Fusion on Fedora); pick **exactly
  one** power manager; set hostname/timezone/locale; enroll fingerprint if
  supported. See [references/first-boot-checklist.md](references/first-boot-checklist.md).
- **Phase 7 — Laptop pain points.** NVIDIA Optimus/PRIME, Wi-Fi firmware
  (Broadcom/Realtek), battery, S3-vs-s2idle suspend, HiDPI/Wayland. See
  [references/laptop-fixes.md](references/laptop-fixes.md).
- **Phase 8 — Reversibility.** Keep Windows recovery media + the install USB as a
  rescue environment; back up the LUKS header (`cryptsetup luksHeaderBackup`);
  don't casually toggle RST↔AHCI or Secure Boot/TPM after install; test the live
  session every time before committing.

---

## How to produce the runbook

1. **Gather three inputs.** (a) The **distro** — normally the output of the
   `linux-distro-selector` skill; if the user hasn't chosen, point them there
   first. (b) The **machine** — make/model, CPU, GPU(s), Wi-Fi chipset,
   storage layout, laptop vs desktop. (c) **Wipe vs dual-boot** and
   **encryption** preference (Phase 0).
2. **Web-search to refresh versions.** Confirm the current stable release of the
   chosen distro and the current writer-tool version; correct any "as of 2026-07"
   numbers before writing.
3. **Fill the template.** Copy [templates/install-runbook.md](templates/install-runbook.md)
   and personalize every `{{placeholder}}` — target disk, distro, filesystem,
   encryption choice, and the machine-specific laptop fixes from Phase 7.
4. **Lead with the danger checklist**, then hand the runbook over **phase by
   phase**. Tell the human to complete and confirm each phase before you (or
   they) move to the next; pause at every destructive step.
5. **Point forward.** After first boot succeeds, tell them to switch to the
   `linux-dev-workstation` skill to configure the dev environment, then
   `linux-ai-dev-stack` for the AI toolchain.

Use [examples/dell-xps-full-wipe-ubuntu.md](examples/dell-xps-full-wipe-ubuntu.md)
as a model of the finished output.

---

## Verified current versions (as of 2026-07 — verify)

| Thing | Current | Note |
|---|---|---|
| Ubuntu LTS | 26.04 LTS (2026-04-23) | 24.04.x LTS supported to 2029 (ESM 2036). |
| Fedora Workstation | 44 (Apr 2026); 43 still supported | DNF5, Anaconda; NVIDIA Wayland-first. |
| Pop!_OS | COSMIC era (~1.0) | NVIDIA ISO ships drivers preinstalled. |
| Ventoy | 1.1.16 (2026-06-25) | Multi-ISO USB; Secure Boot key enroll. |
| Rufus | 4.15 (2026-06-30) | Windows-only writer. |
| balenaEtcher | ~v2.x, maintained | Cross-platform; auto-verifies the write. |

---

## See also

- `linux-distro-selector` — run **before** this skill to pick the distro and
  confirm the hardware will work.
- `linux-dev-workstation` — run **after** first boot to configure drivers, shell,
  editors, language toolchains, containers, and security.
- `linux-ai-dev-stack` — run after the workstation is set up to install the local
  and cloud AI toolchain.
