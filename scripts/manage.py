#!/usr/bin/env python3
"""Targeted operations on this host. Uses vanityctl before falling back to inventory."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def compose(name, observed):
    project = observed["compose_projects"].get(name)
    if not project:
        raise SystemExit(f"Unknown Compose project: {name}")
    args = ["docker", "compose", "--project-name", name, "--project-directory", os.path.expanduser(project["directory"])]
    for filename in project["files"]:
        if not Path(filename).expanduser().is_file():
            raise SystemExit(f"Missing {filename}; restore private config/source first")
        args += ["-f", os.path.expanduser(filename)]
    return args


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["list", "status", "logs", "restart", "up", "images", "registry", "refresh"])
    p.add_argument("target", nargs="?", help="Compose/vanityctl name, launchd:LABEL, or container:NAME")
    a = p.parse_args()
    if a.action == "refresh":
        from inventory import collect
        destination = ROOT / "inventory/observed.json"
        destination.write_text(json.dumps(collect(), indent=2, sort_keys=True) + "\n")
        print("Refreshed allowlisted metadata; review diff before publishing.")
        return
    observed = json.loads((ROOT / "inventory/observed.json").read_text())
    if a.action == "list":
        print("Compose projects:", ", ".join(sorted(observed["compose_projects"])))
        print("Launch agents:")
        for agent in observed["launch_agents"]:
            print("  launchd:" + agent["label"])
        print("Standalone containers:")
        for c in observed["containers"]:
            if not c["compose_project"]:
                print("  container:" + c["name"])
        return
    if a.action == "images":
        for c in observed["containers"]:
            print(c["name"], c["image"], ",".join(c["repo_digests"]) or "LOCAL IMAGE: export for migration")
        return
    if a.action == "registry":
        run(["vanityctl", "config", "validate"])
        run(["vanityctl", "list"])
        return
    if a.action == "status" and not a.target:
        run(["vanityctl", "list"])
        run(["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"])
        return
    if not a.target:
        p.error("This operation requires one target")
    if a.target.startswith("launchd:"):
        label = a.target.split(":", 1)[1]
        if label not in {x["label"] for x in observed["launch_agents"]}:
            p.error("Label not in inventory; refresh first")
        agent = next(x for x in observed["launch_agents"] if x["label"] == label)
        domain = "system" if agent.get("scope") == "system" else f"gui/{os.getuid()}"
        service = f"{domain}/{label}"
        if a.action == "status":
            run(["launchctl", "print", service])
        elif a.action == "restart":
            run(["launchctl", "kickstart", "-k", service])
        else:
            p.error("Native agents support status/restart; see private plist for log paths")
        return
    if a.target.startswith("container:"):
        name = a.target.split(":", 1)[1]
        if name not in {x["name"] for x in observed["containers"] if not x["compose_project"]}:
            p.error("Not an inventoried standalone container")
        commands = {"status": ["docker", "ps", "-a", "--filter", "name=^/" + re.escape(name) + "$"],
                    "restart": ["docker", "restart", name], "logs": ["docker", "logs", "--tail", "100", name]}
        if a.action not in commands:
            p.error("Standalone containers support status/restart/logs; creation belongs to their source scripts")
        run(commands[a.action])
        return
    registry = json.loads(subprocess.check_output(["vanityctl", "list", "--json"], text=True))
    if a.target in {s["name"] for s in registry} and a.action != "up":
        run(["vanityctl", a.action, a.target])
    else:
        # Up is deliberately targeted; never apply all unrelated services.
        op = {"status": ["ps", "-a"], "logs": ["logs", "--tail", "100"],
              "restart": ["restart"], "up": ["up", "-d"]}[a.action]
        run(compose(a.target, observed) + op)


if __name__ == "__main__":
    main()
