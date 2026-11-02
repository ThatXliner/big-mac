#!/usr/bin/env python3
"""Register missing existing Compose projects, without starting/replacing workloads."""
import argparse
import json
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--execute", action="store_true", help="Write additive registry fragments; default is a plan")
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
observed = json.loads((root / "inventory/observed.json").read_text())
known = {s["name"] for s in json.loads(subprocess.check_output(["vanityctl", "list", "--json"], text=True))}
fragments = Path.home() / ".vanityctl/services"
for name, project in sorted(observed["compose_projects"].items()):
    if name in known:
        print("Already registered:", name)
        continue
    directory = os.path.expanduser(project["directory"])
    files = [os.path.expanduser(f) for f in project["files"]]
    if not files or not all(Path(f).is_file() for f in files):
        print("Missing config; skipped:", name)
        continue
    fragment = fragments / ("big-mac-" + name + ".yaml")
    if fragment.exists():
        raise SystemExit(f"Unloaded fragment already exists: {fragment}; inspect it")
    print("Register" if a.execute else "Would register", name)
    if a.execute:
        fragments.mkdir(parents=True, exist_ok=True)
        data = {"services": {name: {"type": "compose", "directory": directory, "files": files,
                                   "description": "Existing stack indexed by big-mac"}}}
        fragment.write_text(json.dumps(data, indent=2) + "\n")
        try:
            subprocess.run(["vanityctl", "config", "validate"], check=True)
        except Exception:
            fragment.unlink()
            raise
