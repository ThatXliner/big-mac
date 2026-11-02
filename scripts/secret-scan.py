#!/usr/bin/env python3
"""Scan tracked working files and full main-repo history, without exporting ignored files."""
import os
from pathlib import Path
import shutil
import secrets
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
scanner = shutil.which("gitleaks")
if not scanner:
    raise SystemExit("Install gitleaks first (brew install gitleaks)")
files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
with tempfile.TemporaryDirectory(prefix="big-mac-public-scan-") as temporary:
    destination = Path(temporary)
    count = 0
    for name in files:
        source = root / name
        if not name or source.is_dir() or not source.exists():
            continue  # gitlinks are separate repositories
        if source.is_symlink():
            raise SystemExit(f"Review tracked symlink before publication: {name}")
        output = destination / name
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, output)
        count += 1
    if not count:
        raise SystemExit("No tracked files; git add the public files first")
    subprocess.run([scanner, "dir", str(destination), "--config", str(root / ".gitleaks.toml"), "--redact", "--no-banner", "--ignore-gitleaks-allow"], check=True)
    # Ensure the image-tag exception never bypasses the rest of the snapshot.
    snapshot = destination / "inventory/observed.json"
    with snapshot.open("a") as f:
        f.write('\napi_key = "' + "ghp_" + secrets.token_hex(18) + '"\n')
    probe = subprocess.run([scanner, "dir", str(destination), "--config", str(root / ".gitleaks.toml"),
                            "--redact", "--no-banner"], capture_output=True)
    if probe.returncode != 1:
        raise SystemExit("Scanner failed its synthetic credential detection check; do not publish")
if subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
    subprocess.run([scanner, "git", str(root), "--config", str(root / ".gitleaks.toml"), "--redact", "--no-banner", "--ignore-gitleaks-allow", "--log-opts=--all"], check=True)
print(f"Scanned {count} tracked working files and available main-repo history; synthetic detection check passed.")
