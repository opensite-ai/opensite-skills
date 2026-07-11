# Security Hardening

SSH keys, commit signing, secrets, firewall, auto-updates, and backups.
Versions "as of 2026-07 — verify."

> **SAFETY:** enabling a default-deny firewall on a remote/SSH box can lock you
> out. **Always `allow ssh` (and any Tailscale interface) before `enable`**, and
> confirm you still have console access. Confirm before any firewall change.

## 1. SSH keys (ed25519)

```bash
ssh-keygen -t ed25519 -C "youruser@host" -f ~/.ssh/id_ed25519   # add a passphrase
# Hardware-backed (FIDO2/YubiKey) — strongest:
ssh-keygen -t ed25519-sk -C "youruser@yubikey" -f ~/.ssh/id_ed25519_sk
ssh-add ~/.ssh/id_ed25519      # load into the agent
```

ed25519 is the modern default (small, fast, secure). Use `ed25519-sk`/`ecdsa-sk`
for hardware-key-backed SSH when possible. Harden `~/.ssh/config` with
`IdentitiesOnly yes` and per-host keys. On servers, harden `sshd`:
`PasswordAuthentication no`, disable root login, key-only, optional non-standard
port + fail2ban (confirm you have key access first).

## 2. Commit signing (SSH-based, simplest)

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true
# For local verification of others' commits:
git config --global gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers
```

Upload the same key to GitHub as a **signing key** (in addition to an auth key).
One key type for auth + signing = less overhead. GPG and 1Password (as the
SSH/commit-signing agent) are alternatives.

## 3. Secrets management

| Tool | Model | Use when |
|---|---|---|
| **age + sops** | Encrypt values in YAML/JSON/env, **commit to git**, decrypt at runtime; add teammates via public keys; no cloud | Zero-infra, git-native, dotfiles, NixOS via sops-nix |
| **1Password CLI** (`op`) | `op://` references; secrets never hit disk, resolved at apply time; vault sharing + rotation | Teams; managed vault + rotation |
| **pass** | GPG-encrypted files in a git repo | Minimalist, GPG-centric |
| **HashiCorp Vault** | Central dynamic secrets, leases | Larger teams / production infra |

**Recommendation:** age + sops for a solo/git-first workflow (pairs with chezmoi
& Nix); 1Password CLI if you already use 1Password and want team sharing +
zero-disk exposure. **Never commit plaintext secrets**; add pre-commit scanning
(**gitleaks**/**trufflehog**).

```bash
# age + sops example
age-keygen -o ~/.config/sops/age/keys.txt
sops --encrypt --age <public-key> secrets.env > secrets.enc.env   # commit the .enc
```

## 4. Firewall (default-deny inbound)

```bash
# Ubuntu/Debian — ufw  (allow ssh BEFORE enable!)
sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw enable            # CONFIRM: can lock out remote sessions

# Fedora/RHEL — firewalld
sudo firewall-cmd --add-service=ssh --permanent
sudo firewall-cmd --reload

# Arch — ufw or nftables directly
```

All are frontends over nftables. On a laptop: default-deny inbound + allow only
what you need. Scope Tailscale traffic with ACLs instead of opening public ports.

## 5. Automatic security updates

```bash
# Ubuntu/Debian
sudo apt install unattended-upgrades && sudo dpkg-reconfigure -plow unattended-upgrades
# Fedora
sudo dnf install dnf-automatic && sudo systemctl enable --now dnf-automatic.timer
# Arch: no auto-updates by design — update deliberately (`pacman -Syu`), read the
# news first; pair with btrfs snapshots to roll back a bad update.
```

Reboot for kernel updates (or use livepatch/kexec where available).

## 6. Backups & snapshots

- **Local instant rollback:** **btrfs** (or **zfs**) snapshots via **snapper** or
  **Timeshift** (scheduled/pre-update). Not a backup (same disk) but the fastest
  "undo a bad upgrade."
- **Off-host backups (the real backup):**
  - **restic** — Go, single binary, dedup, encrypted, many backends
    (S3/B2/Tigris/rclone). `restic backup`, `forget --prune`, easy restores.
  - **borg** (+ **borgmatic** for scheduling) — excellent dedup/compression over
    SSH.

```bash
# restic to an object-store target, on a systemd timer
export RESTIC_REPOSITORY=s3:https://... RESTIC_PASSWORD_FILE=~/.config/restic/pass
restic init
restic backup ~/code ~/.config
restic forget --keep-daily 7 --keep-weekly 4 --prune
```

**Recommendation:** btrfs/zfs snapshots for local rollback **plus** restic (or
borg) to an off-site/object-storage target on a timer. **Test restores.** Encrypt
backups (both do by default). Full-disk encryption (LUKS) is handled at install
time by the `linux-install-planner` skill.

## Verify

```bash
ssh-add -l                         # keys loaded in the agent
git log --show-signature -1        # last commit signature verifies
sudo ufw status                    # or: sudo firewall-cmd --state
systemctl status unattended-upgrades.service 2>/dev/null || systemctl status dnf-automatic.timer
restic snapshots                   # backups exist
```
