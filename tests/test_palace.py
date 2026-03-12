# test_palace.py
#
# Run basic infrastructure checks and all 4 Palace example simulations on Modal.
# Palace parallelism is controlled via its own CLI flags (-np for MPI, -nt for OpenMP).
#
# Usage:
#   modal run test_palace.py                                         # GPU, latest-gpu-sm80
#   modal run test_palace.py --mode cpu                              # CPU, latest
#   modal run test_palace.py --mode gpu --image-tag v0.16.0-gpu-sm80
#   modal run test_palace.py --mode cpu --image-tag v0.16.0
#   modal run test_palace.py --version v0.16.0                      # override Palace version
#   modal run test_palace.py -- --verbose                            # show full output

import modal
import subprocess
import sys

app = modal.App("palace-test")

IMAGE_REGISTRY = "ghcr.io/benvial/palace"
PALACE_REPO    = "https://github.com/awslabs/palace.git"

EXAMPLES = [
    ("Capacitance (spheres)",  "spheres",  "spheres.json"),
    ("Inductance (rings)",     "rings",    "rings.json"),
    ("Eigenmodes (cylinder)",  "cylinder", "cavity_pec.json"),
    ("Coaxial (matched load)", "coaxial",  "coaxial_matched.json"),
]


# ── Image builder ─────────────────────────────────────────────────────────────

def _palace_image(tag: str) -> modal.Image:
    return (
        modal.Image.from_registry(f"{IMAGE_REGISTRY}:{tag}")
        .apt_install("python3", "python3-pip", "git")
        .run_commands("ln -sf /usr/bin/python3 /usr/bin/python")
        .run_commands("python -m pip install --break-system-packages json5")
    )

# Module-level images — one per mode. The tag used here is just the default;
# the entrypoint passes the actual image at spawn time via the `image` kwarg
# on .map() / .starmap(). We use two separate functions (cpu/gpu) at module
# level so Modal can register them with their respective GPU resources.
_cpu_image = _palace_image("latest")
_gpu_image = _palace_image("latest-gpu-sm80")


# ── Helpers (run inside Modal containers) ────────────────────────────────────

def shell(cmd: str) -> tuple[int, str]:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()

def _patch_solver_backend(config_path: str, backend: str) -> None:
    import json5
    import json

    with open(config_path) as f:
        cfg = json5.load(f)

    cfg.setdefault("Solver", {})["Backend"] = backend

    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=2)

def _clone_and_run(version: str, example_subdir: str, config_file: str, backend: str) -> dict:
    clone_dir = f"/tmp/palace-{example_subdir}"
    rc, out = shell(
        f"git clone --depth=1 --branch {version} --filter=blob:none "
        f"--sparse {PALACE_REPO} {clone_dir} 2>&1 && "
        f"cd {clone_dir} && "
        f"git sparse-checkout set examples/{example_subdir} 2>&1"
    )
    if rc != 0:
        return {"passed": False, "output": f"Clone failed:\n{out}"}

    config_path = f"{clone_dir}/examples/{example_subdir}/{config_file}"
    _patch_solver_backend(config_path, backend)

    rc, out = shell(
        f"cd {clone_dir}/examples/{example_subdir} && "
        f"palace -np 1 -nt 1 {config_file} 2>&1"
    )
    return {"passed": rc == 0, "output": "\n".join(out.splitlines()[-30:])}


def _do_check_infra(mode: str) -> list[dict]:
    results = []
    if mode == "gpu":
        rc, out = shell(
            "nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader"
        )
        results.append({"name": "nvidia-smi", "passed": rc == 0, "output": out})

    rc, out = shell("palace --version")
    results.append({"name": "palace --version", "passed": rc == 0, "output": out})

    rc, out = shell("palace -np 2 --version")
    results.append({"name": "MPI (2 procs)", "passed": rc == 0, "output": out})

    return results


# ── Modal functions (module-level, one pair per device type) ──────────────────

@app.function(image=_cpu_image, timeout=120)
def check_infra_cpu(mode: str):
    return _do_check_infra(mode)

@app.function(image=_gpu_image, gpu="A100", timeout=120)
def check_infra_gpu(mode: str):
    return _do_check_infra(mode)

@app.function(image=_cpu_image, timeout=600)
def run_example_cpu(name: str, subdir: str, config: str, version: str, backend: str):
    return {"name": name, **_clone_and_run(version, subdir, config, backend)}

@app.function(image=_gpu_image, gpu="A100", timeout=600)
def run_example_gpu(name: str, subdir: str, config: str, version: str, backend: str):
    return {"name": name, **_clone_and_run(version, subdir, config, backend)}


# ── Entrypoint ────────────────────────────────────────────────────────────────

@app.local_entrypoint()
def main(
    mode: str      = "gpu",
    image_tag: str = "",
    version: str   = "v0.16.0",
):
    if mode not in ("cpu", "gpu"):
        print(f"ERROR: --mode must be 'cpu' or 'gpu', got '{mode}'")
        sys.exit(1)

    if not image_tag:
        image_tag = "latest-gpu-sm80" if mode == "gpu" else "latest"

    backend      = "GPU" if mode == "gpu" else "CPU"
    check_infra  = check_infra_gpu  if mode == "gpu" else check_infra_cpu
    run_example  = run_example_gpu  if mode == "gpu" else run_example_cpu

    print(f"\nMode          : {mode.upper()}")
    print(f"Image         : {IMAGE_REGISTRY}:{image_tag}")
    print(f"Palace version: {version}")
    print(f"Solver backend: {backend}")
    print("=" * 60)

    # Spawn everything in parallel
    infra_future = check_infra.spawn(mode)
    sim_futures  = [
        run_example.spawn(name, subdir, config, version, backend)
        for name, subdir, config in EXAMPLES
    ]

    # Collect
    infra_results = infra_future.get()
    sim_results   = [f.get() for f in sim_futures]
    all_results   = infra_results + sim_results

    # Summary
    verbose = "--verbose" in sys.argv
    print("\nResults:")
    print("-" * 60)
    passed = 0
    for r in all_results:
        icon = "✅" if r["passed"] else "❌"
        print(f"  {icon}  {r['name']}")
        if not r["passed"] or verbose:
            for line in r["output"].splitlines():
                print(f"       {line}")
        passed += int(r["passed"])

    total = len(all_results)
    print("-" * 60)
    print(f"  {passed}/{total} passed\n")
    sys.exit(0 if passed == total else 1)