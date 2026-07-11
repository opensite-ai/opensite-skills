# Reference — Phase 3: UEFI/BIOS and Windows Prep

> **Highest-footgun phase.** All Windows-side prep here happens **before**
> rebooting to install. Planner note: these are steps the human performs; you
> cannot see their firmware. Have them read each setting back before changing it.

---

## 3.1 Disable Fast Startup (and understand hibernation)

Fast Startup leaves the Windows filesystem in a hibernated / "dirty" state.
Mounting it from Linux can corrupt it, and it breaks dual-boot and a shared ESP.

From an **admin** command prompt:

```
powercfg /H off
```

This disables Fast Startup **and** hibernation (the safest option for dual-boot).
Then pick **Shut down** — **not Restart**. A Restart does **not** clear the
hibernation state; only a full shutdown does.

---

## 3.2 BitLocker (dual-boot: critical)

Windows 11 increasingly turns on **device encryption / BitLocker by default**.

- An encrypted disk looks like random noise to the Linux installer, so **"Install
  alongside Windows" cannot safely resize the partition** (Ubuntu docs call this
  out explicitly).
- **Dual-boot:** in Windows, `Control Panel → BitLocker → Turn off`. **Full
  decrypt is safest** before resizing; suspending works but is riskier.
- **Save the BitLocker recovery key regardless** (Microsoft account or printout).
  Changing Secure Boot / TPM settings later can trigger a recovery prompt, and
  without the key the user is locked out of Windows.
- **Full wipe:** BitLocker doesn't block the erase, but still save the recovery
  key in case the user aborts and boots back into Windows after changing firmware.

---

## 3.3 Enter firmware setup

- Reboot and tap the firmware key. Common keys (varies by vendor):
  - **Dell / System76 desktops:** `Del` or `F2`
  - **Laptops (general):** `F2` or `Esc`
  - **Lenovo:** `F1`, or `Enter` then `F1`
  - **HP:** `Esc` then `F10`
  - **Also try:** `F1`, `F10`
- From Windows you can also reach it via `Settings → System → Recovery →
  Advanced startup → Restart now → Troubleshoot → UEFI Firmware Settings`.
- Learn the **one-time boot menu** key (often `F12`, `F9`, `F7`, or `Esc`) to
  pick the USB **without** permanently changing the boot order.

---

## 3.4 Secure Boot — keep vs disable

- **Keep it ON** for **Ubuntu, Fedora, Pop!_OS, or openSUSE** — they ship a
  Microsoft-signed `shim`, so Secure Boot "just works." Keeping it on is more
  secure and avoids a BitLocker recovery prompt on the Windows side.
  - **Caveat:** out-of-tree / DKMS drivers (proprietary **NVIDIA**, VirtualBox,
    some Wi-Fi) require enrolling a **MOK (Machine Owner Key)**. On the next boot
    a blue **MOK Manager** screen appears — the user chooses "Enroll MOK" and
    enters the password set during install. Ubuntu/Fedora automate creating the
    key; the human just completes the blue screen. Skipping it = no NVIDIA driver.
- **Disable it** for **Arch or any distro without a signed shim**, or if the
  firmware refuses to boot the USB. The setting is usually `Security → Secure Boot
  → Disabled`. Some firmware requires setting a **supervisor/admin password**
  first to expose the toggle, or switching the OS mode from "Windows UEFI mode"
  to "Other OS".

---

## 3.5 Storage mode: Intel RST / RAID / VMD → AHCI

Many Windows laptops (especially Dell; some HP/Lenovo) ship the SATA/NVMe
controller in **Intel RST / "RAID On" / VMD** mode.

- **Symptom:** the Linux installer **shows no disks**.
- **Modern kernels (Ubuntu 26.04, Fedora 44) include the `vmd` driver**, so most
  NVMe drives are detected even with VMD/RST on — **try installing first.**
- If the disk is invisible, switch the firmware SATA/NVMe mode to **AHCI** (or
  **disable the VMD controller**).
- **Dual-boot gotcha:** switching RST → AHCI **after** Windows is installed makes
  Windows blue-screen **`INACCESSIBLE_BOOT_DEVICE`**. To keep Windows bootable,
  do the Microsoft-documented safe-mode dance **before** the switch:
  1. Windows admin cmd: `bcdedit /set {current} safeboot minimal`
  2. Reboot into firmware, set **AHCI**.
  3. Boot Windows (it loads the AHCI driver in safe mode), then admin cmd:
     `bcdedit /deletevalue {current} safeboot`, and reboot.
- **Full wipe:** just switch to AHCI directly — no dance needed.

---

## 3.6 TPM

- Leave **TPM 2.0 enabled**. It is needed if the user ever wants Windows 11 back,
  and it enables **LUKS TPM auto-unlock** on Linux (see the partitioning
  reference). Disabling TPM can trigger BitLocker recovery on the Windows side.

---

## Order of operations for Phase 3

1. `powercfg /H off`, then full **Shut down**.
2. Turn BitLocker off / save the recovery key (dual-boot).
3. Enter firmware; note the one-time boot menu key.
4. Decide Secure Boot (keep for shim distros; disable for Arch).
5. Handle RST/VMD only if the installer can't see the disk.
6. Confirm TPM 2.0 stays on.

---

## Sources (authoritative)
- Ubuntu Desktop docs — BitLocker section; "Intel RST during Ubuntu installation"
- Arch Wiki — Dual boot with Windows (Fast Startup, ESP); Secure Boot (shim / MOK / DKMS)
- Microsoft docs — `bcdedit safeboot` AHCI switch procedure
