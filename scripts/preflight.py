"""Cross-platform deployment checks; no changes to services or data."""

import argparse
import shutil
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--demo", action="store_true")
parser.add_argument("--require-load-tools", action="store_true")
args = parser.parse_args()
required = [
    "backend/Dockerfile",
    "backend/app/main.py",
    "backend/app/allocation/worker.py",
    "backend/app/lab/worker.py",
    "frontend/Dockerfile",
    "contracts/openapi.json",
    ".env",
]
missing = [name for name in required if not Path(name).is_file()]
missing += [
    f"command:{name}"
    for name in (["docker"] + (["k6"] if args.require_load_tools else []))
    if not shutil.which(name)
]
if missing:
    parser.exit(1, "Preflight unavailable: " + ", ".join(missing) + "\n")
command = ["docker", "compose", "--env-file", ".env", "-f", "compose.yaml"]
if args.demo:
    command += ["-f", "infra/compose.demo.yaml", "--profile", "lab"]
subprocess.run([*command, "config", "--quiet"], check=True)
subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, check=True)
print("Compose configuration and Docker daemon are available.")
