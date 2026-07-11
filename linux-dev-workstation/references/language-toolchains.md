# Language Toolchains

Real depth for **Rust, Python, Ruby, and JavaScript/TypeScript** — each with
install, per-project pinning, an explicit **update/upgrade workflow**, and
LSP + linter/formatter. `mise` is the meta version-manager; `uv` owns Python;
`rustup` owns Rust. Versions "as of 2026-07 — verify."

## 0. mise — the meta version-manager

`mise` (Rust, formerly rtx) manages runtimes for 100s of languages, **plus env
vars (replaces direnv) and a task runner (replaces make)**. Reads
`.tool-versions` (asdf-compatible) and richer `mise.toml`. Installs prebuilt
binaries (Ruby/Node in ~15s).

```bash
curl https://mise.run | sh
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc     # or use shims for CI/IDEs
mise use --global node@lts ruby@3.4                # global defaults
mise use node@22 ruby@3.4                          # writes to local mise.toml (per-project pin)
```

Per-project pinning: run `mise use <tool>@<version>` inside the repo — it writes
`mise.toml` / `.tool-versions`, and mise auto-switches on `cd`. See
[../templates/mise.toml](../templates/mise.toml).

**Update mise + everything it manages:**

```bash
mise self-update            # upgrade mise itself
mise upgrade                # upgrade all installed tools to latest allowed by pins
mise upgrade node           # upgrade a single tool
mise outdated               # show what would change first (safe preview)
```

**Cross-cutting LSP / linter / formatter map (as of 2026-07 — verify):**

| Language | LSP | Linter | Formatter |
|----------|-----|--------|-----------|
| Rust | rust-analyzer | clippy | rustfmt |
| Python | basedpyright (or pyright) | ruff | ruff format |
| Ruby | ruby-lsp | rubocop | rubocop / syntax_tree |
| JS/TS | typescript-language-server | biome or eslint | biome or prettier |

---

## 1. Rust (rustup)

**rustup** is the canonical, non-negotiable installer — it manages toolchains,
targets, and components.

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
# adds ~/.cargo/bin to PATH; provides cargo, rustc, rustup
rustup component add clippy rustfmt rust-analyzer   # linter, formatter, LSP
cargo install cargo-binstall                        # fast prebuilt binary installs
cargo binstall cargo-nextest cargo-watch cargo-edit # example dev tools
```

**Per-project pinning** — commit a `rust-toolchain.toml` so everyone uses the
same toolchain (rustup auto-installs it on `cd`):

```toml
# rust-toolchain.toml
[toolchain]
channel = "1.89.0"          # or "stable" / "nightly-2026-06-01"
components = ["clippy", "rustfmt", "rust-analyzer"]
```

(`mise.toml` can also pin Rust via the `rust` key; pick one source of truth.)

**Update workflow:**

```bash
rustup update              # update all installed toolchains + rustup itself
rustup update stable       # just the stable channel
rustup toolchain list      # see what's installed
cargo install-update -a    # (via cargo-update) refresh installed cargo binaries
```

**Lint/format/LSP:** `cargo clippy --all-targets --all-features` (deny warnings
in CI with `-D warnings`), `cargo fmt`, and rust-analyzer for editors.

---

## 2. Python (uv default; pixi for ML)

**uv** (Astral, Rust) replaces pip, pip-tools, pipx, poetry, pyenv, virtualenv,
and twine; 10–100× faster than pip; a universal cross-platform lockfile
(`uv.lock`); installs & pins Python itself; runs tools (`uvx`) and PEP 723 inline
scripts.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.13            # install a Python
uv init myproj && cd myproj       # new project with pyproject.toml
uv add requests                   # add a dependency (updates uv.lock)
uv run python app.py              # run inside the managed env
uv tool install ruff basedpyright # global CLI tools (pipx-style)
```

**Per-project pinning** — `uv python pin 3.13` writes `.python-version`, and
`uv.lock` pins every dependency deterministically. Commit both. (Common pattern:
**uv owns Python + project envs**; mise owns everything else.)

**Update workflow:**

```bash
uv self update            # upgrade uv itself
uv python upgrade         # upgrade managed Python patch versions
uv lock --upgrade         # bump all deps to latest allowed by pyproject constraints
uv lock --upgrade-package requests   # bump just one
uv tool upgrade --all     # upgrade global tools
```

