# chezmoi Dotfiles Repo Layout

A recommended layout for a `dotfiles` repo managed by
[chezmoi](https://chezmoi.io) (source of truth in git; `chezmoi apply` renders
into `$HOME`). Replace `youruser` with your own values — never commit real
secrets in plaintext.

## Bootstrap a fresh machine

```bash
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- init --apply youruser
# later, on any machine:
chezmoi update        # git pull + re-apply
chezmoi doctor        # sanity check
```

## Repo structure

```
dotfiles/                          # your git repo (the chezmoi source dir)
├── .chezmoi.toml.tmpl             # prompts for machine-specific data on init
├── .chezmoiignore                 # paths to skip per-OS/host
├── dot_zshrc                      # -> ~/.zshrc
├── dot_gitconfig.tmpl             # -> ~/.gitconfig (templated per machine)
├── dot_tmux.conf                  # -> ~/.tmux.conf
├── dot_config/
│   ├── starship.toml              # -> ~/.config/starship.toml
│   ├── nvim/                      # -> ~/.config/nvim/ (or track upstream separately)
│   ├── ghostty/config             # -> ~/.config/ghostty/config
│   └── mise/config.toml           # -> ~/.config/mise/config.toml (global tools)
├── private_dot_ssh/
│   └── config.tmpl                # -> ~/.ssh/config (0600; never commit keys)
├── run_once_before_10-install-packages.sh.tmpl   # runs once, before apply
├── run_onchange_after_20-mise-install.sh.tmpl     # re-runs when its hash changes
└── encrypted_private_secrets.env.age              # age-encrypted, safe to commit
```

## Naming conventions (chezmoi attributes)

| Prefix | Meaning |
|--------|---------|
| `dot_` | becomes a leading `.` (`dot_zshrc` → `~/.zshrc`) |
| `private_` | file mode `0600` (owner-only) |
| `.tmpl` | rendered as a Go template (per-OS/host values) |
| `run_once_` | script runs once per machine (bootstrap installs) |
| `run_onchange_` | script re-runs when its contents change |
| `encrypted_` | decrypted on apply (age/gpg) — safe to commit ciphertext |

## Templating example (per-OS values)

```gotmpl
# dot_gitconfig.tmpl
[user]
    name = Your Name
    email = {{ .email }}
{{- if eq .chezmoi.os "linux" }}
[credential]
    helper = cache --timeout=3600
{{- end }}
```

## Secrets

Use `encrypted_` files with **age** (see references/security-hardening.md) or
reference a password manager (`{{ onepasswordRead "op://..." }}`). Never commit
plaintext tokens or private keys. Pair chezmoi (user dotfiles) with an Ansible
playbook (system packages) — see templates/ansible-workstation.yml.
