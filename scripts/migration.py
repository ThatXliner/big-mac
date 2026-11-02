#!/usr/bin/env python3
"""Plan a migration; export private config, source, images or quiesced data through age."""
import argparse
import datetime
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def expand(path):
    return str(Path(path).expanduser())


def make_plan():
    from inventory import collect
    d = collect()
    home = Path.home()
    configs = {str(p) for p in (home / "Library/LaunchAgents").glob("*.plist")}
    configs.update(str(p) for p in (home / ".cloudflared").glob("*") if p.suffix in {".yml", ".yaml", ".json", ".pem"})
    for relative in [".vanityctl/config.yaml", ".vanityctl/services", ".vanityctl/api-token",
                     ".vanityctl/adopted", ".config/vanityctl", ".big-mac-bootstrap", "scripts", "bin"]:
        if (home / relative).exists():
            configs.add(str(home / relative))
    sources = {expand(s["directory"]) for s in d["sources"]}
    for project in d["compose_projects"].values():
        configs.update(expand(f) for f in project["files"])
        directory = Path(project["directory"]).expanduser()
        configs.update(str(p) for p in directory.glob(".env*"))
        # Includes untracked app configs and build contexts; restore this before Compose.
        sources.add(str(directory))
    # The registry can name extra overlays not present in every container label.
    # Resolve it privately; descriptions/environment values are never exported.
    registry = json.loads(subprocess.check_output(["vanityctl", "list", "--json"], text=True))
    for service in registry:
        spec = json.loads(subprocess.check_output(["vanityctl", "describe", service["name"], "--json"], text=True))
        directory = Path(spec.get("directory") or str(home)).expanduser()
        if spec.get("type") == "compose":
            files = spec.get("files") or ([spec["file"]] if spec.get("file") else [])
            for filename in files:
                path = Path(filename).expanduser()
                configs.add(str(path if path.is_absolute() else directory / path))
            sources.add(str(directory))
        if spec.get("env_file"):
            path = Path(spec["env_file"]).expanduser()
            configs.add(str(path if path.is_absolute() else directory / path))
    bind_dirs, volumes = set(), set()
    for c in d["containers"]:
        for m in c["mounts"]:
            if m["type"] == "volume":
                volumes.add(m["volume"])
            elif m["type"] == "bind":
                path = Path(m["source"]).expanduser()
                if str(path) in {"/var/run/docker.sock", "/run/docker.sock"}:
                    continue
                if path.is_file():
                    configs.add(str(path))
                elif path.is_dir():
                    bind_dirs.add(str(path))
    for agent in d["launch_agents"]:
        configs.add(expand(agent["plist"]))
        configs.update(expand(s) for s in agent["script_paths"])
        executable = agent["executable"]
        if executable.startswith("~/") and Path(executable).expanduser().is_file():
            configs.add(expand(executable))
        directory = agent["directory"]
        if directory.startswith("~/") and Path(directory).expanduser().is_dir():
            sources.add(expand(directory))
        # Config/argument files remain private, including paths omitted by metadata export.
        with Path(agent["plist"]).expanduser().open("rb") as stream:
            raw = plistlib.load(stream)
        for argument in raw.get("ProgramArguments", []):
            if not isinstance(argument, str):
                continue
            candidate = Path(argument.partition("=")[2] if argument.startswith("--") and "=" in argument else argument).expanduser()
            if candidate.is_absolute() and candidate.is_file():
                # System binaries come from package managers; preserve local files and configs.
                if str(candidate).startswith(str(home) + "/") or candidate.suffix in {".json", ".yml", ".yaml", ".toml", ".conf", ".env"}:
                    configs.add(str(candidate))
    # Native data/services that aren't represented by Docker bind mounts.
    native = [str(home / p) for p in ["minecraft-server", ".ollama", "qwen-audio-server",
              "qwen-omni", "qwen2_audio_infer.py", "qwen_audio_server.py", "qwen_omni_infer.py",
              "ollama-auth-proxy.py", "ultravox_infer.py", "ultravox-env", ".config/sing-box",
              ".local/share/billion", ".config/billion", ".cache/huggingface"]
              if (home / p).exists()]
    configs.update(p for p in ["/opt/homebrew/etc/wireguard", "/opt/homebrew/etc/sing-box"] if Path(p).exists())
    return {"created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "config_paths": sorted(p for p in configs if Path(p).exists()),
            "source_paths": sorted(sources), "bind_data_paths": sorted(bind_dirs),
            "native_paths": native, "named_volumes": sorted(volumes),
            "images": sorted({c["image"] for c in d["containers"]}), "inventory": d,
            "notes": ["Review paths before export; this plan is private.",
                      "Data export requires relevant writers stopped and/or database logical dumps.",
                      "Image archives are architecture-specific; preserve custom rebuild sources too.",
                      "Native paths are a starting list: audit launch agents, model caches and external disks."]}


