# Hardware & Requirements Intake Worksheet

Fill this in with the user, then map the answers to a recommendation using
`references/distro-matrix.md` and `references/hardware-compat-triage.md`. Keep it
advisory — this worksheet produces a distro recommendation, not an install plan.

---

## 1. Primary optimization (pick ONE)

- [ ] Never-breaks / "set and forget"
- [ ] Bleeding-edge GPU / AI toolchains ASAP
- [ ] Byte-for-byte reproducibility / fleet consistency
- [ ] Laptop — battery life + hardware just working
- [ ] Switching from Windows — low friction
- [ ] Homelab / server / self-hosted models

> The tie-break axis: newest tools **vs** zero maintenance. Note which the user
> weights more heavily: __________________________________

## 2. Hardware

| Field | Value |
|---|---|
| CPU / APU (model) | |
| GPU vendor + model | (NVIDIA series / AMD / Intel Arc / Apple Silicon / integrated) |
| GPU compute needed? (CUDA/ROCm/XPU) | (yes/no — for ML frameworks) |
| RAM | |
| Storage (size + NVMe/SATA) | |
| Form factor | (laptop / desktop) |
| Laptop make + model (if laptop) | |
| Hybrid graphics? (NVIDIA Optimus) | (yes/no/unknown) |
| Wi-Fi chipset | (Intel / MediaTek / Broadcom / Realtek / unknown) |
| Displays | (count, resolution, HiDPI/4K, mixed-DPI?) |

## 3. Constraints & preferences

| Field | Value |
|---|---|
| Secure Boot must stay on? | (yes/no/don't care) |
| Comfortable doing dev inside containers? | (yes/no) |
| Willing to learn Nix? | (yes/no) |
| Production/cloud parity required? | (which OS do the servers run?) |
| Multiple machines to keep identical? | (yes/no — how many) |
| Terminal / maintenance comfort | (beginner / intermediate / senior) |
| Desktop preference | (GNOME / KDE / COSMIC / tiling WM / no preference) |

## 4. Triage flags (from hardware-compat-triage.md)

- [ ] NVIDIA on a rolling distro → plan requires **DKMS** driver
- [ ] NVIDIA laptop → **Optimus/PRIME** handling needed
- [ ] Broadcom / some Realtek Wi-Fi → may need **wired install**
- [ ] Very new silicon (Lunar/Arrow Lake, Strix, latest GPUs) → **recent-kernel** distro
- [ ] Secure Boot on + no key management → **out-of-box shim** distro
- [ ] X11-only pro tool in use → verify Wayland/Xwayland support

---

## 5. Recommendation (output)

**Primary pick:** ______________________
- Rationale (one line): ______________________
- Biggest trade-off: ______________________

**Alternative:** ______________________
- When to prefer it instead: ______________________

**Verified via web search on (date):** __________  (confirm current release + support window)

**Next step:** hand off to the `linux-install-planner` skill to build the install
runbook; then `linux-dev-workstation` after first boot.
