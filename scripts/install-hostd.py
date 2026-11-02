#!/usr/bin/env python3
"""Install a user hostd agent on a fresh Mac without overwriting existing configuration."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import secrets
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--start", action="store_true")
a = p.parse_args()
os.umask(0o077)
home = Path.home()
root = home / ".vanityctl"
root.mkdir(exist_ok=True)
(root / "services").mkdir(exist_ok=True)
(root / "logs").mkdir(exist_ok=True)
config = root / "config.yaml"
if not config.exists():
    token = root / "api-token"
    if not token.exists():
        with token.open("x") as f:
            f.write(secrets.token_urlsafe(48) + "\n")
    config.write_text(json.dumps({"version": 1, "api": {"listen": "127.0.0.1:7788",
        "token_file": str(token), "public_read_only": False}, "services": {}}, indent=2) + "\n")
hostd = shutil.which("hostd")
if not hostd:
    raise SystemExit("Install vanityctl/hostd first with bootstrap-macos.sh --install")
target = home / "Library/LaunchAgents/dev.vanityctl.hostd.plist"
if target.exists():
    raise SystemExit("Existing hostd agent preserved; inspect it and use vanityctl doctor")
target.parent.mkdir(parents=True, exist_ok=True)
plist = {"Label": "dev.vanityctl.hostd", "ProgramArguments": [hostd, "--config", str(config)],
         "RunAtLoad": True, "KeepAlive": True,
         "EnvironmentVariables": {"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
         "StandardOutPath": str(root / "logs/hostd.log"), "StandardErrorPath": str(root / "logs/hostd.log")}
with target.open("xb") as f:
    plistlib.dump(plist, f)
subprocess.run(["plutil", "-lint", str(target)], check=True)
if a.start:
    subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(target)], check=True)
print("Created", target)
