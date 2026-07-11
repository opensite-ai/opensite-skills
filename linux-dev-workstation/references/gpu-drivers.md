# GPU Drivers & Compute Stacks

Per-vendor, per-distro install + verify + gotchas. Covers NVIDIA, AMD (ROCm),
Apple Silicon (Asahi), Intel (Arc/NPU), and CPU-only fallback.
**All versions "as of 2026-07 — verify" with a web search before installing.**

> **SAFETY:** the driver stage is the one genuinely destructive stage in this
> skill. Blacklisting `nouveau`, DKMS rebuilds, MOK enrollment, and reboots can
> leave a black screen. Confirm with the user first, keep X11 as a fallback, and
> run the verify command **before** rebooting into a Wayland session.

## Headline status (2026)

| Vendor | Status for AI dev | Biggest gotcha |
|---|---|---|
| **NVIDIA** | Gold standard. `nvidia-open` is the default/required path for Turing+ (required on Blackwell RTX 50). CUDA 13.x + cuDNN 9.x. | Kernel-module mismatch after updates + Secure Boot MOK signing. Maxwell/Pascal/Volta still need the proprietary module. |
| **AMD** | Production-ready for inference (PyTorch + vLLM/SGLang). Stack is **ROCm 7.2.x**. | Short official consumer-GPU list; unlisted cards need `HSA_OVERRIDE_GFX_VERSION`. Training still trails CUDA. |
| **Apple/Asahi** | Excellent desktop Linux; not viable for serious ML. | No CUDA/ROCm/PyTorch-GPU; only llama.cpp Vulkan. M1/M2 only; M3/M4 not ready. |
| **Intel** | Viable and improving for Arc + Core Ultra. | IPEX archived (Mar 2026) — use upstream PyTorch XPU wheels. Thinner ecosystem. |
| **CPU-only** | Fine for small quantized inference, embeddings, CI. | Unusable for training or large models; memory-bandwidth bound. |

Detect the vendor first: `lspci | grep -Ei 'vga|3d|display'`.

---

## 1. NVIDIA

### Open vs proprietary kernel modules (the key decision)

- **Turing / Ampere / Ada / Hopper** (RTX 20/30/40, GTX 16, A/H-series) → use
  `nvidia-open` (recommended by upstream).
- **Blackwell (RTX 50) / Grace Hopper** → **must** use open modules; proprietary
  is unsupported.
- **Maxwell / Pascal / Volta** (GTX 9/10, Titan V) → open modules are **not**
  compatible; keep the **proprietary** module (newer feature branches drop these
  cards entirely).
- Only the kernel module is open; CUDA userspace stays proprietary (still needs
  `allowUnfree` on NixOS).

**Branches (as of 2026-07 — verify):** `580.x` is the current LTSB/production
branch; `590`/`595` are newer feature branches; `570`/`575` are superseded. Use
`580 LTSB` for stability, or match what your distro ships.

### Per-distro install

```bash
# Ubuntu — recommended path
ubuntu-drivers devices                    # shows recommended driver
sudo ubuntu-drivers install               # installs recommended (often -open)
sudo apt install nvidia-driver-580-open   # or pin the open variant explicitly
# Debian 13: enable non-free-firmware + contrib, then:
sudo apt install nvidia-open-kernel-dkms nvidia-driver
```

```bash
# Fedora — RPM Fusion + akmods (native way)
sudo dnf install \
  https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm \
  https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
sudo dnf install akmod-nvidia-open xorg-x11-drv-nvidia-cuda  # open module variant
sudo akmods --force && sudo dracut --force   # build for current kernel; auto-rebuilds on updates
```

```bash
# Arch — open modules are the MAIN packages for Turing+/Blackwell
sudo pacman -S nvidia-open        # for the 'linux' kernel
sudo pacman -S nvidia-open-dkms   # any kernel (rebuilds per-kernel via DKMS)
sudo pacman -S nvidia-open-lts    # for 'linux-lts'
# Maxwell/Pascal (dropped from main): AUR proprietary, e.g. nvidia-580xx-dkms
```

```nix
# NixOS (configuration.nix)
hardware.graphics.enable = true;
services.xserver.videoDrivers = [ "nvidia" ];
hardware.nvidia.open = true;                    # false = proprietary (Maxwell–Volta)
hardware.nvidia.package = config.boot.kernelPackages.nvidiaPackages.production;
nixpkgs.config.allowUnfree = true;
```

