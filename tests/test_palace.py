# test_palace.py
#
# Run basic infrastructure checks, an MPI parallel regression test, and all
# Palace example simulations on Modal.
# Palace parallelism is controlled via its own CLI flags (-np for MPI, -nt for OpenMP).
#
# Usage:
#   modal run test_palace.py                                         # GPU, latest-gpu-sm80
#   modal run test_palace.py --mode cpu                              # CPU, latest
#   modal run test_palace.py --mode gpu --image-tag v0.16.0-gpu-sm80
#   modal run test_palace.py --mode cpu --image-tag v0.16.0
#   modal run test_palace.py --version v0.16.0                      # override Palace version
#   modal run test_palace.py --verbose true                          # show full output

import modal
import subprocess
import sys
import argparse


parser = argparse.ArgumentParser(
    prog="modal run test_palace.py --",
    description="Run Palace tests and examples on Modal.",
)
parser.add_argument(
    "--image-tag", default="", help="Image tag to use (default: latest)"
)
parser.add_argument("--mode", default="gpu", help="Mode to run in (cpu or gpu)")
parser.add_argument("--verbose", default=False, help="Show full output")
parser.add_argument(
    "--version", default="", help="Override Palace version for git examples"
)


parsed = parser.parse_args(sys.argv[3:])

image_tag = parsed.image_tag
mode = parsed.mode

app = modal.App("palace-test")

IMAGE_REGISTRY = "ghcr.io/benvial/palace"
PALACE_REPO = "https://github.com/awslabs/palace.git"

# Example used for the MPI regression test — the cheapest one to run.
MPI_EXAMPLE = ("spheres", "spheres.json")
MPI_NPROCS = 2

EXAMPLES = [
    ("Capacitance (spheres)", "spheres", "spheres.json"),
    ("Inductance (rings)", "rings", "rings.json"),
    ("Eigenmodes (cylinder)", "cylinder", "cavity_pec.json"),
    ("Coaxial (matched load)", "coaxial", "coaxial_matched.json"),
    ("Coplanar waveguide (waveport adaptive)", "cpw", "cpw_wave_adaptive.json"),
]


# ── Image builder ─────────────────────────────────────────────────────────────


def _palace_image(tag: str) -> modal.Image:
    force = True  # any(tag == t or tag.startswith(t) for t in ("latest", "dev"))
    return (
        # force_build for mutable tags (dev, latest) so Modal always re-pulls;
        # immutable version tags (v0.x.y) are safe to cache.
        modal.Image.from_registry(
            f"{IMAGE_REGISTRY}:{tag}", force_build=force, add_python="3.12"
        )
        .apt_install("git")
        .run_commands("pip install json5")
    )


_image = _palace_image(image_tag)


# ── Helpers (run inside Modal containers) ────────────────────────────────────


def shell(cmd: str) -> tuple[int, str]:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def _patch_solver_backend(config_path: str, backend: str) -> None:
    import json5
    import json

    with open(config_path, "r") as f:
        cfg = json5.load(f)

    cfg.setdefault("Solver", {})["Device"] = backend
    # cfg["Solver"]["Linear"]["Type"] = "AMS"

    with open(config_path, "w") as f:
        f.write(json.dumps(cfg, indent=2))


def _clone_and_run(
    version: str,
    example_subdir: str,
    config_file: str,
    backend: str,
    nprocs: int = 1,
    clone_suffix: str = "",
) -> dict:
    clone_dir = f"/tmp/palace-{example_subdir}{clone_suffix}"
    rc, out = shell(
        f"git clone --depth=1 --branch {version} --filter=blob:none "
        f"--sparse {PALACE_REPO} {clone_dir} 2>&1 && "
        f"cd {clone_dir} && "
        f"git sparse-checkout set examples/{example_subdir} 2>&1"
    )
    if rc != 0:
        return {"passed": False, "output": f"Clone failed:\n{out}", "raw": out}

    config_path = f"{clone_dir}/examples/{example_subdir}/{config_file}"
    _patch_solver_backend(config_path, backend)

    rc, out = shell(
        f"cd {clone_dir}/examples/{example_subdir} && "
        f"palace -np {nprocs} -nt 1 {config_file} 2>&1"
    )
    if parsed.verbose:
        print(out)
    return {
        "passed": rc == 0,
        "output": "\n".join(out.splitlines()[-30:]),
        "raw": out,
        "run_dir": f"{clone_dir}/examples/{example_subdir}",
    }


def _mpi_sizes_from_output(run_dir: str) -> list:
    """Read Problem.MPISize out of every palace.json the run wrote."""
    import glob
    import json

    sizes = []
    for path in sorted(glob.glob(f"{run_dir}/**/palace.json", recursive=True)):
        with open(path, "r") as f:
            sizes.append(json.load(f).get("Problem", {}).get("MPISize"))
    return sizes


