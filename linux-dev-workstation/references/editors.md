# Editors / IDEs

Advanced, power-user config for Neovim/Vim, VS Code, and Zed. Versions
"as of 2026-07 — verify." Many seniors run Neovim + VS Code (or Zed) side by side.

## 1. Neovim / Vim

The modern power-user editor: Lua config, Tree-sitter highlighting, native LSP,
`lazy.nvim` plugin manager. **Install current Neovim (≥ 0.10)** — distro packages
lag; use the AppImage, Homebrew, `mise use neovim`, `pixi global install neovim`,
or Arch's fresh `pacman`.

### Distributions (starting points)

- **kickstart.nvim** — one well-commented `init.lua` you copy and own. **Best for
  learning** how Neovim/LSP actually work. Recommended first step.
  ```bash
  git clone https://github.com/nvim-lua/kickstart.nvim ~/.config/nvim
  nvim   # first launch bootstraps lazy.nvim + plugins
  ```
- **LazyVim** — curated, batteries-included framework on lazy.nvim. **Best if you
  want a ready IDE** now and will customize later.
  ```bash
  git clone https://github.com/LazyVim/starter ~/.config/nvim && rm -rf ~/.config/nvim/.git
  nvim
  ```
- Also: AstroNvim, NvChad.

### Core plugins regardless of distribution

- **telescope.nvim** (fzf-native) — fuzzy files/grep/symbols.
- **nvim-treesitter** — accurate syntax/indent/textobjects.
- **nvim-lspconfig + mason.nvim** — LSP servers installed/managed in-editor.
- **nvim-cmp** or **blink.cmp** — completion.
- **gitsigns.nvim**, **which-key.nvim**, **conform.nvim** (format), **nvim-lint**.

### LSP wiring (the point of the setup)

Use `mason.nvim` to install servers, then attach via `nvim-lspconfig`. Typical
servers for this skill's languages: `rust_analyzer`, `basedpyright` + `ruff`,
`ruby_lsp`, `ts_ls` (typescript-language-server) + `biome`. See
[language-toolchains.md](language-toolchains.md) for the per-language LSP list.
Verify a server attached with `:LspInfo` and `:checkhealth`.

## 2. VS Code

Broadest ecosystem and the **best remote story** (Remote-SSH, Dev Containers,
WSL). Install the **deb/rpm from Microsoft's repo** for smooth full-toolchain
access — the Flatpak runs sandboxed and complicates toolchain access. Consider
**VSCodium** (telemetry-free build) to avoid MS telemetry.

```bash
# Debian/Ubuntu (Microsoft repo)
sudo install -D -o root -g root -m 644 <(wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor) \
  /usr/share/keyrings/microsoft.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/code stable main" \
  | sudo tee /etc/apt/sources.list.d/vscode.list
sudo apt update && sudo apt install code
```

Power-user config:

- **Settings Sync** — sign in to sync settings/keybindings/extensions across
  machines (`Settings Sync: Turn On`).
- **Remote-SSH** + **Dev Containers** — edit on the remote GPU box or in a
  reproducible container; extensions and language servers run remote. Best-in-
  class for remote GPU work (see [containers.md](containers.md) and
  [../templates/devcontainer.json](../templates/devcontainer.json)).
- **Baseline extensions:** language packs (rust-analyzer, Python/Pylance, gopls),
  GitLens, Error Lens, Even Better TOML.
- **Keybindings** — customize via `keybindings.json`; keep them close to your
  Neovim/tmux muscle memory if you switch often.

## 3. Zed

Rust, GPU-accelerated, extremely fast, collaborative, built-in AI (Agent Panel),
growing extension ecosystem. **Remote development goes directly over SSH** (no
Zed servers since v0.157; needs **≥ v0.159**) with a headless server on the
remote — a good fit for remote GPU boxes. Linux x86_64/arm64 supported.

```bash
curl -f https://zed.dev/install.sh | sh
zed --version
```

Config lives in `~/.config/zed/settings.json` (JSON with comments). Set the
language servers, formatter-on-save, and the AI panel provider there. For remote
GPU boxes, add hosts to Zed's remote projects and let it spawn the headless
server over SSH.

**Recommendation:** Zed as a fast daily driver where its language support is
mature; VS Code when you need a specific extension or the most robust
remote/devcontainer support; Neovim for terminal-centric/remote-everywhere
workflows.

## Verify

```bash
nvim --version | head -1      # expect >= 0.10; run :checkhealth inside nvim
code --version                # or: codium --version
zed --version                 # expect >= 0.159 for remote SSH
```
