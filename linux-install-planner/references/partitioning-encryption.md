# Reference — Phase 4: Partitioning, Filesystems & Encryption

> Planner note: prefer letting the **graphical installer** handle partitioning and
> encryption via its checkboxes — it is safer than manual `cryptsetup` for most
> users. Reach for the manual commands only for Arch or custom layouts. Every
> device path (`/dev/nvme0n1p2`, `/dev/sdX`) is a **placeholder** the human must
> replace with their verified target.

---

## 4.1 Full wipe vs dual-boot layout

- **Full wipe:** choose the installer's **"Erase disk and install."** Simplest and
  safest; combine with the "Encrypt" checkbox.
- **Dual-boot:** shrink the Windows partition **from within Windows Disk
  Management** (`diskmgmt.msc` → Shrink Volume) **before** installing. This is
  more reliable than the Linux installer's resize and flushes Windows' own
  filesystem state. Leave the freed space **unallocated**; the installer's
  "Install alongside Windows" fills it. (Confirm BitLocker off + Fast Startup off
  from Phase 3 first, or the resize is unsafe.)

---

## 4.2 UEFI partition scheme (GPT)

Minimum modern layout:

| Partition | Size | FS | Notes |
|---|---|---|---|
| **ESP** (EFI System Partition) | 512 MB – 1 GB | FAT32 | Reuse the existing Windows ESP when dual-booting; create fresh on full wipe. Use 1 GB if keeping multiple kernels / systemd-boot. |
| **root `/`** | rest of disk (or ~50–100 GB if a separate `/home`) | ext4 or btrfs | |
| **`/home`** (optional) | remainder | ext4 / btrfs | A separate `/home` lets you reinstall the OS without losing data. On **btrfs**, use a **subvolume** instead of a separate partition. |
| **swap** | see 4.4 | swap or zram | |

---

## 4.3 Filesystem choice (2026)

- **ext4** — rock-solid default. Pick for maximum simplicity/stability. No
  snapshots.
- **btrfs** — **recommended for a dev machine.** Copy-on-write **snapshots** (roll
  back a bad update or kernel), compression (`zstd`), and subvolumes. Fedora's
  default; available on Ubuntu/openSUSE. Slight overhead and the occasional
  `btrfs balance`, but the snapshot safety net is worth it.
- **zfs** — powerful (native encryption, checksums, snapshots) but **not in the
  mainline kernel** (licensing). Best on Ubuntu's experimental ZFS-on-root, or if
  the user already knows ZFS. Overkill for a single laptop — skip unless asked.

---

## 4.4 swap / zram / hibernation

- **zram** (compressed RAM swap) is the modern default (Fedora ships it;
  Ubuntu/Pop!_OS can enable it). Fast, no disk wear, no fixed partition. Good when
  **not** hibernating.
- A **swap partition or swapfile sized ≥ RAM** is required for **hibernate
  (suspend-to-disk)**. Want hibernate → make swap ≥ RAM (plus a little).
- Rule of thumb: 16 GB RAM → zram + an optional 8–16 GB swapfile; want hibernate →
  swap ≥ RAM.

---

## 4.5 Full-disk encryption (LUKS2)

- Recommend **LUKS2** for laptops (theft risk). Most graphical installers (Ubuntu,
  Fedora, Pop!_OS) offer a single **"Encrypt the new installation" checkbox** —
  use it; it sets a good default (LUKS2 + Argon2id KDF). **Prefer this over manual
  setup.**
- **Manual / Arch:**

  ```bash
  # /dev/nvme0n1pN is a PLACEHOLDER — replace with the verified target partition
  cryptsetup luksFormat /dev/nvme0n1pN         # LUKS2 + Argon2id by default
  cryptsetup open /dev/nvme0n1pN cryptroot
  ```

  **GRUB caveat:** GRUB's LUKS2 support is limited — if `/boot` is on the
  encrypted volume **and** you use GRUB, format that volume with `--pbkdf
  pbkdf2`. Using **systemd-boot** with a modern setup avoids this problem.

- **TPM2 auto-unlock (optional, nicer UX):** after install, bind a keyslot to the
  TPM so the disk unlocks without a passphrase at boot (keep the passphrase as a
  fallback):

  ```bash
  # PCR 7 = Secure Boot state. /dev/nvme0n1p2 is a PLACEHOLDER.
  sudo systemd-cryptenroll /dev/nvme0n1p2 --tpm2-device=auto --tpm2-pcrs=7
  ```

  **Warning:** binding to PCR 7 requires **Secure Boot ON and in user mode**.
  Firmware certificate changes (including `fwupd` updates) can change PCR 7 and
  **lock you out** — always keep the passphrase and a **LUKS header backup**.

---

## 4.6 btrfs snapshots (the payoff)

- **Timeshift** (Ubuntu / Pop!_OS / Mint world) — easy GUI, schedules btrfs
  snapshots; pairs with the `@` / `@home` subvolume layout those installers create.
- **Snapper + snap-pac + grub-btrfs** (Fedora / openSUSE / Arch world) —
  auto-snapshots before every package transaction and lets you **boot into a
  read-only snapshot from the GRUB menu** to recover a broken system. openSUSE
  does this out of the box.
- Requires the btrfs subvolume layout (`@` for `/`, `@home` for `/home`, and a
  `.snapshots` subvolume). The graphical installers set this up when you pick
  btrfs — **verify it exists before relying on snapshots.**

---

## 4.7 Header backup (do this in Phase 8, plan it here)

```bash
# Back up the LUKS header to external media, then verify the copy exists offline.
sudo cryptsetup luksHeaderBackup /dev/nvme0n1pN \
     --header-backup-file luks-header-backup.img
```

A corrupted LUKS header with **no backup** = permanently unrecoverable data, even
with the correct passphrase. Store the backup off the machine.

---

## Sources (authoritative)
- Arch Wiki — dm-crypt / Encrypting an entire system (LUKS2, Argon2id, GRUB pbkdf2); systemd-cryptenroll (TPM2 PCR7); Snapper
- Ubuntu / Fedora installer docs — encrypt checkbox, btrfs default, ZFS-on-root
- openSUSE — Snapper + grub-btrfs default setup
