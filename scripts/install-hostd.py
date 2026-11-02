#!/usr/bin/env python3
"""Compatibility entrypoint; daemon/skill setup belongs to vanityctl."""
import argparse
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--start", action="store_true")
args = parser.parse_args()
command = ["vanityctl", "install", "--codex-skill"]
if args.start:
    command.append("--start")
subprocess.run(command, check=True)
