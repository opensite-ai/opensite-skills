# ML Frameworks & GPU Containers

Create a reproducible Python ML environment, install PyTorch/JAX/TensorFlow for your
compute platform (NVIDIA/AMD/Intel), run Jupyter and the HuggingFace stack, and set
up reproducible GPU containers. Versions are **as of 2026-07 — verify** against
`pytorch.org`, `docs.nvidia.com`, etc. Assumes GPU drivers already work
(`linux-dev-workstation`).

## 1. Python environment for ML

- **pixi** (prefix.dev, Rust) — modern successor to conda for reproducible ML. Uses
  **conda-forge** (30k+ packages) **and PyPI via uv**, built-in lockfiles, per-project
  `pixi.toml`, task runner, multi-env, first-class CUDA. Best when you need
  native/CUDA deps with full reproducibility.
- **uv** (Astral, Rust) — the fast default when deps are pure-PyPI wheels (PyTorch now
  ships good PyPI wheels): `uv init`, `uv add <pkg>`, `uv run <cmd>`,
  `uv python install 3.13`, `uv tool install ruff`.
- **conda/mamba** — only for legacy environments.

Common split: **uv owns Python + project envs**; use **pixi** for ML projects needing
conda-forge native deps. Never `pip install` ML packages globally — always per-project.

## 2. PyTorch / JAX / TensorFlow by compute platform

The **host needs only the GPU driver**; CUDA/ROCm userspace comes from the wheels or
the container. Match the driver ≥ the CUDA runtime version.

**PyTorch** (stable 2.7.0, needs Python 3.10+ — as of 2026-07 — verify). Pick from the
pytorch.org matrix:
```bash
# NVIDIA CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
# AMD ROCm (Linux only)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.3
# CPU-only
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```
With **uv**, add the PyTorch index in `pyproject.toml`
(`[[tool.uv.index]]` / `[tool.uv.sources]`) so CUDA wheels resolve deterministically.
With **pixi/conda-forge**, `pixi add pytorch` pulls CUDA-enabled builds.

- **Intel (Arc / Core Ultra):** use upstream **PyTorch XPU** wheels (IPEX is
  deprecated); NPU via `linux-npu-driver` + OpenVINO. Verify: `torch.xpu.is_available()`.
- **Apple Silicon (Asahi):** no CUDA/ROCm — use Metal/Vulkan paths and llama.cpp for
  inference; PyTorch MPS support is limited on Asahi.
- **JAX:** `pip install -U "jax[cuda12]"` (bundled CUDA libs) or `jax[cuda12_local]`
  against a system CUDA.
- **TensorFlow:** `pip install tensorflow[and-cuda]` (bundles CUDA/cuDNN, Linux) —
  less common than PyTorch/JAX for new work.

Verify the GPU is visible:
```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

## 3. Jupyter / JupyterLab

Per-project, never global: `uv add jupyterlab` / `pixi add jupyterlab`, then
`uv run jupyter lab` / `pixi run jupyter lab`. Register a kernel per env:
`python -m ipykernel install --user --name <env>`. VS Code / Zed notebook UIs or
JupyterLab Desktop make nicer front-ends. If serving Jupyter beyond localhost, front
it with auth + TLS or a Tailscale/cloudflared tunnel (see [remote-gpu.md](remote-gpu.md))
— never expose an unauthenticated notebook.

## 4. HuggingFace stack

Core: `transformers`, `datasets`, `accelerate`, `peft`, `safetensors`, and the
unified **`hf` CLI** (`huggingface-cli` is deprecated).
```bash
uv add transformers datasets accelerate
uv tool install "huggingface_hub[cli]"    # provides `hf`
hf auth login
pip install hf_transfer && export HF_HUB_ENABLE_HF_TRANSFER=1   # fast transfers
accelerate config                          # multi-GPU / mixed precision
```
Consolidate the model cache with `HF_HOME` (shared with llama.cpp `-hf` and
Transformers); prune with `hf cache ls` / `hf cache rm`.

## 5. Reproducible GPU containers

Install the **NVIDIA Container Toolkit** (currently 1.19.x — verify) so containers see
the GPU. (This overlaps with `linux-dev-workstation`'s containers reference — use one
source of truth.)
```bash
# Docker
sudo apt install nvidia-container-toolkit        # or dnf; add the NVIDIA repo first
sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi
```
**Podman (rootless, preferred for security)** via CDI:
```bash
sudo nvidia-ctk runtime configure --runtime=podman
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
podman run --device nvidia.com/gpu=all ...
```
**Rootless Docker:** `nvidia-ctk runtime configure --runtime=docker
--config=$HOME/.config/docker/daemon.json`, `systemctl --user restart docker`, and
`sudo nvidia-ctk config --set nvidia-container-cli.no-cgroups --in-place`.

Base images on `nvidia/cuda` or framework images (`pytorch/pytorch`, `rocm/pytorch`);
pin CUDA/cuDNN in the image; keep only the driver on the host. Podman rootless + CDI is
the most secure reproducible pattern; Docker is fine and most widely documented. A
ready Compose service with an NVIDIA GPU reservation is in
[../templates/gpu-compose.yaml](../templates/gpu-compose.yaml).
