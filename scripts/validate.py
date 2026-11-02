#!/usr/bin/env python3
"""Offline checks for scripts and the public snapshot."""
import ast
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
for source in [*root.joinpath("scripts").glob("*.py"), *root.joinpath("tests").glob("*.py")]:
    ast.parse(source.read_text(), filename=str(source))
d = json.loads((root / "inventory/observed.json").read_text())
assert d["schema"] == 1
for c in d["containers"]:
    assert not {"Env", "Cmd", "Labels", "command", "environment", "credentials"} & c.keys()
    assert c["image"] and c["image_id"].startswith("sha256:")
for name, project in d["compose_projects"].items():
    assert project["directory"] and project["files"], name
catalog = root / "docs/services.md"
before = catalog.read_text()
subprocess.run(["python3", str(root / "scripts/catalog.py")], check=True)
assert catalog.read_text() == before, "Catalog was stale; regenerated it. Review and rerun checks."
skill = root / "skills/big-mac/SKILL.md"
assert skill.read_text().startswith("---\nname: big-mac\ndescription:")
assert (root / "vendor/vanityctl/Cargo.lock").is_file(), "Initialize the vanityctl submodule"
print("PASS: Python syntax, snapshot shape, generated catalog, skill metadata and submodule")
