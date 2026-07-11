# Local LLM Inference

Pick an engine, size a model to your VRAM, run it as a service, expose it safely,
and tune it. All version/model/flag specifics are **as of 2026-07 — verify** against
project docs before relying on exact values (this space changes weekly).

## 1. Engine selection matrix

| Engine | Best for | Formats | Multi-user throughput | CPU offload | GPU vendors | API |
|---|---|---|---|---|---|---|
| **Ollama** | individuals, dev boxes, agents | GGUF | medium | yes (auto) | NV/AMD/Apple | OpenAI + native |
| **llama.cpp / `llama-server`** | control, laptops, exotic HW, MoE-on-CPU | GGUF | medium | **best** | NV/AMD/Intel/Apple/CPU/Vulkan | OpenAI + Anthropic |
| **vLLM** | fleet serving, high QPS | safetensors, AWQ/GPTQ/FP8/FP4 | **highest** | no | NV/AMD/TPU/NPU/Apple | OpenAI |
| **SGLang** | agents / shared-prefix, day-0 models | safetensors, FP4/FP8/INT4/AWQ/GPTQ | **highest** | no | NV/AMD/Intel/TPU/NPU | OpenAI |
| **LM Studio** | GUI users, desktop server | GGUF/MLX | low-medium | yes | NV/AMD/Apple | OpenAI + Anthropic |
| **text-generation-webui** | all-in-one UI + LoRA training | GGUF/EXL3/HF/TRT-LLM | low-medium | yes | NV/AMD/Intel/Apple/CPU | OpenAI + Anthropic |
| **ExLlamaV3 + TabbyAPI** | max quality-per-VRAM, power users | EXL3/EXL2 | low-medium | limited | NVIDIA | OpenAI |
| **mlc-llm** | mobile / web / edge / exotic | MLC-compiled | n/a | varies | broad + WebGPU | varies |

**Decision flow**

1. Just want it working / manage models → **Ollama** (or **LM Studio** for a GUI).
2. Need control, weird hardware, or run-a-huge-model-on-small-VRAM → **llama.cpp**.
3. Serving many users/agents on a real GPU → **vLLM** (raw QPS) or **SGLang**
   (shared prefixes / newest models).
4. Cramming the biggest, best model into consumer VRAM → **ExLlamaV3 + TabbyAPI (EXL3)**.
5. Fronting several engines / team keys / cost tracking / cloud fallback → add
   **LiteLLM** (see model-wiring.md).

## 2. Install and run each engine

### Ollama — the default
```bash
curl -fsSL https://ollama.com/install.sh | sh   # installs + a systemd service
ollama run qwen3            # pull + chat (as of 2026-07 — verify tags)
ollama pull llama3.3:70b    # pull only
ollama ps                   # loaded models + GPU/CPU split
```
APIs: native REST at `http://localhost:11434/api/{generate,chat,embeddings}` and
OpenAI-compatible at `http://localhost:11434/v1/...`. GPU notes: NVIDIA needs
compute capability 5.0+ and driver ≥550 (CC 5.0–6.2 need ≥570); AMD via ROCm and
Apple Metal supported. Select GPUs with `CUDA_VISIBLE_DEVICES` (UUIDs are more
reliable than indices). Common footgun: default context is **4096** — raise it (see
§6). Ollama has **no built-in auth** — front it with a reverse proxy.

### llama.cpp / `llama-server` — the flexible workhorse
```bash
brew install llama.cpp   # or winget / nix / conda-forge / Docker / prebuilt release
llama-server -hf ggml-org/gpt-oss-20b-GGUF:Q4_K_M \
  --host 0.0.0.0 --port 8080 --api-key mykey \
  -ngl auto -c 8192 -fa on -ctk q8_0 -ctv q8_0
```
`-hf user/model[:quant]` defaults to `Q4_K_M` and shares the standard HF cache.
Speaks both OpenAI-compatible and **Anthropic Messages** APIs; has `--embeddings`
and `--rerank` modes, speculative decoding, schema-constrained JSON, `/metrics`.
GPU matrix: CUDA (NVIDIA), HIP/ROCm (AMD), **Vulkan** (vendor-agnostic incl.
older/AMD/Intel), SYCL (Intel GPU), Metal (Apple), CPU. Vulkan is the pragmatic
path for AMD/Intel consumer cards. `ik_llama.cpp` (fork) is faster for CPU/hybrid MoE.

