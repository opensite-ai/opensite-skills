# Remote / Cloud GPU

When local VRAM is not enough, rent a GPU: pick a provider, set up remote dev, sync
code and data, and connect over a private network. Provider pricing/features are
**as of 2026-07 — verify.**

## 1. When to go remote vs local

- **Local GPU** if you have a capable card (e.g. 24GB+ consumer GPU) and iterate
  constantly — no per-hour cost, lowest latency, best privacy. Good for dev, small
  models, LoRA, and inference.
- **Remote GPU** when you need big VRAM (A100/H100/B200), multi-GPU, short bursts, or
  do not want to own hardware. Pay per second/minute: spin up, train, spin down.

## 2. Providers (2026 landscape)

| Provider | Best for | Notes |
|---|---|---|
| **RunPod** | **default choice** | Widest GPU catalog, **per-second** billing, Pods (VMs) + Serverless (scale-to-zero, ~<200ms cold starts on ~half of requests), one-click UI, network volumes. |
| **Vast.ai** | **cheapest raw compute** | Marketplace of independent hosts; RTX 4090 often ~$0.25–0.30/hr, ~40–60% cheaper, but variable reliability/bandwidth. Great for cost-driven, interruption-tolerant jobs. |
| **Lambda** | **multi-GPU training** | SXM clusters (8×H100/8×B200), **no egress fees**, predictable per-minute pricing, on-demand + reserved. |
| **Modal** | **serverless inference / Python-native** | Define GPU functions in Python, autoscaling, cron; often better than RunPod Serverless for inference. |

Others worth knowing: Paperspace, CoreWeave (enterprise), Fly.io GPUs, Together /
Replicate (hosted inference).

## 3. Remote dev tooling

- **SSH** is the foundation — hardened ed25519 keys, `~/.ssh/config` host aliases,
  `ControlMaster` multiplexing for fast reconnects.
- **VS Code Remote-SSH / Dev Containers** — edits files on the remote with local UI;
  extensions + language servers run remote. Best-in-class for remote GPU boxes.
- **Zed remote** (≥ v0.159) — direct SSH, headless server on the remote, local UI +
  AI panel; fast alternative to VS Code Remote.
- **mosh** — resilient shell over UDP; survives roaming/flaky links and sleep/wake.
  Pair with tmux/Zellij so long jobs persist across disconnects. (mosh has no
  port-forwarding — keep SSH for that.)
- **Neovim over SSH + tmux** — the lowest-dependency remote workflow; works everywhere.

## 4. Syncing code & data

- **git** — canonical source of truth for code history (push/pull local ↔ remote).
- **rsync** — one-shot/scheduled sync of large artifacts, datasets, checkpoints
  (`rsync -avzP --exclude .git`). Best for big files git should not hold.
- **mutagen** — continuous, low-latency two-way sync for edit-locally/run-remotely;
  feels like a local filesystem without sshfs lag. Best for tight
  iterate-on-remote-GPU loops.
- Recommendation: **git** for history, **mutagen** for live iteration, **rsync** for
  datasets/checkpoints. Avoid sshfs for hot loops (latency).

## 5. Networking / tunneling

- **Tailscale** — WireGuard mesh VPN; connect laptop ↔ remote GPU ↔ home server by
  stable MagicDNS names regardless of NAT/IP. SSH over Tailscale, ACLs, ephemeral
  nodes for cloud instances. The easiest secure private networking for remote GPU
  boxes — prefer it over opening public ports.
- **cloudflared** (Cloudflare Tunnel) — expose a service (Jupyter, an inference API)
  via a public HTTPS hostname without opening ports; good for demos/webhooks. Add auth.
- Recommendation: **Tailscale** for private dev access; **cloudflared** only when you
  must expose an endpoint publicly. The same LAN-exposure safety rules from
  [local-llm-inference.md](local-llm-inference.md) apply to remote model servers.

## 6. Cost tips

- Prefer **per-second/per-minute** billing (RunPod) and **scale-to-zero serverless**
  (RunPod Serverless / Modal) for spiky workloads.
- Use **spot/interruptible/Vast marketplace** for fault-tolerant training with
  checkpointing.
- Watch **egress fees** (Lambda has none). Persist data on **network volumes** and
  shut down compute when idle. Cache datasets/models on the volume to avoid
  re-download.
- Right-size VRAM; use mixed precision/quantization (see
  [local-llm-inference.md](local-llm-inference.md)).
