#!/usr/bin/env python3
"""Compare tracked content against live credential values without printing those values.

Run on the host, in addition to gitleaks. Reads local secrets but exports none.
"""
import json
from pathlib import Path
import plistlib
import re
import subprocess

root = Path(__file__).resolve().parents[1]
names = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
public = b"\n".join((root / n).read_bytes() for n in names if n and (root / n).is_file() and not (root / n).is_symlink())
if not public:
    raise SystemExit("No tracked public content to check")
pattern = re.compile(r"password|secret|token|api.?key|anon.?key|service.*key|credential|database.?url|dsn|authorization|userpass", re.I)
values = []


def record(label, key, value):
    if pattern.search(key) and isinstance(value, str) and len(value) >= 8:
        values.append((label + ":" + key, value))


ids = subprocess.check_output(["docker", "ps", "-aq"], text=True).split()
for container in json.loads(subprocess.check_output(["docker", "inspect", *ids], text=True)) if ids else []:
    for entry in container["Config"].get("Env", []):
        key, _, value = entry.partition("=")
        record(container["Name"], key, value)
        if key in {"USERPASS", "UNBLOCK_USERPASS"}:
            record(container["Name"], "password", value.partition(":")[2])
home = Path.home()
for path in (home / "Library/LaunchAgents").glob("*.plist"):
    with path.open("rb") as f:
        plist = plistlib.load(f)
    for key, value in plist.get("EnvironmentVariables", {}).items():
        record(path.name, key, value)
for relative in [".vanityctl/api-token", ".config/vanityctl/cloudflare-token"]:
    path = home / relative
    if path.exists():
        record(relative, "token", path.read_text().strip())
for path in (home / ".cloudflared").glob("*.json"):
    try:
        data = json.loads(path.read_text())
    except (ValueError, OSError):
        continue
    if isinstance(data, dict):
        for key, value in data.items():
            record(path.name, key, value)
matches = [label for label, value in values if value.encode() in public]
if matches:
    raise SystemExit("STOP: live credential value found in tracked content. Sources: " + ", ".join(matches))
print(f"PASS: compared {len(values)} live sensitive values with tracked content; no matches (values not logged).")
