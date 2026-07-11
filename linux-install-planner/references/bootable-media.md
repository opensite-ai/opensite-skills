# Reference — Phase 2: Bootable Install Media

> Planner note: these are commands **the human runs at their own machine**. Every
> version is "as of 2026-07 — verify" before you hand it over.

A corrupted or tampered ISO wastes hours or is a real security risk. **Verify the
ISO before writing it**, then flash the correct USB stick. Never skip verification
and never assume the target device path — always confirm it.

---

## 2.1 Verify the ISO FIRST (two independent checks)

Do both. The checksum proves the download is intact; the GPG signature proves the
checksum list itself is authentic (not swapped by a mirror or MITM).

### Integrity — checksum

- **Linux/macOS:** `sha256sum ubuntu-26.04-desktop-amd64.iso` and compare the
  output to the published `SHA256SUMS`.
- **Windows (PowerShell):** `Get-FileHash .\ubuntu-26.04-desktop-amd64.iso -Algorithm SHA256`
  and compare the `Hash` value.

### Authenticity — GPG signature (Ubuntu's documented flow)

Download `SHA256SUMS` and `SHA256SUMS.gpg` from the **same mirror directory** as
the ISO, then:

```bash
# Import the Ubuntu image-signing key
gpg --keyid-format long --keyserver hkp://keyserver.ubuntu.com \
    --recv-keys 0x843938DF228D22F7B3742BC0D94AA3F0EFE21092

# The signature over the checksum file must say "Good signature"
gpg --verify SHA256SUMS.gpg SHA256SUMS

# Verify the ISO against the now-trusted checksum list
sha256sum -c SHA256SUMS 2>&1 | grep OK
```

- **Fedora:** the `*-CHECKSUM` files are GPG-signed. `curl -O` the Fedora GPG
  keys, then verify with `gpgv` (or import + `gpg --verify`) and `sha256sum -c`.
  **Fedora Media Writer verifies automatically** — prefer it for Fedora.
- **Pop!_OS / others:** follow the vendor's published checksum page; if only a
  checksum (no signature) is offered, at minimum match the SHA256 over HTTPS from
  the official domain.

Only proceed to writing once both checks pass.

---

## 2.2 Choose the writer

| Tool | Version (verify) | Platform | Best for | Notes |
|---|---|---|---|---|
| **Ventoy** | 1.1.16 | Windows / Linux | **Default.** Drop many ISOs on one USB, no re-flash | Installs a bootloader once; copy `.iso` files onto the exposed FAT/exFAT partition. Supports Secure Boot (one-time key enroll on first boot). Non-destructive updates. Great for trying multiple distros. |
| **Rufus** | 4.15 | Windows only | Single ISO, maximum control | Use **"DD Image" mode** if prompted (byte-for-byte, safest for hybrid Linux ISOs); "ISO mode" works for most. Can also make Windows install media. |
| **balenaEtcher** | ~v2.x | Win / macOS / Linux | Simplest cross-platform; **auto-verifies** | Flashes one ISO and wipes the USB. Best for a non-technical user. |
| **`dd`** | n/a | Linux / macOS | Terminal purists | No verification of its own — add `conv=fsync`. **Triple-check the target.** |

**Selection guidance for the runbook:** default to **Ventoy** (the user keeps the
stick and can try Ubuntu, Pop!_OS, and Fedora without re-flashing). Fall back to
**balenaEtcher** for the "just make it work" persona, **Rufus** for Windows-only +
control, `dd` only for confident terminal users.

---

## 2.3 Ventoy walkthrough (recommended default)

1. Download Ventoy for the host OS (Windows or Linux) from the official site.
2. Insert the USB (≥ 8 GB; **all data on it will be erased** by the Ventoy
   install step). Confirm which device it is before continuing.
3. Run `Ventoy2Disk` (Windows GUI) or `sudo ./Ventoy2Disk.sh -i /dev/sdX`
   (Linux) — **replace `/dev/sdX` with the USB device**, verified via `lsblk`.
4. After install, Ventoy exposes a large FAT/exFAT partition. **Copy** the
   verified `.iso` file(s) onto it with a normal file copy — no flashing.
5. Boot the machine from the USB; Ventoy shows a menu of the ISOs present. If
   Secure Boot is on, the first boot may prompt a one-time key enrollment.

---

## 2.4 `dd` walkthrough (advanced, no safety net)

```bash
lsblk                       # identify the USB by size/model FIRST
sudo dd if=distro.iso of=/dev/sdX bs=4M status=progress oflag=sync conv=fsync
```

- `/dev/sdX` is a **placeholder** — replace it with the USB device (e.g. the
  8/16/32 GB removable disk from `lsblk`), **never** a partition like
  `/dev/sdX1`, and **never** the internal disk.
- Pointing `dd` at the internal drive is instant, unrecoverable destruction. Have
  the human read the `lsblk` output back before confirming.
- `dd` does not verify; the `oflag=sync`/`conv=fsync` flags flush writes. To spot
  a bad write, re-read the device and compare its checksum, or use a verifying
  tool (Etcher) instead.

---

## 2.5 Distro-specific writers

- **Fedora Media Writer** downloads + verifies + writes in one step — the
  preferred path for Fedora; it removes the manual checksum/GPG steps.
- **Pop!_OS** ships a standard ISO (and a separate **NVIDIA ISO** with drivers
  preinstalled — use it for NVIDIA laptops); write it with Ventoy/Etcher/Rufus.

---

## Sources (authoritative)
- Ventoy official docs (ventoy.net) — usage, Secure Boot, checksum, non-destructive install (1.1.16, 2026-06-25)
- Rufus official site (rufus.ie) — 4.15 (2026-06-30), ISO/DD mode
- Ubuntu: "How to verify your Ubuntu download" (GPG + sha256)
- Fedora Project docs / Fedora Media Writer
- System76: "Installing Pop!_OS"