### vLLM — high-throughput GPU serving
```bash
uv venv --python 3.12 --seed && source .venv/bin/activate
uv pip install vllm --torch-backend=auto
vllm serve Qwen/Qwen3-8B --port 8000       # OpenAI API at :8000/v1
```
Levers: `--tensor-parallel-size N`, `--gpu-memory-utilization` (default ~0.9,
lower if OOM), `--max-model-len`, `--max-num-seqs`, `--quantization`
(AWQ/GPTQ/FP8/INT4/NVFP4). Likes headroom (pre-reserves KV cache): a 7–8B model at
fp16 wants ~16–20GB; on tight consumer cards use an AWQ/GPTQ/FP8 build and cap
`--max-model-len`. AMD ROCm via the rocm extra index.

### SGLang — throughput + agentic workloads
```bash
pip install "sglang[all]"
python -m sglang.launch_server --model-path Qwen/Qwen3-8B --port 30000
```
**RadixAttention** (automatic prefix/KV reuse) makes it excellent for agents and
shared-prefix traffic; day-0 support for new open models. Comparable to vLLM for
raw serving; both expose an OpenAI API.

### ExLlamaV3 + TabbyAPI — best quant-per-VRAM (NVIDIA)
```bash
docker run --gpus all -p 5000:5000 -v /path/to/models:/app/models \
  ghcr.io/theroyallab/tabbyapi:latest
```
EXL3 (streamlined QTIP variant) hits SOTA quality-per-bit; a 3–4 bpw EXL3 often
matches much larger GGUF quants; 2–8-bit KV cache quantization. TabbyAPI is an
OpenAI-compatible server explicitly aimed at hobby/small-user use, not a fleet.

### LM Studio / text-generation-webui / mlc-llm
LM Studio: GUI + headless service (`lms` CLI), OpenAI + Anthropic endpoints, default
port `1234`, MCP + idle TTL. text-generation-webui: all-in-one UI, multiple
switchable backends, LoRA training. mlc-llm: compile-and-deploy to mobile/web/edge.

## 3. Quantization formats (2026)

Effective **bits-per-weight (bpw)** — not the nominal name — drives VRAM and
quality; an **imatrix** during conversion minimizes loss.

- **GGUF (llama.cpp)** — universal CPU/GPU. `Q4_K_M` (~4.8 bpw) is the everyday
  default (best size/quality knee); `Q5_K_M` (~5.7) for a bit more; `Q6_K` (~6.6)
  near-lossless; `Q8_0` (~8.5) effectively lossless. **i-quants** (`IQ2_XXS…IQ4_XS`)
  give better quality-per-bit at very low bpw (need imatrix). **MXFP4** is the
  native 4-bit format used by gpt-oss.
- **AWQ** — 4-bit weight-only, calibration-based; great quality, fast on GPU;
  first-class in vLLM/SGLang. Best for GPU-only high-throughput.
- **GPTQ** — older 4-bit PTQ; widely available, largely superseded by AWQ/EXL3.
- **EXL2 / EXL3** — mixed-bitrate (EXL2) and QTIP/trellis SOTA-per-bit (EXL3),
  NVIDIA-focused; best quality-per-VRAM on consumer GPUs.
- **FP8 / NVFP4 / INT8** — datacenter/Blackwell-oriented; use where the GPU has
  native FP8/FP4 tensor cores.

Rule: above ~5 bpw quality differences are small; **4–5 bpw is the sweet spot**;
below ~3 bpw quality drops fast. Larger models tolerate heavier quant better than
small ones (a 4-bit 70B beats an 8-bit 8B at similar VRAM).