**ML / scientific Python → pixi.** Uses conda-forge (30k+ native packages incl.
CUDA) **and** PyPI via uv, with built-in lockfiles and `pixi global`. Best for
CUDA/conda-forge native deps + full reproducibility. `pixi init`, `pixi add
pytorch`, `pixi run <cmd>`; update with `pixi update`. (conda/mamba only for
legacy envs.) GPU/ML framework install belongs in the `linux-ai-dev-stack` skill.

**Lint/format/LSP:** **ruff** (`ruff check` + `ruff format` — one fast tool
replacing flake8/isort/black), **basedpyright** (or pyright) for type checking +
LSP. Add `ruff` and `basedpyright` to `[tool.uv]` dev deps or install as uv tools.

---

## 3. Ruby (mise; ruby-lsp + rubocop)

Manage Rubies with **mise** (fast prebuilt installs) or `ruby-install`/`rbenv`.

```bash
mise use ruby@3.4                 # per-project pin (writes mise.toml/.tool-versions)
mise use --global ruby@3.4        # global default
gem install bundler               # per-project dependency manager
bundle init && bundle add rails   # add gems (updates Gemfile + Gemfile.lock)
gem install ruby-lsp rubocop      # LSP + linter/formatter
```

**Per-project pinning** — `mise.toml`/`.tool-versions` pin the Ruby version;
`Gemfile.lock` pins gems. Commit both.

**Update workflow:**

```bash
mise upgrade ruby         # newer patch/minor Ruby (respecting the pin)
mise use ruby@3.4.5       # or move the pin explicitly
gem update --system       # update RubyGems itself
bundle update             # update all gems to latest allowed by Gemfile
bundle update rails       # update one gem + its deps
bundle outdated           # preview available updates first
```

Re-run `bundle install` after switching Ruby versions (native extensions rebuild
per-Ruby). **Lint/format/LSP:** rubocop (`rubocop -A` to autocorrect), ruby-lsp
in editors (it can drive rubocop diagnostics + formatting).

---

## 4. JavaScript / TypeScript (Node via mise; pnpm; biome)

Manage Node with **mise** (`mise use node@lts`) or **fnm** (Rust, `.nvmrc`-aware)
if you only need Node. Avoid `nvm` (slow bash) for new setups.

```bash
mise use node@lts                 # per-project pin (writes mise.toml/.tool-versions)
corepack enable                   # ship pnpm/yarn versions with the project
npm i -g pnpm                     # or via corepack
pnpm add -D typescript @biomejs/biome typescript-language-server
```

**Package managers — when to use each:**

- **pnpm** — default; fast, disk-efficient (content-addressed store), strict.
- **npm** — universal baseline; fine for simple projects and libraries.
- **yarn** (Berry) — if a project already standardizes on it.
- **bun** — fastest all-in-one (runtime + package manager + bundler); use where
  its runtime compat is acceptable.

**Per-project pinning** — pin Node in `mise.toml`/`.nvmrc`; pin the package
manager with `"packageManager": "pnpm@9.x"` in `package.json` (corepack enforces
it); commit the lockfile (`pnpm-lock.yaml`).

**Update workflow:**

```bash
mise upgrade node         # newer Node (respecting the pin) — or `mise use node@22`
corepack use pnpm@latest  # bump the pinned package manager
pnpm up                   # update deps within semver ranges
pnpm up --latest          # bump to latest, updating package.json ranges
pnpm outdated             # preview first
npm -g update             # if you keep any global npm tools
```

**Lint/format/LSP:** **biome** (one fast Rust tool: `biome check --write` for
lint + format) or the classic **eslint + prettier** pair; **typescript-language-
server** (`ts_ls`) for editors; `tsc --noEmit` for type checking in CI.

---

## Update cadence & safety

- **Preview before upgrading:** `mise outdated`, `uv lock --upgrade --dry-run`
  (inspect the diff), `bundle outdated`, `pnpm outdated`, `cargo install-update -l`.
- **Pin in git, upgrade deliberately.** Lockfiles (`uv.lock`, `Gemfile.lock`,
  `pnpm-lock.yaml`, `Cargo.lock`) are the safety net — commit them and let CI
  catch regressions.
- **Separate runtime bumps from dependency bumps.** Change the Ruby/Node/Python
  version in its own commit; run the test suite before bumping the dependency
  tree on top.
- **Rebuild native extensions after a runtime change** (Ruby gems, Python wheels
  with C extensions, node-gyp modules).
- For a systematic multi-package upgrade across ecosystems, defer to the
  `dependency-upgrade-orchestrator` skill.
