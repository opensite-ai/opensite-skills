# Hardware Compatibility Triage — "Will My Hardware Work?"

Facts below are **as of 2026-07 — verify** with a web search for the user's exact
model. The goal of triage is to surface anything that should *push* the distro
choice (GPU vendor, Wi-Fi chipset, very new laptop silicon, Secure Boot posture)
before an install runbook is generated.

Ask for: CPU/APU, **GPU vendor + model**, RAM, storage, laptop-or-desktop (and
make/model if a laptop), and **Wi-Fi chipset**. Map each against the sections below.

---

## GPU vendor implications (often the deciding factor)

### NVIDIA
- **Wayland is now fine on NVIDIA.** Explicit sync (`linux-drm-syncobj-v1`) landed in the
  **555** driver series (2024) and fixed the flicker/out-of-order-frame issues; **560+**
  defaults to the open kernel modules; by the 2025 **590** series, Wayland + NVIDIA is
  genuinely daily-usable (HDR, Vulkan fixes).
- **Open kernel modules** are the recommended default for **Turing and newer** GPUs;
  proprietary modules are still needed for older cards.
- **Easiest NVIDIA distros:** Pop!_OS, Bazzite, Bluefin-nvidia/ublue images, Ubuntu
  (`ubuntu-drivers`, signed for Secure Boot). Fedora via RPM Fusion **akmod** (auto-rebuilds).
- **On rolling distros (Arch/CachyOS/EndeavourOS), always use the DKMS driver** so the
  module rebuilds on every kernel update. Never install the plain (non-DKMS) driver there.
- **Laptop implication:** most NVIDIA laptops are **Optimus hybrids** (see below).

### AMD
- **Best out-of-box Wayland/desktop experience** — the `amdgpu` kernel driver is upstream
  and needs no proprietary install for graphics. Great default for a hassle-free desktop.
- **Compute (ROCm)** support is narrower than CUDA: recent Radeon RX / Instinct cards are
  supported; older/consumer GPUs may need `HSA_OVERRIDE_GFX_VERSION`. If the user's AI work
  depends on GPU compute, verify their exact card is on the current ROCm support list.

### Intel (Arc / Core Ultra)
- Integrated Xe and discrete **Arc** GPUs are well supported by the upstream kernel + Mesa;
  favor a **recent kernel** (Fedora, CachyOS, Tumbleweed) for the newest silicon.
- Compute via upstream **PyTorch XPU** wheels; **NPU** (Core Ultra) via the Linux NPU driver
  + OpenVINO. Verify at runtime — this stack moves quickly.

### Apple Silicon (M-series)
- Use **Fedora Asahi Remix**. Practical support skews to **M1/M2-class** machines; verify
  M3/M4 status before promising it works.
- **No CUDA and no ROCm.** GPU acceleration is via Vulkan; local LLMs run well through
  llama.cpp using the GPU/Metal-adjacent path. Set expectations accordingly for ML frameworks.

### Integrated / CPU-only fallback
- Any distro works. Local LLM inference is still viable on CPU (llama.cpp) at smaller model
  sizes; recommend generous RAM. Flag that GPU-dependent ML frameworks will be slow.

---

## Wi-Fi chipset pitfalls

- **Broadcom** (common in older/consumer laptops and some Macs): frequently needs the
  `broadcom-wl` / out-of-tree firmware and often will **not** work on the live installer
  without a wired connection. Flag this early — it changes the install plan (have Ethernet
  or a USB tether ready).
- **Some Realtek** parts (certain USB and newer PCIe chips) need out-of-tree DKMS drivers.
- **Intel and MediaTek** Wi-Fi are generally the smoothest (in-kernel firmware).
- **Very new laptops:** brand-new Wi-Fi/Bluetooth combos may need a newer kernel — prefer
  Fedora / CachyOS / Tumbleweed or an Ubuntu **HWE** stack over an older LTS kernel.

---

## NVIDIA Optimus / hybrid laptops

- Most gaming/creator laptops ship an **NVIDIA Optimus** hybrid (Intel/AMD iGPU + NVIDIA dGPU).
- Expect to manage **PRIME** offloading (run the desktop on the iGPU, offload GPU-heavy apps
  to the dGPU) or a dedicated GPU mode. Battery life depends heavily on getting this right.
- Distros that smooth this over: **Pop!_OS** (System76 tooling), **Bazzite/Bluefin-nvidia**,
  Ubuntu (`prime-select`). Detailed configuration belongs to `linux-dev-workstation`.

---

## Secure Boot

- **Works out of the box (MS-signed shim):** Ubuntu, Fedora, Debian, openSUSE, Mint, Pop!_OS,
  and the atomic Fedora / Universal Blue images.
- **Manual effort:** Arch / CachyOS / EndeavourOS (`sbctl` or `shim-signed` + your own keys);
  **NixOS** uses **Lanzaboote** (signs Unified Kernel Images).
- If the user refuses to disable Secure Boot and does not want to manage keys, steer them to
  the "out of the box" group.

---

## Laptop niceties: fingerprint, webcam, battery

- **Fingerprint / webcam / new sensors** on very recent laptops: favor a **recent kernel**
  (Fedora 43, CachyOS, Tumbleweed) over an older LTS kernel, or use Ubuntu LTS **HWE** stacks.
- **Power/battery:** Fedora and Ubuntu ship `power-profiles-daemon`/`tuned`; add **TLP** for
  extra savings. Newest kernels help on brand-new Intel Lunar/Arrow Lake and AMD Strix silicon.
- **Best-supported laptop brands:** Framework, Lenovo ThinkPad, Dell XPS / Developer Edition,
  System76. On these, Fedora and Ubuntu LTS are the smoothest.

---

## HiDPI / Wayland readiness

- Wayland now genuinely **wins** on fractional scaling, mixed-DPI multi-monitor, and per-monitor
  refresh — a reason to prefer it on modern laptops + external 4K displays.
- GNOME is Wayland-only (49/50); KDE targets Wayland-only in Plasma 6.8. Choosing an X11-first
  workflow is swimming upstream in 2026.
- If a specific pro tool assumes X11 (some screen-share/remote/color/automation stacks), verify
  it works via Xwayland/PipeWire portals before committing — or keep an X11-capable session
  (Cinnamon/Mint, KDE on an older release) as a shrinking-window fallback.

---

## Quick "will my hardware work?" checklist

Run through these before recommending a distro:

- [ ] **GPU vendor + model** identified, and its driver path is known (NVIDIA open vs proprietary;
      AMD amdgpu/ROCm support; Intel Arc/XPU/NPU; Apple Silicon Asahi; CPU-only).
- [ ] If **NVIDIA + rolling distro**, the plan uses **DKMS** drivers.
- [ ] **Laptop?** Checked for NVIDIA Optimus/PRIME and battery/power daemon support.
- [ ] **Wi-Fi chipset** identified; Broadcom/some-Realtek flagged (may need wired install).
- [ ] **Secure Boot** posture decided (keep on → out-of-box distro; or willing to manage keys).
- [ ] **New silicon** (Lunar/Arrow Lake, Strix, latest AMD/NVIDIA) → recent-kernel distro chosen.
- [ ] Any **X11-only pro tools** verified against Wayland/Xwayland.
- [ ] Versions and support windows **verified via web search** (not taken from embedded numbers).

Hand the confirmed hardware profile to `linux-install-planner` for the install runbook, and to
`linux-dev-workstation` for driver configuration after first boot.
