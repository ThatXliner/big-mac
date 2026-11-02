#!/usr/bin/env python3
"""Create private auth + register unblock with existing vanityctl (no global apply)."""
import json
import os
from pathlib import Path
import secrets
import subprocess

root = Path(__file__).resolve().parents[1]
env = root / "services/unblock/.env"
os.umask(0o077)
if not env.exists():
    with env.open("x") as f:
        f.write("UNBLOCK_PORT=8093\nUNBLOCK_USERPASS=unblock:" + secrets.token_urlsafe(32) + "\n")
    print("Generated login in", env, "(not printed; keep private)")
env.chmod(0o600)
subprocess.run(["docker", "compose", "--project-directory", str(env.parent), "config", "--quiet"], check=True)
directory = Path.home() / ".vanityctl/services"
directory.mkdir(parents=True, exist_ok=True)
fragment = directory / "big-mac-unblock.yaml"
desired = {"services": {"unblock": {"type": "compose", "directory": str(env.parent),
            "files": ["compose.yaml"], "description": "Authenticated Ladder proxy"}}}
if fragment.exists() and json.loads(fragment.read_text()) != desired:
    raise SystemExit("Existing unblock fragment differs; inspect it before replacing")
fragment.write_text(json.dumps(desired, indent=2) + "\n")  # JSON is valid YAML.
subprocess.run(["vanityctl", "config", "validate"], check=True)
# Reconcile just this registered stack, including private environment changes.
subprocess.run(["vanityctl", "up", "unblock"], check=True)
subprocess.run(["vanityctl", "status", "unblock"], check=True)
