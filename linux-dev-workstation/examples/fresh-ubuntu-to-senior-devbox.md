# Example: Fresh Ubuntu → Senior Dev Box

A worked transcript of an agent using this skill on a **fresh Ubuntu 24.04 LTS**
desktop with an **NVIDIA RTX 4070 (Ada)**, Wayland, Secure Boot **on**. It shows
the SAFETY PROTOCOL in action: detect → confirm → act → verify. Versions
"as of 2026-07 — verify."

---

## Step 1 — Detection

```
$ . /etc/os-release && echo "$PRETTY_NAME"
Ubuntu 24.04.2 LTS
$ command -v apt dnf pacman
/usr/bin/apt
$ lspci | grep -Ei 'vga|3d|display'
01:00.0 VGA compatible controller: NVIDIA Corporation AD104 [GeForce RTX 4070]
$ echo "$XDG_SESSION_TYPE"
wayland
$ mokutil --sb-state
SecureBoot enabled
```

**Findings:** Ubuntu/apt · NVIDIA Ada (Turing+, so `nvidia-open`) · Wayland ·
desktop · Secure Boot ON → MOK signing required. Agent branches accordingly.

## Stage 1 — GPU drivers (the destructive one)

> Agent: "Installing `nvidia-driver-580-open` will blacklist `nouveau`, build a
> DKMS module, and — because Secure Boot is on — enroll a MOK key requiring a
> reboot into the MOK Manager. X11 stays available as a fallback. Proceed?"
> User: "yes"

```bash
sudo ubuntu-drivers install                 # picks the -open recommended build
# Secure Boot: enroll a signing key (one-time password, then reboot to confirm)
sudo mokutil --import /var/lib/dkms/mok.pub || true
# NVIDIA container toolkit for later GPU containers:
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
```

Verify (before trusting a Wayland reboot):

```
$ nvidia-smi
Driver Version: 580.167.08   CUDA Version: 13.0
GeForce RTX 4070 ...  0MiB / 12282MiB
```

Passed → safe to reboot. (See references/gpu-drivers.md.)

## Stage 2 — Shell + terminal

```bash
sudo apt install -y zsh
grep -q "$(command -v zsh)" /etc/shells || command -v zsh | sudo tee -a /etc/shells
chsh -s "$(command -v zsh)"                  # CONFIRMED with user
curl -sS https://starship.rs/install.sh | sh
# modern CLI via Homebrew-on-Linux (apt versions lag)
brew install eza bat fd ripgrep zoxide fzf git-delta dust procs btop
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
cp templates/tmux.conf ~/.tmux.conf
```

Verify: `rg --version && starship --version && tmux -V` all print. (See
references/shell-terminal.md.)

## Stage 3 — Editors

```bash
mise use -g neovim@latest
git clone https://github.com/LazyVim/starter ~/.config/nvim && rm -rf ~/.config/nvim/.git
# VS Code from the Microsoft repo (see references/editors.md)
```

Verify: `nvim --version | head -1` → v0.11; `:checkhealth` clean.

## Stage 4 — Language toolchains

```bash
curl https://mise.run | sh && eval "$(mise activate zsh)"
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup component add clippy rustfmt rust-analyzer
curl -LsSf https://astral.sh/uv/install.sh | sh && uv python install 3.13
mise use -g ruby@3.4 node@lts && gem install ruby-lsp rubocop
corepack enable && pnpm add -g @biomejs/biome typescript-language-server
```

Verify:

```
$ mise ls && rustc -V && uv --version && ruby -v && node -v
rust 1.89.0 · python 3.13 · ruby 3.4 · node lts
rustc 1.89.0
uv 0.x
```

(See references/language-toolchains.md — includes the per-language update
workflows.)

## Stage 5 — Containers

```bash
sudo apt install -y podman           # rootless by default
podman run --rm hello-world
```

Verify: `podman run --rm hello-world` prints the hello banner. (See
references/containers.md.)

## Stage 6 — Reproducibility

```bash
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- init --apply youruser
# Ansible captures system packages; chezmoi captures dotfiles.
```

Verify: `chezmoi doctor` reports no problems. (See references/reproducibility.md.)

## Stage 7 — Security hardening

> Agent: "About to enable a default-deny firewall. I've already added an
> `allow ssh` rule so this won't lock you out. Enable now?"  User: "yes"

```bash
ssh-keygen -t ed25519 -C "youruser@devbox" -f ~/.ssh/id_ed25519
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true
sudo ufw default deny incoming && sudo ufw allow ssh && sudo ufw enable
sudo apt install -y unattended-upgrades
restic version   # off-host backups configured to object storage
```

Verify: `git log --show-signature -1` verifies; `sudo ufw status` shows
default-deny + ssh allowed. (See references/security-hardening.md.)

## Hand-off

Base workstation complete and verified. Agent hands off to the
`linux-ai-dev-stack` skill to install local LLM inference (the RTX 4070's 12 GB
VRAM → 7B–13B Q4 tier), AI coding agents + MCP servers, ML frameworks, and any
remote GPU workflow.
