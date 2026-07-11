# Reference — Phase 6: First-Boot Checklist

> Run these in order on the freshly installed system. Commands are grouped by
> distro family; the human runs them at the machine. Versions are "as of 2026-07
> — verify." This phase ends where the `linux-dev-workstation` skill begins.

---

## 1. Full system update immediately

- **Ubuntu / Pop!_OS:** `sudo apt update && sudo apt full-upgrade`
- **Fedora:** `sudo dnf upgrade --refresh`
- **Arch:** `sudo pacman -Syu`

Reboot if the kernel updated.

---

## 2. Trigger driver install (if not done in the installer)

- **Ubuntu:** `ubuntu-drivers devices` then `sudo ubuntu-drivers autoinstall`
  (installs the recommended NVIDIA driver). The **Pop!_OS NVIDIA ISO** already
  has it.
- **Fedora:** enable **RPM Fusion** (step 4), then `sudo dnf install akmod-nvidia`
  (Wayland-first on Fedora 44). Wait for the `akmod` to build before rebooting.
- With Secure Boot on, the first reboot after an NVIDIA install shows the blue
  **MOK enrollment** screen — complete it (see the UEFI reference). A black screen
  on first boot usually means MOK enrollment is still pending.
- Full driver depth (AMD ROCm, Intel XPU/NPU, Apple Asahi, CPU fallback) belongs
  to the `linux-dev-workstation` skill — this phase just gets the display working.

---

## 3. Firmware updates via fwupd / LVFS

Works across Dell, Lenovo, HP, Framework, and many others:

```bash
fwupdmgr refresh --force
fwupdmgr get-updates
fwupdmgr update
```

Do this early — firmware fixes suspend, battery, USB, and NVMe bugs.

> **Caution:** if you set up **TPM-bound LUKS on PCR 0** (not the recommended
> PCR 7), firmware updates can change the PCR measurement and lock unlocking.
> Keep the passphrase and LUKS header backup regardless.

---

## 4. Enable Flatpak + Flathub (universal app source)

```bash
sudo apt install flatpak        # Fedora/Pop!_OS usually have it already
flatpak remote-add --if-not-exists flathub \
    https://flathub.org/repo/flathub.flatpakrepo
```

- **Fedora:** also enable **RPM Fusion** (free + nonfree) for codecs and NVIDIA:
  install the free and nonfree release RPMs from the RPM Fusion site, then
  `sudo dnf upgrade --refresh`.
- **Ubuntu:** `snap` is preinstalled; Flathub is still worth adding.

---

## 5. Power management — pick EXACTLY ONE manager (they conflict)

- **power-profiles-daemon** — GNOME/KDE default; integrates with the desktop power
  slider. Good default; leave it.
- **TLP** — more aggressive battery savings / CPU control. If you install it,
  **mask `power-profiles-daemon`** (and often `systemd-rfkill`) to avoid conflict.
  Install `tlp-pd` if you still want the desktop power-profile UI.
- **tuned / tuned-ppd** — Fedora's newer default in some spins.

**Never run TLP + power-profiles-daemon + tuned together.** Running two managers
at once causes erratic performance and battery behavior.

---

## 6. Identity: hostname / timezone / locale

```bash
hostnamectl        # confirm a real hostname was set (not "user-pc")
timedatectl        # confirm timezone + NTP sync
localectl          # confirm locale/keymap
```

---

## 7. Function keys / brightness / audio keys

Usually work out of the box. If a key does nothing, note the laptop vendor/model
for later kernel or quirk fixes (see the laptop-fixes reference).

---

## 8. Fingerprint reader / IR webcam

```bash
fprintd-enroll     # needs the fprintd package + a supported reader
```

Set expectations: many Goodix / Synaptics readers are **unsupported** on Linux.
Standard UVC webcams just work; Windows Hello **IR face-unlock** cameras usually
do **not** work for face login on Linux.

---

## 9. Hand off to the dev environment

Git, shell, editor, container runtime, language toolchains, and dotfiles are the
natural next step — that is the `linux-dev-workstation` skill's job, followed by
`linux-ai-dev-stack` for the AI toolchain. Do **not** try to cover them here.

---

## Sources (authoritative)
- Ubuntu / Fedora / Arch package + driver docs
- fwupd / LVFS (fwupd.org) — `fwupdmgr refresh/get-updates/update`
- RPM Fusion — Fedora codecs/NVIDIA; Flathub (flathub.org)
- Arch Wiki — TLP, Power management, fprintd
