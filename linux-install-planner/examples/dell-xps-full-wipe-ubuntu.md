# Worked Example — Dell XPS, Full Wipe → Ubuntu 26.04 LTS, LUKS

A complete runbook as `linux-install-planner` would hand it over. Demonstrates
planner voice ("you will…"), the danger checklist first, and phase-by-phase
handoff. Versions are "as of 2026-07 — verify."

**Scenario.** New Dell XPS 13 (single soldered NVMe, Intel iGPU only, Intel Wi-Fi,
16 GB RAM). User wants a clean AI-dev machine, no Windows, encrypted. Distro
chosen via `linux-distro-selector`: **Ubuntu 26.04 LTS** (best laptop firmware/
driver support, huge community). Strategy: **full wipe + LUKS + btrfs**.

---

## ⚠️ Before you touch anything — DANGER CHECKLIST
1. **Back up.** Copy your files to an external drive and to cloud. Open the copy
   and confirm the files really opened. A full wipe erases everything including
   Dell's hidden recovery partition. If you might want Windows back, make Windows
   recovery media now (search "recovery drive", 16–32 GB USB).
2. **BitLocker.** Full wipe, so encryption won't block the erase — but save your
   BitLocker recovery key from your Microsoft account in case you abort.
3. **Storage mode.** Dell XPS often ships in **RAID/RST** mode. You'll check this
   in Phase 3; modern Ubuntu usually sees the NVMe anyway. Full wipe means you can
   switch straight to AHCI if needed — no `bcdedit` dance.
4. **Fast Startup.** In an admin prompt run `powercfg /H off`, then pick **Shut
   down** (not Restart).
5. **Right disk.** When you flash the USB and when you erase, you'll confirm the
   device with `lsblk` first. Your internal NVMe is the ~512 GB / 1 TB disk; the
   USB is the small removable one. Never point a writer at the internal disk.

---

## Phase 0 — End state
Full wipe (Linux only), LUKS2 encryption ON, Ubuntu 26.04 LTS, btrfs root.

## Phase 1 — Pre-flight
- You backed up and verified (above).
- Record the OEM key from PowerShell (admin):
  `(Get-CimInstance -ClassName SoftwareLicensingService).OA3xOriginalProductKey`
  — blank output is normal (digital license in firmware).
- Recon: single soldered NVMe, Intel iGPU (no NVIDIA — no MOK dance needed),
  Intel AX Wi-Fi (works on the live USB). Good, low-risk machine.
- Update the BIOS from Dell's Windows tool now.

## Phase 2 — Bootable media
- Download the Ubuntu 26.04 desktop ISO and `SHA256SUMS` + `SHA256SUMS.gpg`.
- Verify:
  ```bash
  gpg --keyid-format long --keyserver hkp://keyserver.ubuntu.com \
      --recv-keys 0x843938DF228D22F7B3742BC0D94AA3F0EFE21092
  gpg --verify SHA256SUMS.gpg SHA256SUMS        # "Good signature"
  sha256sum -c SHA256SUMS 2>&1 | grep OK
  ```
- Write with **Ventoy** (so you can also try Fedora/Pop!_OS later): install Ventoy
  to the USB (confirm the USB device via `lsblk` first — `/dev/sdX` is a
  placeholder), then copy the verified `.iso` onto Ventoy's partition.

## Phase 3 — UEFI/BIOS + Windows prep
- Already did `powercfg /H off` + Shut Down.
- Boot and tap **F2** for firmware; note **F12** for the one-time boot menu.
- **Secure Boot:** keep it **ON** — Ubuntu ships a signed shim, and there's no
  NVIDIA driver here needing MOK.
- **Storage:** if the Ubuntu installer later shows no disk, come back and set SATA
  Operation to **AHCI** (full wipe, so switch freely).
- **TPM:** leave 2.0 enabled.

## Phase 4 — Partitioning, filesystem, LUKS
- You'll use the installer's "Erase disk and install Ubuntu" + the **Encrypt**
  checkbox (LUKS2 + Argon2id) — no manual `cryptsetup` needed.
- Choose **btrfs** for snapshot rollback. 16 GB RAM, no hibernate → **zram**
  (Ubuntu enables it) plus an optional 8 GB swapfile.

## Phase 5 — Installer walkthrough
1. Insert USB, reboot, **F12** → pick the USB (Ventoy → the Ubuntu ISO).
2. Choose **Try Ubuntu** first; confirm Wi-Fi, trackpad, and display all work.
3. Launch Install. Connect to Wi-Fi. Set language/keyboard/timezone.
4. **Check** "Install third-party software for graphics and Wi-Fi hardware and
   additional media formats."
5. Install type: **Erase disk and install Ubuntu** → Advanced → choose **btrfs** →
   tick **Encrypt** and set a strong passphrase (write it down offline).
6. Create your user; set a **real hostname** (e.g. `xps-dev`, not `user-pc`).
7. Install, remove the USB when prompted, reboot; enter the LUKS passphrase.

## Phase 6 — First boot
```bash
sudo apt update && sudo apt full-upgrade
fwupdmgr refresh --force && fwupdmgr get-updates && fwupdmgr update
sudo apt install flatpak
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
hostnamectl; timedatectl
```
- No NVIDIA, so no driver step. Power management: keep the default
  **power-profiles-daemon** (do not add TLP unless you need it).
- Enroll fingerprint if the XPS reader is supported: `fprintd-enroll`.

## Phase 7 — Laptop fixes
- Intel iGPU + Intel Wi-Fi → nothing special.
- Suspend: `cat /sys/power/mem_sleep`. If it shows `[s2idle]` and battery drains
  in a bag, first apply BIOS updates via `fwupdmgr`; that fixes most XPS cases.
- HiDPI: GNOME on Wayland handles the XPS panel; set fractional scaling in
  `Settings → Displays` if needed.

## Phase 8 — Reversibility
- Keep the Ventoy USB as your rescue environment.
- Back up the LUKS header off-machine:
  ```bash
  sudo cryptsetup luksHeaderBackup /dev/nvme0n1p3 \
       --header-backup-file luks-header-backup.img   # replace pN with your LUKS partition
  ```
- Don't casually flip Secure Boot or storage mode now — it can trigger a LUKS or
  boot problem.

---

**Result.** Encrypted Ubuntu 26.04 LTS on the XPS, snapshots via btrfs, firmware
current. **Next:** run `linux-dev-workstation` to set up the dev environment, then
`linux-ai-dev-stack` for local + cloud AI tooling.
