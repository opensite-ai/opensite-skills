# Shell & Terminal

zsh/fish + starship, the modern CLI set, terminal emulators, and multiplexers
(tmux vs Zellij). Versions "as of 2026-07 — verify."

> **SAFETY:** `chsh` changes your default login shell. Confirm with the user and
> make sure the target shell is installed and in `/etc/shells` before running it,
> or a broken rc can lock you out of interactive logins.

## 1. Shell: zsh vs fish

- **zsh** — the senior default. POSIX-compatible (bash one-liners "just work"),
  huge plugin ecosystem. Skip heavy frameworks (Oh-My-Zsh is slow); use a lean
  plugin manager (**zinit** or **antidote**) or source a few plugins manually:
  `zsh-autosuggestions`, `zsh-syntax-highlighting` (or `fast-syntax-highlighting`),
  `zsh-history-substring-search`, plus fzf keybindings.
- **fish** — friendlier out of the box (autosuggestions, highlighting, sane
  completions, zero config) but **not POSIX** — you cannot paste bash one-liners
  verbatim. Fish 4.x (rewritten in Rust) is fast and stable.
- **Recommendation:** zsh + starship for someone who lives in shell scripts and
  remote boxes. Choose fish only if you accept the non-POSIX tax.

```bash
sudo apt install zsh    # or: sudo dnf install zsh / sudo pacman -S zsh
grep -q "$(command -v zsh)" /etc/shells || command -v zsh | sudo tee -a /etc/shells
chsh -s "$(command -v zsh)"   # CONFIRM FIRST — changes default shell
```

## 2. Prompt: starship

Single static Rust binary, cross-shell, fast, TOML config at
`~/.config/starship.toml`. Needs a **Nerd Font** (JetBrainsMono/FiraCode Nerd
Font) for glyphs.

```bash
curl -sS https://starship.rs/install.sh | sh
# zsh:  echo 'eval "$(starship init zsh)"'   >> ~/.zshrc
# fish: echo 'starship init fish | source'   >> ~/.config/fish/config.fish
```

## 3. Modern CLI set (install as a set)

| Classic | Modern | Notes |
|---|---|---|
| `ls` | **eza** | icons, git status, tree; `alias ls='eza --icons --git'` |
| `cat` | **bat** | syntax highlight + paging; Debian binary is `batcat` |
| `find` | **fd** | fast, gitignore-aware; Debian binary is `fdfind` |
| `grep` | **ripgrep (rg)** | fastest recursive search — the biggest single win |
| `cd` | **zoxide** | frecency jumping; `eval "$(zoxide init zsh)"`, use `z <partial>` |
| — | **fzf** | fuzzy finder; powers Ctrl-R history, Ctrl-T files |
| `diff` | **delta** | git diffs; set as `core.pager`/`interactive.diffFilter` |
| `du` | **dust** | intuitive disk-usage tree |
| `ps` | **procs** | readable process viewer |
| `top`/`htop` | **btop** | best-in-class TUI monitor (CPU/mem/net/disk/GPU) |

```bash
# Arch (current versions):
sudo pacman -S eza bat fd ripgrep zoxide fzf git-delta dust procs btop
# Fedora:
sudo dnf install eza bat fd-find ripgrep zoxide fzf git-delta dust procs btop
# Ubuntu/Debian: apt versions lag; prefer Homebrew-on-Linux, `cargo binstall`,
# or `mise`/`pixi global` for current builds. Symlink Debian binary names:
#   ln -s "$(command -v fdfind)" ~/.local/bin/fd
#   ln -s "$(command -v batcat)" ~/.local/bin/bat
```

Non-negotiables: **ripgrep + fzf + zoxide + bat**. The compounding productivity
gain is real; install the full set.

## 4. Terminal emulators (all GPU-accelerated)

- **Ghostty** — top pick for 2026 (Zig, native GTK4 UI, zero-config, Kitty
  graphics protocol). **1.3.1** (Mar 2026) added scrollback search + native
  scrollbars. In Ubuntu 26.04 repos; also Flatpak/AUR/Homebrew.
- **Kitty** — mature, extremely fast, scriptable (kittens, graphics protocol).
- **WezTerm** — Rust, Lua config, built-in multiplexer + SSH domains.
- **Alacritty** — Rust, minimalist, no tabs/splits by design — pair with
  tmux/Zellij. Pure-speed canvas.

GPU accel matters most for fast scrolling and large `rg`/log output. Ghostty for
the best default; Kitty/WezTerm for more built-in features; Alacritty + tmux for
minimalists.

## 5. Multiplexer: tmux vs Zellij

- **tmux** (C, 2007) — the proven standard. Unbeatable ecosystem (**tpm**,
  `tmux-resurrect`, `tmux-continuum`), fully scriptable, remote-first (sessions
  survive SSH disconnects — essential for remote GPU work). Steeper keybinding
  curve; needs `~/.tmux.conf` tuning — see [../templates/tmux.conf](../templates/tmux.conf).
- **Zellij** (Rust, 2021) — modern, mode-based, **discoverable** (on-screen key
  hints), floating panes + per-pane resize, WASM plugins, KDL layouts. Younger
  plugin ecosystem.
- **Recommendation:** tmux for heavy remote/SSH work and maximum scriptability;
  Zellij if mostly local and you value UX/onboarding. Both survive SSH drops.

```bash
# tmux + tpm (tmux plugin manager)
sudo apt install tmux   # or dnf/pacman
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
# copy the template, then inside tmux press: prefix + I  (installs plugins)
cp <this-skill>/templates/tmux.conf ~/.tmux.conf
```

A **sessionizer** (fzf + `tmux switch-client`) that jumps to a project as a named
session is the single biggest tmux ergonomics win — bind it to `prefix + f`.

## Verify

```bash
echo "$SHELL"; zsh --version
starship --version
rg --version && fzf --version && zoxide --version && bat --version
tmux -V   # or: zellij --version
```
