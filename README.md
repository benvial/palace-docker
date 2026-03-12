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
| `dev` | Built from Palace `main` branch | Weekly (Mondays) |

### GPU images (CUDA 12.6, Ubuntu 24.04)

| Tag | Architecture | GPUs | Updated |
|-----|-------------|------|---------|
| `latest-gpu-sm75` / `v0.16.0-gpu-sm75` / `v0.15.0-gpu-sm75` | Turing (sm75) | T4, RTX 2080 | On Palace release |
| `latest-gpu-sm80` / `v0.16.0-gpu-sm80` / `v0.15.0-gpu-sm80` | Ampere (sm80) | A100, A10, A30 | On Palace release |
| `latest-gpu-sm90` / `v0.16.0-gpu-sm90` / `v0.15.0-gpu-sm90` | Hopper (sm90) | H100, H200 | On Palace release |
| `dev-gpu-sm75` / `dev-gpu-sm80` / `dev-gpu-sm90` | All architectures | See above | Weekly (Mondays) |

> **Note:** GPU images require an NVIDIA driver ≥ r560 and the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) on the host.

### Build schedule

| Trigger | Images built |
|---------|-------------|
| Release published on this repo (e.g. `v0.16.0`) | CPU + GPU images for that Palace version only |
| Weekly (Monday 06:00 UTC) | `dev` CPU + GPU images from current Palace `main` |
| Manual (`workflow_dispatch`) | Any version on demand |

## Usage

### Pull the image

```bash
# CPU
docker pull ghcr.io/benvial/palace:latest

# GPU (choose the tag matching your GPU architecture)
docker pull ghcr.io/benvial/palace:latest-gpu-sm80

# Development build (rebuilt weekly from Palace main)
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
  mpirun -n 4 palace /sim/config.json
```

### Interactive shell

```bash
docker run --rm -it \
  -v /path/to/simulation:/sim \
  ghcr.io/benvial/palace:latest \
  bash
```