# Containers

Docker Engine vs Podman (rootless), Compose v2, image hygiene, and devcontainers.
Versions "as of 2026-07 — verify."

> **SAFETY:** adding a user to the `docker` group grants root-equivalent access
> to the host (the daemon runs as root). Confirm with the user; prefer **rootless
> Podman** or **rootless Docker** on a security-sensitive box.

## 1. Docker Engine vs Podman

- **Docker Engine** — most widely documented; daemon-based. The `docker` group is
  root-equivalent — treat it as such, or run rootless (below).
- **Podman** — daemonless, **rootless by default**, drop-in `docker` CLI
  compatibility (`alias docker=podman` works for most flows), integrates with
  systemd (`podman generate systemd` / Quadlet). Preferred for security.

```bash
# Docker Engine (Ubuntu/Debian, official repo)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"      # CONFIRM: root-equivalent; re-login after
docker run --rm hello-world

# Podman (rootless out of the box)
sudo apt install podman              # or dnf/pacman
podman run --rm hello-world
```

### Rootless Docker (if you want Docker without the root daemon)

```bash
dockerd-rootless-setuptool.sh install
systemctl --user enable --now docker
export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/docker.sock
```

## 2. Compose v2

Compose is now a Docker CLI plugin (`docker compose`, no hyphen). Podman provides
`podman compose` (wrapping compose) or the native `podman-compose`.

```bash
docker compose version
docker compose up -d          # start services from compose.yaml
docker compose down           # stop + remove
```

A minimal `compose.yaml`:

```yaml
services:
  db:
    image: postgres:17
    environment:
      POSTGRES_PASSWORD: devpassword
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
volumes:
  pgdata:
```

For a GPU-enabled Compose service (NVIDIA reservation) and full GPU passthrough,
see the `linux-ai-dev-stack` skill — that is where the AI/ML container work
lives. GPU driver + container-toolkit install is in
[gpu-drivers.md](gpu-drivers.md).

## 3. Image hygiene

- **Pin base image tags** (`postgres:17`, not `latest`); digest-pin for
  reproducibility (`image@sha256:...`).
- **Multi-stage builds** — compile in a builder stage, copy only artifacts into a
  slim runtime (`-slim`, `distroless`, or `alpine` where libc allows).
- **`.dockerignore`** to keep build context small (exclude `.git`, `node_modules`,
  data).
- **Non-root `USER`** in the image; least-privilege.
- **Prune regularly:** `docker system prune` / `podman system prune` (CONFIRM —
  removes stopped containers, dangling images, unused networks). Scan images with
  `trivy` or `docker scout`.

## 4. Dev Containers (containers.dev spec)

`.devcontainer/devcontainer.json` defines a Docker/Podman-based dev environment
consumed by **VS Code**, **GitHub Codespaces**, and the `devcontainer` CLI. This
is the **best cross-editor, team-friendly reproducibility** that doesn't require
teammates to learn Nix — ideal for onboarding and CI parity, and it works against
remote/GPU hosts. See [../templates/devcontainer.json](../templates/devcontainer.json).

```bash
npm i -g @devcontainers/cli
devcontainer up --workspace-folder .
devcontainer exec --workspace-folder . bash
```

Use **Features** (`ghcr.io/devcontainers/features/*`) to layer languages/tools
onto a base image instead of hand-writing a Dockerfile. Configure Podman as the
container engine in VS Code settings (`dev.containers.dockerPath: podman`) to run
devcontainers rootless.

## Verify

```bash
docker run --rm hello-world      # or: podman run --rm hello-world
docker compose version           # or: podman compose version
docker info | grep -i rootless   # confirm rootless mode if expected
```