def encrypted_stream(command, destination, recipient):
    if not shutil.which("age"):
        raise SystemExit("Install age first (brew install age); no plaintext archive is created.")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Never overwrite an earlier backup.
    with destination.open("xb") as output:
        producer = subprocess.Popen(command, stdout=subprocess.PIPE)
        try:
            encrypt = subprocess.run(["age", "--recipient", recipient], stdin=producer.stdout, stdout=output)
            producer.stdout.close()
            code = producer.wait()
            if encrypt.returncode or code:
                raise RuntimeError(f"Export failed (producer={code}, age={encrypt.returncode})")
        except BaseException:
            producer.kill()
            producer.wait()
            destination.unlink(missing_ok=True)
            raise
    print("Encrypted export:", destination)


def tar_command(paths, exclude=()):
    if not paths:
        raise SystemExit("No paths in this export")
    if any(not Path(p).is_absolute() or not Path(p).exists() for p in paths):
        raise SystemExit("Every plan path must be an existing absolute path")
    # Relative archive members allow restoration to a staging directory first.
    return ["tar", "-czf", "-", *[f"--exclude={e}" for e in exclude], "-C", "/", "--", *[p.lstrip("/") for p in paths]]


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["plan", "config", "sources", "images", "databases", "data"])
    p.add_argument("--plan", type=Path, default=ROOT / "local/migration-plan.json")
    p.add_argument("--output", type=Path)
    p.add_argument("--recipient", help="age public recipient, never the private identity")
    p.add_argument("--writers-stopped", action="store_true")
    p.add_argument("--volume-helper", help="An already installed image containing tar (prefer an immutable digest)")
    a = p.parse_args()
    if a.action == "plan":
        a.plan.parent.mkdir(parents=True, exist_ok=True)
        a.plan.write_text(json.dumps(make_plan(), indent=2) + "\n")
        a.plan.chmod(0o600)
        print("Private plan:", a.plan, "— review paths before exporting")
        return
    if not a.recipient or not a.output:
        p.error("Exports require --recipient and --output")
    d = json.loads(a.plan.read_text())
    if a.action == "databases":
        ids = subprocess.check_output(["docker", "ps", "-q"], text=True).split()
        containers = json.loads(subprocess.check_output(["docker", "inspect", *ids], text=True)) if ids else []
        a.output.mkdir(parents=True, exist_ok=True)
        count = 0
        for container in containers:
            env = dict(e.split("=", 1) for e in container["Config"].get("Env", []) if "=" in e)
            if "PG_MAJOR" not in env:
                continue
            name = container["Name"].lstrip("/")
            # Local socket authentication stays inside the container. No password in argv.
            command = ["docker", "exec", name, "pg_dumpall", "--username", env.get("POSTGRES_USER", "postgres")]
            encrypted_stream(command, a.output / (name + ".sql.age"), a.recipient)
            count += 1
        if not count:
            raise SystemExit("No running PG_MAJOR containers found; inspect database inventory manually")
        print("Exported", count, "PostgreSQL clusters; coordinate app writes for a consistent cutover.")
        return
    if a.action == "config":
        command = tar_command(d["config_paths"] + [str(a.plan.resolve())])
    elif a.action == "sources":
        command = tar_command(d["source_paths"], ["node_modules", ".venv", "venv", ".next", "target", "__pycache__"])
    elif a.action == "images":
        command = ["docker", "save", *d["images"]]
    else:
        if not a.writers_stopped:
            p.error("Stop writers and capture logical database dumps before --writers-stopped")
        live = subprocess.check_output(["docker", "ps", "-q"], text=True).strip()
        if live:
            p.error("Data export requires all Docker containers stopped; this tool never stops them for you")
        if d["named_volumes"] and not a.volume_helper:
            p.error("Data export needs --volume-helper IMAGE with tar installed")
        # Separate streams keep large backups bounded in memory. Output is a private directory.
        a.output.mkdir(parents=True, exist_ok=True)
        paths = d["bind_data_paths"] + d["native_paths"]
        if paths:
            encrypted_stream(tar_command(paths), a.output / "bind-and-native.tar.gz.age", a.recipient)
        for volume in d["named_volumes"]:
            if not volume or "/" in volume or volume.startswith("-"):
                raise SystemExit("Invalid volume name in plan")
            command = ["docker", "run", "--rm", "--network", "none", "--read-only",
                       "--mount", f"type=volume,source={volume},target=/data,readonly",
                       "--entrypoint", "tar", a.volume_helper, "-czf", "-", "-C", "/data", "."]
            encrypted_stream(command, a.output / (volume + ".tar.gz.age"), a.recipient)
        return
    encrypted_stream(command, a.output, a.recipient)


if __name__ == "__main__":
    main()