### CUDA Toolkit + cuDNN

Order that matters: **Driver → CUDA Toolkit → cuDNN → framework.** CUDA 13.x is
current (13.2 latest supported by PyTorch early 2026); cuDNN 9.x. The CUDA
runtime bundled with a PyTorch wheel does **not** need to match a system CUDA
toolkit — only the *driver* must be new enough. Most users skip a system CUDA
install and let the wheel bring its own runtime.

```bash
# System CUDA (Ubuntu 24.04) — optional; only if you compile CUDA yourself
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb && sudo apt update
sudo apt install cuda-toolkit-13-0 cudnn9-cuda-13
# Add to shell profile:
# export PATH=/usr/local/cuda/bin:$PATH
# export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```

### Secure Boot (MOK signing)

Unsigned out-of-tree modules won't load under Secure Boot → silent fallback to
`nouveau` / no accel. **Confirm with the user before enrolling a key** (requires
a reboot into MOK Manager).

```bash
sudo openssl req -new -x509 -newkey rsa:2048 -keyout /root/MOK.priv -out /root/MOK.der \
  -nodes -days 36500 -subj "/CN=Local NVIDIA MOK/"
sudo mokutil --import /root/MOK.der   # set a one-time password; reboot → Enroll MOK
# Point DKMS at the key so every rebuild is signed:
# /etc/dkms/nvidia.conf -> mok_signing_key=/root/MOK.priv  mok_certificate=/root/MOK.der
```

Fedora: enroll the RPM Fusion akmods key (`/etc/pki/akmods/certs/public_key.der`)
via `mokutil`. Single-user escape hatch: disable Secure Boot in firmware.

### Containers (nvidia-container-toolkit + CDI)

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install nvidia-container-toolkit   # ~1.19.x as of 2026-07

sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu24.04 nvidia-smi

