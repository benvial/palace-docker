# Docker image for Palace

[![Build](https://img.shields.io/github/actions/workflow/status/benvial/palace-docker/build.yml?style=for-the-badge&logo=github&label=build+cpu)](https://github.com/benvial/palace-docker/actions/workflows/build.yml)
[![Build](https://img.shields.io/github/actions/workflow/status/benvial/palace-docker/build-gpu.yml?style=for-the-badge&logo=github&label=build+gpu)](https://github.com/benvial/palace-docker/actions/workflows/build.yml)
<!-- [![Version](https://img.shields.io/badge/palace-v0.16.0-blue?style=for-the-badge)](https://github.com/awslabs/palace/releases/tag/v0.16.0) -->
[![GHCR](https://img.shields.io/badge/ghcr.io-palace-green?style=for-the-badge&logo=github)](https://github.com/benvial/palace-docker/pkgs/container/palace)

[Palace](https://awslabs.github.io/palace/stable/) is an open-source, parallel finite element code for full-wave 3D electromagnetic simulations in the frequency or time domain.

Built images are available on the [GitHub Container Registry](https://github.com/benvial/palace-docker/pkgs/container/palace).

## Available Tags

### CPU images (Ubuntu 24.04)

| Tag | Description | Updated |
|-----|-------------|---------|
| `latest` | Latest stable release | On Palace release |
| `v0.16.0` | Palace v0.16.0 | Fixed |
| `v0.15.0` | Palace v0.15.0 | Fixed |
| `dev` | Built from Palace `main` branch | Weekly (Mondays), overwritten |

### GPU images (CUDA 12.6, Ubuntu 24.04)

| Tag | Architecture | GPUs | Updated |
|-----|-------------|------|---------|
| `latest-gpu-sm75` / `v0.16.0-gpu-sm75` / `v0.15.0-gpu-sm75` | Turing (sm75) | T4, RTX 2080 | On Palace release |
| `latest-gpu-sm80` / `v0.16.0-gpu-sm80` / `v0.15.0-gpu-sm80` | Ampere (sm80) | A100, A10, A30 | On Palace release |
| `latest-gpu-sm90` / `v0.16.0-gpu-sm90` / `v0.15.0-gpu-sm90` | Hopper (sm90) | H100, H200 | On Palace release |
| `dev-gpu-sm75` / `dev-gpu-sm80` / `dev-gpu-sm90` | All architectures | See above | Weekly (Mondays), overwritten |

> **Note:** GPU images require an NVIDIA driver ≥ r560 and the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) on the host.

### Build schedule

| Trigger | Images built |
|---------|-------------|
| Release published on this repo (e.g. `v0.16.0`) | CPU + GPU images for that Palace version only, plus `latest` |
| Weekly (Monday 06:00 UTC CPU, 07:00 UTC GPU) | `dev` CPU + GPU images from current Palace `main` |
| Manual (`workflow_dispatch`) | Any version on demand |

Version tags (`v0.16.0`, `v0.16.0-gpu-sm80`, …) are permanent. The `dev` tags are
moving pointers: each weekly build replaces the previous one, and the orphaned
manifest it leaves behind is deleted in the same run. Only the most recent `dev`
image exists for each of the four variants — there is no archive of past `dev`
builds. To reproduce an older one, rebuild from its Palace commit (see below).

### Manual builds

Both workflows accept a `build-type` — `dev`, or a Palace version tag or commit
SHA — and a `push-latest` flag that also moves `latest` (`latest-gpu-sm<arch>` for
GPU) onto the resulting image. `push-latest` is off by default; releases move
`latest` on their own, and the weekly build never does.

```bash
# rebuild the dev images from current Palace main
gh workflow run build.yml     -f build-type=dev
gh workflow run build-gpu.yml -f build-type=dev   # all three architectures

# build a specific Palace version and make it the new latest
gh workflow run build.yml -f build-type=v0.16.0 -f push-latest=true

# rebuild from a specific Palace commit
gh workflow run build.yml -f build-type=abc1234
```

The same inputs are available as a form under **Actions → Run workflow**.

## Usage

### Pull the image

```bash
# CPU
docker pull ghcr.io/benvial/palace:latest

# GPU (choose the tag matching your GPU architecture)
docker pull ghcr.io/benvial/palace:latest-gpu-sm80

# Development build (moving tag, rebuilt weekly from Palace main)
docker pull ghcr.io/benvial/palace:dev
docker pull ghcr.io/benvial/palace:dev-gpu-sm80
```

### Run a simulation

```bash
# CPU — mount your simulation directory and run palace
docker run --rm \
  -v /path/to/simulation:/sim \
  ghcr.io/benvial/palace:latest \
  palace /sim/config.json

# GPU — pass --gpus all and use the matching GPU image
docker run --rm --gpus all \
  -v /path/to/simulation:/sim \
  ghcr.io/benvial/palace:latest-gpu-sm80 \
  palace /sim/config.json

# Multi-process with MPI (CPU, 4 processes)
docker run --rm \
  -v /path/to/simulation:/sim \
  ghcr.io/benvial/palace:latest \
  palace -np 4 /sim/config.json
```

### MPI

Both the CPU and GPU images are built against OpenMPI 5.0.3, compiled from source
into `/usr/local`, and ship its launcher. `palace -np N config.json` runs a real
N-rank job with no extra flags.

> **Note:** CPU images through `v0.16.0` were built against Ubuntu's MPICH, whose
> launcher and client libraries do not interoperate: `-np N` there started N
> independent single-rank runs that overwrote each other's output. Parallel CPU
> runs need an image built after that — `dev`, or a version tag above `v0.16.0`.

### Interactive shell

```bash
docker run --rm -it \
  -v /path/to/simulation:/sim \
  ghcr.io/benvial/palace:latest \
  bash
```