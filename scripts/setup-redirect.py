#!/usr/bin/env python3
"""Register one loopback redirect with vanityctl and start only that service."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("name")
p.add_argument("target", help="Destination HTTP(S) origin")
p.add_argument("--port", type=int, default=8094)
a = p.parse_args()
if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", a.name):
    p.error("Use a lowercase service name with letters, numbers and hyphens")
root = Path(__file__).resolve().parents[1]
server = root / "services/redirect/server.py"
python = shutil.which("python3")
if not python:
    raise SystemExit("python3 is required")
subprocess.run([python, str(server), a.target, "--port", str(a.port), "--check"], check=True)
fragment = Path.home() / ".vanityctl/services" / f"big-mac-{a.name}.yaml"
desired = {"services": {a.name: {"type": "process", "directory": str(server.parent),
    "command": python, "args": [str(server), a.target, "--port", str(a.port)],
    "restart": "always", "description": "Loopback HTTP redirect; preserve paths and queries"}}}
fragment.parent.mkdir(parents=True, exist_ok=True)
if fragment.exists() and json.loads(fragment.read_text()) != desired:
    raise SystemExit("Existing redirect fragment differs; inspect it before replacing")
os.umask(0o077)
fragment.write_text(json.dumps(desired, indent=2) + "\n")
fragment.chmod(0o600)
subprocess.run(["vanityctl", "config", "validate"], check=True)
subprocess.run(["vanityctl", "up", a.name], check=True)
subprocess.run(["vanityctl", "status", a.name, "--json"], check=True)
