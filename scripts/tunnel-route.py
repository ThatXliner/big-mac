#!/usr/bin/env python3
"""Add an HTTP ingress to an existing local Cloudflare tunnel; preserve other routes."""
import argparse
import datetime
from pathlib import Path
import re
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("hostname")
p.add_argument("port", type=int)
p.add_argument("--config", type=Path, default=Path.home() / ".cloudflared/config.yml")
p.add_argument("--restart-label", help="Existing user LaunchAgent label for this tunnel")
a = p.parse_args()
if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", a.hostname) or not 1 <= a.port <= 65535:
    p.error("Invalid hostname or port")
text = a.config.read_text()
tunnel = re.search(r"(?m)^tunnel:\s*([a-zA-Z0-9-]+)\s*$", text)
if not tunnel:
    raise SystemExit("Expected a local tunnel ID in config")
route = f"  - hostname: {a.hostname}\n    service: http://localhost:{a.port}\n"
if re.search(r"hostname:\s*" + re.escape(a.hostname) + r"\s*$", text, re.M):
    if route not in text:
        raise SystemExit("Hostname already exists with different routing; inspect manually")
else:
    terminal = "  - service: http_status:404"
    if text.count(terminal) != 1:
        raise SystemExit("Expected exactly one terminal 404 ingress; inspect manually")
    backup = a.config.with_name(a.config.name + ".before-" + datetime.datetime.now().strftime("%Y%m%dT%H%M%S"))
    shutil.copy2(a.config, backup)
    a.config.write_text(text.replace(terminal, route + terminal))
    try:
        subprocess.run(["cloudflared", "tunnel", "--config", str(a.config), "ingress", "validate"], check=True)
        # No --overwrite-dns: refuse to clobber an unrelated existing record.
        subprocess.run(["cloudflared", "tunnel", "route", "dns", tunnel[1], a.hostname], check=True)
    except Exception:
        shutil.copy2(backup, a.config)
        raise
    print("Saved original config at", backup)
if a.restart_label:
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", a.restart_label):
        p.error("Invalid label")
    import os
    subprocess.run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{a.restart_label}"], check=True)
else:
    print("Restart the existing tunnel supervisor to load this route.")