## 4. Sizing a model to your VRAM

```
weights_GB ≈ params_billion × (bpw / 8) × 1.2      # 1.2 ≈ runtime overhead
# Q4_K_M (~4.8 bpw) ≈ 0.6 GB/B   Q6_K ≈ 0.8   Q8_0 ≈ 1.1   FP16 ≈ 2.0
kv_GB ≈ 2 × n_layers × n_kv_heads × head_dim × ctx_tokens × kv_bytes / 1e9
# kv_bytes: f16=2, q8_0=1, q4_0=0.5
```
Shortcut: **GGUF file size on disk ≈ weight VRAM**; add headroom + KV cache. Modern
models use GQA so KV is smaller than dense estimates — but **long context, not
weights, is what usually OOMs you**. Cap `--ctx-size`/`--max-model-len` and quantize
the KV cache.

### Model-size → VRAM (single GPU; Q4_K_M unless noted; estimates)

| Params | Q4_K_M weights | Min VRAM (≤8K ctx) | Comfortable (32K, q8 KV) | FP16 (serving) |
|---|---|---|---|---|
| 1–2B | ~1 GB | 2–3 GB | 3–4 GB | ~4 GB |
| 3–4B | ~2.5 GB | 4–5 GB | 6 GB | ~8 GB |
| 7–9B | ~5 GB | 6–8 GB | 10–12 GB | 16–20 GB |
| 12–14B | ~8 GB | 10–12 GB | 14–16 GB | ~28 GB |
| 24–32B | ~18 GB | 20–24 GB | 28–32 GB | 48–64 GB |
| 70B | ~40 GB | 44–48 GB | 56–64 GB | ~140 GB (multi-GPU) |
| 120B MoE (gpt-oss) | ~63 GB (MXFP4) | 1×80GB or 2×48GB, or CPU-offload MoE | — | multi-GPU |
| 235B+ MoE | 130GB+ | multi-GPU / heavy CPU offload | — | cluster |

### VRAM tier → tiered model recommendations (as of 2026-07 — verify)

| GPU VRAM | Sweet spot | Examples |
|---|---|---|
| **8 GB** (3050/4060, laptops) | 3–8B @ Q4, short ctx | Qwen3-4B/8B, Gemma 3 4B, Llama 3.x 8B, Phi-4-mini |
| **12 GB** (3060/4070) | 8–14B @ Q4–Q5 | Qwen3-14B, Gemma 3 12B, gpt-oss-20B (offload MoE) |
| **16 GB** (4060 Ti 16G/4070 Ti S) | 14B comfy / 24–32B tight | Qwen3-14B, Mistral Small, gpt-oss-20B |
| **24 GB** (3090/4090/5090) | 24–32B @ Q4–Q5 | Qwen3-32B, Gemma 3 27B, gpt-oss-20B full |
| **48 GB** (RTX 6000 Ada/A6000, 2×24GB) | 70B @ Q4 (EXL3), 32B @ Q6/Q8 | Llama 3.3 70B, Qwen3-32B high-quality |
| **80–96GB / multi-GPU** | 70B fp8/awq serving, 120B MoE | gpt-oss-120B, Nemotron 3 Super, large MoE |
| **CPU-only / big RAM** | MoE with active-expert offload | gpt-oss, Qwen3-MoE via `-ncmoe` / ik_llama.cpp |

Coding-specific picks: **Qwen3-Coder**, **Devstral 2**, **Codestral**,
GLM-4.x-Coder-class, DeepSeek-Coder lineage — pair with FIM or an agent.

## 5. Storage, systemd, safe LAN exposure

**HF cache:** `HF_HOME` (default `~/.cache/huggingface`) controls the shared model
store; llama.cpp `-hf`, the `hf` CLI, and Transformers share it. Ollama keeps its
own store (`OLLAMA_MODELS`, blob format). Prefer one cache on a big disk + symlinks;
prune with `hf cache ls` / `hf cache rm`.