def _do_check_mpi_parallel(version: str, backend: str) -> dict:
    """Regression test for the MPI launcher: a real multi-rank Palace run.

    When the image's MPI client and launcher speak different wire protocols,
    MPI_Init silently takes the singleton path: `palace -np N` starts N
    independent one-rank runs that overwrite each other's output. Neither a
    single-rank example nor `palace -np N --version` sees that, so assert the
    rank count Palace itself reports, in stdout and in palace.json.
    """
    subdir, config_file = MPI_EXAMPLE
    name = f"MPI parallel run ({MPI_NPROCS} ranks)"
    result = _clone_and_run(
        version, subdir, config_file, backend, nprocs=MPI_NPROCS, clone_suffix="-mpi"
    )
    if not result["passed"]:
        return {"name": name, "passed": False, "output": result["output"]}

    problems = []
    banner = f"Running with {MPI_NPROCS} MPI processes"
    if banner not in result["raw"]:
        problems.append(
            f"stdout never reported {banner!r} — ranks ran as MPI singletons"
        )

    sizes = _mpi_sizes_from_output(result["run_dir"])
    if not sizes:
        problems.append("no palace.json was written")
    elif any(size != MPI_NPROCS for size in sizes):
        problems.append(f"palace.json Problem.MPISize = {sizes}, expected {MPI_NPROCS}")

    if problems:
        return {
            "name": name,
            "passed": False,
            "output": "\n".join(problems + result["output"].splitlines()[-20:]),
        }
    return {"name": name, "passed": True, "output": banner}


def _do_check_infra(mode: str) -> list[dict]:
    results = []
    if mode == "gpu":
        rc, out = shell(
            "nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader"
        )
        if parsed.verbose:
            print(out)
        results.append({"name": "nvidia-smi", "passed": rc == 0, "output": out})

    rc, out = shell("palace --version")
    if parsed.verbose:
        print(out)
    results.append({"name": "palace --version", "passed": rc == 0, "output": out})

    # Smoke test only: this passes even when the ranks are MPI singletons.
    # `_do_check_mpi_parallel` is what proves the ranks share a communicator.
    rc, out = shell("palace -np 2 --version")
    if parsed.verbose:
        print(out)
    results.append({"name": "MPI (2 procs)", "passed": rc == 0, "output": out})

    return results


# ── Modal functions (module-level, one pair per device type) ──────────────────

timeout = 1200


@app.function(image=_image, timeout=timeout)
def check_infra_cpu(mode: str):
    return _do_check_infra(mode)


@app.function(image=_image, gpu="A100", timeout=timeout)
def check_infra_gpu(mode: str):
    return _do_check_infra(mode)


@app.function(image=_image, timeout=timeout)
def run_example_cpu(name: str, subdir: str, config: str, version: str, backend: str):
    return {"name": name, **_clone_and_run(version, subdir, config, backend)}


@app.function(image=_image, gpu="A100", timeout=timeout)
def run_example_gpu(name: str, subdir: str, config: str, version: str, backend: str):
    return {"name": name, **_clone_and_run(version, subdir, config, backend)}


@app.function(image=_image, timeout=timeout)
def check_mpi_parallel_cpu(version: str, backend: str):
    return _do_check_mpi_parallel(version, backend)


@app.function(image=_image, gpu="A100", timeout=timeout)
def check_mpi_parallel_gpu(version: str, backend: str):
    return _do_check_mpi_parallel(version, backend)


# ── Entrypoint ────────────────────────────────────────────────────────────────


@app.local_entrypoint()
def main(
    mode: str = "gpu",
    image_tag: str = "",
    version: str = "v0.16.0",
    verbose: str = "false",  # pass "true" to show full output
):
    if mode not in ("cpu", "gpu"):
        print(f"ERROR: --mode must be 'cpu' or 'gpu', got '{mode}'")
        sys.exit(1)

    if not image_tag:
        image_tag = "latest-gpu-sm80" if mode == "gpu" else "latest"

    backend = "GPU" if mode == "gpu" else "CPU"
    check_infra = check_infra_gpu if mode == "gpu" else check_infra_cpu
    check_mpi_parallel = (
        check_mpi_parallel_gpu if mode == "gpu" else check_mpi_parallel_cpu
    )
    run_example = run_example_gpu if mode == "gpu" else run_example_cpu

    print(f"\nMode          : {mode.upper()}")
    print(f"Image         : {IMAGE_REGISTRY}:{image_tag}")
    print(f"Palace version: {version}")
    print(f"Solver backend: {backend}")
    print("=" * 60)

    # Spawn everything in parallel
    infra_future = check_infra.spawn(mode)
    mpi_future = check_mpi_parallel.spawn(version, backend)
    sim_futures = [
        run_example.spawn(name, subdir, config, version, backend)
        for name, subdir, config in EXAMPLES
    ]

    # Collect
    infra_results = infra_future.get()
    mpi_result = mpi_future.get()
    sim_results = [f.get() for f in sim_futures]
    all_results = infra_results + [mpi_result] + sim_results

    # Summary
    print("\nResults:")
    print("-" * 60)
    passed = 0
    for r in all_results:
        icon = "✅" if r["passed"] else "❌"
        print(f"  {icon}  {r['name']}")
        if not r["passed"] or verbose == "true":
            for line in r["output"].splitlines():
                print(f"       {line}")
        passed += int(r["passed"])

    total = len(all_results)
    print("-" * 60)
    print(f"  {passed}/{total} passed\n")
    sys.exit(0 if passed == total else 1)
