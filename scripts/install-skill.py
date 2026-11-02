#!/usr/bin/env python3
"""Make this checkout's maintenance skill discoverable to Codex."""
import os
from pathlib import Path

source = Path(__file__).resolve().parents[1] / "skills/big-mac"
codex_root = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
target = codex_root / "skills/big-mac"
target.parent.mkdir(parents=True, exist_ok=True)
if target.is_symlink() and target.resolve() == source:
    print("Skill already linked:", target)
elif target.exists() or target.is_symlink():
    raise SystemExit(f"Existing skill preserved at {target}; inspect before replacing")
else:
    target.symlink_to(source, target_is_directory=True)
    print("Linked skill:", target)