**systemd (Ollama example):**
```bash
sudo systemctl edit ollama.service
# [Service]
# Environment="OLLAMA_HOST=0.0.0.0:11434"
# Environment="OLLAMA_MODELS=/data/ollama"
# Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
sudo systemctl daemon-reload && sudo systemctl restart ollama
```
For llama-server/vLLM/TabbyAPI write your own unit (`ExecStart=... --host 0.0.0.0
--api-key ...`, `Restart=on-failure`, a dedicated `User=`).

**Safe LAN exposure (SAFETY PROTOCOL step 6):**
- Bind to `0.0.0.0` **only** on a trusted network; **always set an API key**
  (`--api-key` for llama-server; Ollama needs a reverse proxy since it has no auth).
- Put **Caddy/nginx** in front for TLS + auth, or use the **LiteLLM proxy** for
  keys + rate limiting; llama-server can do TLS directly (`--ssl-key-file/--ssl-cert-file`).
- For remote access without opening ports, use **Tailscale** or a **Cloudflare
  Tunnel** rather than exposing the port publicly. Restrict CORS
  (`OLLAMA_ORIGINS`) for browser clients.
- **Never** put a raw local LLM port on the public internet unauthenticated.

## 6. Tuning

- **Flash attention:** enable everywhere (`-fa on` / `OLLAMA_FLASH_ATTENTION=1`; on
  by default in vLLM/SGLang). Cuts attention memory and speeds prefill.
- **KV-cache quantization:** `q8_0` ≈ half the cache at ~no quality cost; `q4_0`
  quarter with small-medium loss (`OLLAMA_KV_CACHE_TYPE`, `-ctk/-ctv`; needs flash attn).
- **Context length:** the biggest VRAM lever after weights (`OLLAMA_CONTEXT_LENGTH`,
  `-c`, `--max-model-len`). Use YaRN/RoPE scaling to extend beyond the trained window.
- **Layer / CPU offload:** `-ngl` sets VRAM layers. For **MoE**, keep experts on CPU
  with `-cmoe`/`-ncmoe N` (or ik_llama.cpp) to run models far larger than your VRAM.
- **Speculative decoding:** a draft model → 1.5–3× decode speedups
  (`-md/--model-draft`, `--spec-type draft-eagle3|draft-mtp|ngram-*`; EAGLE/MTP in vLLM/SGLang).
- **Prompt/prefix caching:** llama-server `--cache-prompt`/`--cache-reuse`, SGLang
  RadixAttention, vLLM automatic prefix caching — big wins for repeated prompts/RAG.
- **Multi-GPU:** tensor parallel (`vLLM --tensor-parallel-size`, ExLlamaV3 TP,
  llama-server `-sm row/tensor`) for one big model.

**tok/s ballparks** (single-user, Q4, short ctx; estimates): 7–8B ≈ 20–40 on an
8GB card, 90–150 on a 4090/5090; 70B ≈ 10–18 on 48GB. MoE runs much faster than its
total-param size implies (only active experts compute). CPU-only 7–8B is single- to
low-double-digit tok/s. Monitor with `nvidia-smi`/`rocm-smi`/`nvtop`/`btop`,
llama-server & vLLM `/metrics`, and `ollama ps`. Track TTFT, tokens/sec, VRAM, and
KV/queue occupancy.

## 7. Embeddings + local RAG (brief)

Serve embeddings via llama-server `--embeddings`, Ollama `/v1/embeddings`, or HF
**Text Embeddings Inference (TEI)** (also serves rerankers). Popular local
embedders: BGE-M3/bge-large, GTE, E5-mistral, Nomic-embed, Qwen3-Embedding; rerank
with bge-reranker. Glue with LlamaIndex/LangChain + a vector DB (pgvector, Qdrant,
Milvus, Chroma). Pattern: TEI (embed) + vector DB + llama-server/vLLM (generate),
optionally fronted by LiteLLM.