# CDI (modern, vendor-neutral — required for Podman, default in Docker >= 28.3.0)
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml   # regenerate after driver updates
podman run --rm --device nvidia.com/gpu=all nvidia/cuda:12.4.1-base-ubuntu24.04 nvidia-smi
```

Known issue: on systemd-cgroup hosts, `systemctl daemon-reload` can make running
containers lose GPU access ("Failed to initialize NVML") — restart the container.
See [containers.md](containers.md) for rootless details.

### Wayland (2026)

Usable for daily driving since driver **555+** (explicit-sync + GBM), polished
through 580/590. GNOME/KDE default to Wayland. Needs an explicit-sync compositor
(wlroots ≥0.19 / Sway ≥1.11, KWin, Mutter). Rough edges: some mixed-refresh
multi-monitor and hybrid-GPU (Optimus/PRIME) laptops. **X11 remains the safe
fallback** — keep it available before rebooting.

### Common failure modes

- **`nouveau` conflict** — blacklist it (`/etc/modprobe.d/blacklist-nouveau.conf`
  → `blacklist nouveau` + `options nouveau modeset=0`), rebuild initramfs
  (`update-initramfs -u` / `dracut --force`). Distro packages usually do this.
- **Kernel-module mismatch after update** — fix with **DKMS** (`-dkms`) or
  **akmods** (Fedora); ensure `linux-headers`/`kernel-devel` for the running
  kernel are installed.
- **Secure Boot** — unsigned module refused → MOK section above.
- **GSP firmware bugs** (some Ampere laptops) — boot with
  `nvidia.NVreg_EnableGpuFirmware=0`.
- **Version skew** — `CUDA driver version is insufficient` → update the driver,
  not necessarily the toolkit.

### Verify

```bash
nvidia-smi                              # driver + GPU + processes; must succeed
cat /proc/driver/nvidia/version
nvcc --version                          # if system CUDA installed
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
nvtop                                   # live utilization
```

---

## 2. AMD (ROCm)

Current stack is **ROCm 7.2.x** (7.2.4 stable; 7.13 tech preview) — not 6.x.
`amdgpu` is in-kernel (display works without extra drivers); ROCm adds the
compute stack at `/dev/kfd`.

### Officially supported compute GPUs

- **CDNA Instinct:** MI350X/MI355X (gfx950), MI300X/A/MI325X (gfx942), MI200
  (gfx90a), MI100 (gfx908).
- **RDNA4:** Radeon AI PRO R9700 / RX 9070 family (gfx1200/gfx1201).
- **RDNA3:** RX 7900 XTX/XT/GRE (gfx1100), RX 7700/7800 (gfx1101), PRO W7900/W7800.
- **RDNA2:** gfx1030 (RX 6800/6900) — limited/legacy.
- Not listed = not officially supported; try TheRock nightly builds.

### Install (per-distro)

```bash
# Ubuntu 24.04/22.04 — amdgpu-install
wget https://repo.radeon.com/amdgpu-install/7.2.4/ubuntu/noble/amdgpu-install_7.2.4.xxxxx_all.deb
sudo apt install ./amdgpu-install_*.deb
sudo amdgpu-install --usecase=rocm       # or graphics,rocm
sudo usermod -aG render,video $USER      # REQUIRED for /dev/kfd + /dev/dri; re-login after
# Fedora: sudo dnf install rocm-hip rocminfo rocm-smi
# Arch:   sudo pacman -S rocm-hip-sdk rocm-opencl-sdk
# NixOS:  rocmPackages.* + rocmSupport overlay
```

Supported hosts (ROCm 7.2.x): Ubuntu 24.04.4/22.04.5, RHEL 8.10/9.x/10.x,
Debian 12/13, SLES 15 SP7, Oracle/Rocky.

### Unlisted consumer GPUs — HSA_OVERRIDE_GFX_VERSION

```bash
export HSA_OVERRIDE_GFX_VERSION=11.0.0   # unlisted RDNA3 / RDNA3 APU -> pretend gfx1100
export HSA_OVERRIDE_GFX_VERSION=10.3.0   # unlisted RDNA2 -> pretend gfx1030
```

Overriding *within* a generation is usually safe (gfx1031→gfx1030);
**cross-generation overrides fail** — never map RDNA2 to 11.0.0. Known
regression: ROCm 6.4.3+ SIGSEGVs on gfx1031/gfx1032 — downgrade to 6.4.1. Ollama
and llama.cpp honor the same variable and ship the widest de-facto consumer
support.

### PyTorch on ROCm

```bash
# Prebuilt Docker (avoids host mismatch) — recommended
docker pull rocm/pytorch:latest
docker run -it --cap-add=SYS_PTRACE --security-opt seccomp=unconfined \
  --device=/dev/kfd --device=/dev/dri --group-add video --ipc=host --shm-size 8G \
  rocm/pytorch:latest
# Or pip wheels (stable ROCm 6.4):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.4
```

The ROCm PyTorch build reuses the CUDA API — `torch.cuda.is_available()`,
`.to("cuda")` all work unchanged on AMD. Containers need no toolkit; just pass
`--device=/dev/kfd --device=/dev/dri --group-add video`.

### Reality vs CUDA

Inference is production-ready (PyTorch/vLLM/SGLang; RX 7900 XTX 24 GB is the
value pick). Training still trails (MI300X ~37–66% of H100 real LLM throughput;
FlashAttention 3 / TensorRT-LLM are CUDA-only or immature). **Run Linux, not
Windows.** Choose NVIDIA if you train or need bleeding-edge kernels.

### Verify

```bash
rocminfo | grep -A2 "Name:"                 # agents incl. your gfx target
rocm-smi                                     # util / temp / VRAM
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
groups | grep -E 'render|video'              # must be in both
```

---

## 3. Apple Silicon — Asahi Linux (Fedora Asahi Remix)

- **Fedora Asahi Remix** (based on Fedora 44) is the flagship; install via
  `curl https://alx.sh | sh` **from macOS**. KDE Plasma flagship, 100% Wayland.
- **Supported hardware: M1 and M2 only.** M3/M4 GPU support is not ready.
- Graphics is excellent: the "Honeykrisp" driver gives conformant **Vulkan 1.4**,
  OpenGL 4.6, OpenGL ES 3.2, OpenCL 3.0.

### ML viability — the hard truth

- **No CUDA, no ROCm, no vendor compute stack.** ANE is unused on Linux.
- **PyTorch on Asahi = CPU only.** The `mps` backend is macOS/Metal-exclusive.
- **MLX does not run on Asahi** (macOS ≥14 only; it gained a CUDA backend for
  NVIDIA/Linux, but no Apple-GPU-on-Linux backend).
