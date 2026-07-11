# Reference — Phase 7: Common Laptop Pain Points & Fixes

> Personalize the runbook with only the fixes that match the user's hardware
> (from the Phase 1 recon). Commands are run at the machine; versions are "as of
> 2026-07 — verify."

---

## 7.1 NVIDIA hybrid graphics (Optimus)

- **Best path:** pick a distro that handles it — **Pop!_OS NVIDIA ISO**
  (preconfigured, ships a GPU switcher) or Ubuntu with `nvidia-driver` + built-in
  **PRIME**.
- **Default to hybrid / render-offload:** the iGPU drives the display for battery;
  run a specific app on the dGPU:
  - `prime-run <app>` (Arch), or the official NVIDIA method:
    `__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia <app>`
  - **Ubuntu:** `prime-select on-demand|nvidia|intel`
  - **Pop!_OS:** GPU switcher in the top bar
  - Alternatives: `optimus-manager` (Arch) or `switcheroo-control`
    (desktop-integrated; also handles AMD/Intel)
- **Symptoms to expect:**
  - Black screen on first boot after driver install — usually a pending **MOK
    enrollment**; reboot and complete the blue MOK screen (Secure Boot on).
  - External HDMI ports wired to the dGPU only — needs the dGPU active to output.
- **Wayland vs Xorg:** NVIDIA + Wayland (default on Fedora/GNOME) is solid on
  recent drivers (555+); older setups may prefer Xorg.

---

## 7.2 Wi-Fi firmware

Have a **USB-Ethernet adapter or phone USB-tethering** ready during install so the
user can pull drivers if Wi-Fi is missing on the live USB.

- **Broadcom** (PCI IDs `14e4:`): often no Wi-Fi on the live USB. Install
  post-boot over Ethernet/tether:
  - **Ubuntu:** `bcmwl-kernel-source` (or `firmware-b43-installer`)
  - **Arch:** `broadcom-wl` / `broadcom-wl-dkms` for newer chips, `b43-firmware`
    for old. If both could apply, **prefer `broadcom-wl`** (b43 has known freezes
    on BCM4331). Newest chips use in-kernel `brcmfmac` with firmware from
    `linux-firmware`.
- **Realtek USB/PCIe** (e.g. RTL8821CE, early RTL8852): install `linux-firmware`;
  for unsupported chips use a community DKMS repo (e.g. `rtl8821ce-dkms`). Modern
  kernels (6.11+) cover most.
- **Intel / MediaTek:** generally excellent; work on the live USB.

---

## 7.3 Battery life

- Confirm only **one** power manager is active (see the first-boot reference).
- Inspect and auto-tune: `sudo powertop --auto-tune`.
- Enable **TLP** for more savings (then mask power-profiles-daemon). Set battery
  **charge thresholds** on ThinkPads and other supported machines.
- For Intel, confirm **S0ix** works (see 7.4).

---

## 7.4 Suspend: S3 vs Modern Standby (s2idle)

Check what the machine offers:

```bash
cat /sys/power/mem_sleep      # [s2idle] deep  => s2idle is the active mode
```

Many 2020+ laptops are **s2idle / Modern Standby only** (no S3 in firmware).
s2idle should match S3 savings but on some machines drains the battery in a bag
(the "hot bag" problem). Fixes, in order:

1. **BIOS update** (`fwupd`) — the most common real fix.
2. If firmware exposes a "Sleep mode: Windows / Linux (S3)" toggle, choose
   **Linux/S3**.
3. If `deep` (S3) is listed but not the default, add the kernel parameter
   `mem_sleep_default=deep` (via `/etc/default/grub`
   `GRUB_CMDLINE_LINUX_DEFAULT`, or a systemd-boot entry), then update the
   bootloader config.
4. **AMD:** use `amd_s2idle` / `amd-debug-tools`. **Intel:** use
   `S0ixSelftestTool` to find the device blocking deep idle.

---

## 7.5 HiDPI / fractional scaling

- **Wayland (GNOME/KDE)** handles HiDPI best — prefer it on HiDPI laptops and for
  mixed-DPI multi-monitor setups (per-monitor scaling).
- **GNOME** fractional scaling (125 / 150 / 175 %) is on by default in recent
  releases; if not:

  ```bash
  gsettings set org.gnome.mutter experimental-features "['scale-monitor-framebuffer']"
  ```

  then pick the percentage in `Settings → Displays`. **KDE Plasma** has a native
  scaling slider.
- **Xorg** cleanly does integer scaling only; fractional via `xrandr --scale` is
  blurry and heavier. Prefer Wayland for HiDPI.

---

## Sources (authoritative)
- Arch Wiki — NVIDIA Optimus / PRIME; Broadcom wireless; Power management; TLP;
  Suspend and hibernate (`mem_sleep`); HiDPI
- NVIDIA — PRIME render offload docs
- Kernel/vendor tools — `amd-debug-tools`, Intel `S0ixSelftestTool`, `powertop`
