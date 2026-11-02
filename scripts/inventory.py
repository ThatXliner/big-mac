#!/usr/bin/env python3
"""Read-only, allowlisted metadata export. Run ON the server; no dependencies."""
import datetime
import json
import pathlib
import plistlib
import re
import subprocess
import urllib.parse


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL)


def homepath(value):
    return str(value).replace(str(pathlib.Path.home()), "~")


def collect(include_system=True):
    ids = run("docker", "ps", "-aq").split()
    containers = json.loads(run("docker", "inspect", *ids)) if ids else []
    images = {}
    for image_id in {c["Image"] for c in containers}:
        info = json.loads(run("docker", "image", "inspect", image_id))[0]
        images[image_id] = info.get("RepoDigests", [])
    result = {"schema": 1, "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "containers": [], "launch_agents": [], "compose_projects": {}, "sources": [], "ingress_routes": []}
    for c in sorted(containers, key=lambda item: item["Name"]):
        labels = c["Config"].get("Labels") or {}
        project = labels.get("com.docker.compose.project")
        directory = labels.get("com.docker.compose.project.working_dir")
        files = labels.get("com.docker.compose.project.config_files", "")
        if project and directory:
            result["compose_projects"][project] = {"directory": homepath(directory),
                "files": [homepath(f) for f in files.split(",") if f]}
        result["containers"].append({
            "name": c["Name"].lstrip("/"), "image": c["Config"]["Image"],
            "image_id": c["Image"], "repo_digests": images[c["Image"]],
            "state": c["State"]["Status"], "restart": c["HostConfig"]["RestartPolicy"]["Name"],
            "compose_project": project, "compose_service": labels.get("com.docker.compose.service"),
            "ports": c["HostConfig"].get("PortBindings") or {},
            "mounts": [{"type": m["Type"], "source": homepath(m["Source"]),
                        "destination": m["Destination"], "volume": m.get("Name"), "writable": m["RW"]}
                       for m in c.get("Mounts", [])],
            # Deliberately exclude commands, env values, logs, arbitrary labels and health output.
            "environment_keys": sorted(e.split("=", 1)[0] for e in c["Config"].get("Env", [])),
        })
    paths = list((pathlib.Path.home() / "Library/LaunchAgents").glob("*.plist"))
    paths += list((pathlib.Path.home() / ".vanityctl/generated").rglob("*.plist"))
    if include_system:
        paths += list(pathlib.Path("/Library/LaunchDaemons").glob("*.plist"))
    for path in sorted(paths):
        try:
            with path.open("rb") as stream:
                p = plistlib.load(stream)
        except (OSError, plistlib.InvalidFileException):
            continue
        args = p.get("ProgramArguments", [])
        # Argument values and environment VALUES can contain credentials. Never export them.
        scripts = [homepath(a) for a in args if isinstance(a, str)
                   and a.startswith("/") and a.endswith((".py", ".sh", ".js", ".ts"))]
        result["launch_agents"].append({"label": p.get("Label"), "plist": homepath(path),
            "scope": "system" if str(path).startswith("/Library/LaunchDaemons/") else "user",
            "executable": homepath(p.get("Program") or (args[0] if args else "")),
            "script_paths": scripts, "argument_count": len(args),
            "directory": homepath(p.get("WorkingDirectory", "")),
            "run_at_load": p.get("RunAtLoad", False),
            "keep_alive": bool(p.get("KeepAlive", False)),
            "interval_seconds": p.get("StartInterval"), "calendar": p.get("StartCalendarInterval"),
            "environment_keys": sorted(p.get("EnvironmentVariables", {}))})
    for config in sorted((pathlib.Path.home() / ".cloudflared").glob("*.yml")):
        # Export only hostname + loopback destination, never tunnel credentials or URL tokens.
        try:
            text = config.read_text()
        except OSError:
            continue
        for match in re.finditer(r"(?m)^\s*- hostname: ([a-zA-Z0-9.*_-]+)\s*\n\s+service: ((?:https?|ssh)://(?:localhost|127\.0\.0\.1):\d+)\s*$", text):
            result["ingress_routes"].append({"config": homepath(config), "hostname": match[1], "service": match[2]})
    candidates = {path for path in (pathlib.Path.home() / "Developer").glob("*") if path.is_dir()}
    candidates.update(pathlib.Path(v["directory"].replace("~", str(pathlib.Path.home()), 1))
                      for v in result["compose_projects"].values())
    seen = set()
    for directory in sorted(candidates):
        try:
            top = run("git", "-C", str(directory), "rev-parse", "--show-toplevel").strip()
            if top in seen:
                continue
            seen.add(top)
            origin = run("git", "-C", top, "remote", "get-url", "origin").strip()
            # Publish only GitHub owner/repo, never URL credentials, query strings, custom hosts.
            match = re.fullmatch(r"(?:git@github\.com:|https://(?:[^/@]+@)?github\.com/)([\w.-]+/[\w.-]+?)(?:\.git)?", origin)
            result["sources"].append({"directory": homepath(top),
                "repository": "https://github.com/" + match[1] if match else "(private/local origin omitted)",
                "commit": run("git", "-C", top, "rev-parse", "HEAD").strip(),
                "dirty": bool(run("git", "-C", top, "status", "--porcelain").strip())})
        except subprocess.CalledProcessError:
            continue
    return result


if __name__ == "__main__":
    print(json.dumps(collect(), indent=2, sort_keys=True))