- **What works:** `llama.cpp` with the **Vulkan** backend runs GPU-accelerated
  inference on the Asahi GPU — essentially the only GPU ML path here.
- **Bottom line:** superb desktop/dev Linux on M1/M2; for real Apple AI work use
  **macOS + MLX/Metal**. Use Asahi for coding, not training/serving.

### Verify

```bash
glxinfo -B | grep "OpenGL renderer"           # expect Asahi/Apple GPU
vulkaninfo --summary | grep deviceName        # Vulkan 1.4 device present
python -c "import torch; print(torch.backends.mps.is_available())"  # -> False (expected)
# ML: build llama.cpp with -DGGML_VULKAN=ON, then ./llama-cli --list-devices
```

---

## 4. Intel (Arc GPUs, oneAPI, NPU)

**IPEX was archived 2026-03-30** — its functionality is upstreamed. Use the
native PyTorch **`xpu`** backend; no separate `intel_extension_for_pytorch`
import needed.

### Arc GPU + oneAPI / Level Zero

- GPUs: Arc **Alchemist** (A-series, A770 16 GB) and **Battlemage** (B-series).
  Kernel `i915`/`xe`; comms via **Level Zero**.
- Recommended host: Ubuntu 24.04, kernel ≥6.5 (6.14 for NPU).

```bash
# PyTorch XPU (stable) — brings its own runtime
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/xpu
python -c "import torch; print(torch.xpu.is_available(), torch.xpu.get_device_name(0))"
# For building/oneDNN/oneMKL: install oneAPI Base Toolkit (2025.x),
# then `source /opt/intel/oneapi/setvars.sh`
```

Integrated GPU (Iris Xe / Arc iGPU in Core Ultra) uses the same XPU path.

### NPU (Core Ultra)

Hardware: Meteor Lake, Arrow Lake, Lunar Lake, Panther Lake. Stack: kernel
`ivpu` + `linux-npu-driver` (v1.28+) + Level Zero (v1.24.x) + **OpenVINO 2025.4**
"NPU" plugin. NPU is for efficient INT8 inference, not training.

```bash
pip install openvino
python -c "import openvino as ov; print(ov.Core().available_devices)"  # expect ['CPU','GPU','NPU']
```

### Verify

```bash
clinfo | grep "Device Name"                   # Intel Arc via Level Zero/OpenCL
intel_gpu_top                                  # from intel-gpu-tools
xpu-smi discovery                              # if installed
python -c "import torch; print(torch.xpu.is_available(), torch.xpu.get_device_name(0))"
```

Verdict: cheaper VRAM/$ than NVIDIA, good for local inference (llama.cpp
SYCL/Vulkan, OpenVINO, vLLM-xpu); thinner, churning ecosystem. A fine secondary
inference box, not a first training choice.

---

## 5. CPU-only fallback

**Good enough for:** quantized inference of small models (≤7B, Q4_K_M) via
llama.cpp/Ollama; embeddings, classical ML (sklearn/XGBoost), sentence
transformers; dev, unit tests, CI, model-conversion/quantization.

**Not acceptable for:** any real training/fine-tuning; models ≳13B at
interactive speed; high-throughput serving; diffusion image/video.

Rule: if it fits in RAM and you tolerate low tok/s, CPU is fine. llama.cpp and
Ollama auto-fall back to CPU (or split CPU/GPU layers) transparently.

```bash
python -c "import torch; print(torch.__version__, torch.get_num_threads())"
ollama run llama3.2:3b "hello"                 # verifies CPU inference path
```

---

## VRAM sizing (pointer)

Rule of thumb: **~0.5 GB VRAM per billion params at Q4** + KV cache + ~15–20%
overhead. 7B@Q4 ≈ 5–6 GB (8 GB card); 13B@Q4 ≈ 8–10 GB (12 GB); 70B@Q4 ≈ ~40 GB
(one 48 GB card or 2× 24 GB). VRAM matters more than raw FLOPs for LLM dev. For
model selection by VRAM tier, engine choice, and multi-GPU/eGPU, defer to the
`linux-ai-dev-stack` skill.
