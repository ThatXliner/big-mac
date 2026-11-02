# big-mac

The operations repo for my Mac Studio: an observed service inventory, targeted
maintenance commands, reproducible setup for new services, and a migration path
that keeps credentials and data private. The control plane is
[vanityctl](https://github.com/ThatXliner/vanityctl), pinned as a Git submodule.

The initial inventory covers **104 containers, 19 Compose projects and 26 launchd
definitions** (including stopped containers, system daemons and legacy plists).
See the [service catalog](docs/services.md) and full [metadata snapshot](inventory/observed.json).

## Use on the existing host

```sh
ssh big-mac
cd ~/Developer/big-mac
vanityctl agent-context
python3 scripts/manage.py list
python3 scripts/manage.py status
vanityctl status unblock --json
```

Commands use the registry first and target individual services. Existing app
Compose files, native startup definitions and private config remain in their
original locations. The inventory records those locations and image revisions;
it does not automatically reconcile or restart the machine.

Read [operations](docs/operations.md) for updates, tunnel ownership exceptions,
new-service registration and rollback. Read [migration](docs/migration.md) before
moving the host; it covers encrypted config/source/image exports, PostgreSQL dumps,
volume backups and staged restoration.

## Reuse on your own Mac

```sh
git clone --recurse-submodules https://github.com/ThatXliner/big-mac.git
cd big-mac
bash scripts/bootstrap-macos.sh --install
# Start OrbStack / your Docker engine before continuing.
python3 scripts/install-hostd.py --start
python3 scripts/setup-unblock.py
python3 scripts/check-unblock.py
```

Use `~/Developer/big-mac` for the checkout if you want the same default location;
the setup scripts resolve their own checkout path. Homebrew must already be
installed. The bootstrap installs tooling and vanityctl; it does not clone or
configure my private applications. On an existing machine use `--check` first;
the hostd installer refuses to overwrite an existing agent/configuration.

Ladder listens on `127.0.0.1:8093`. Setup generates a private unique login in
`services/unblock/.env` (mode 0600). Read it privately to log in. Override the
port, image and ruleset in that file; [.env.example](services/unblock/.env.example)
documents the variables. Publish through your own Cloudflare tunnel using the
[example config](examples/cloudflared.yml) and route script described in operations.
The existing installation is at **https://unblock.bryanhu.com**.
It currently allows anonymous access. To use that mode on your own installation,
set `UNBLOCK_USERPASS=` in the private `.env` and run `python3 scripts/manage.py up unblock`.

To manage your own apps, copy/adapt [examples/vanityctl.yaml](examples/vanityctl.yaml)
on a fresh host, or add service fragments to an existing registry. Keep credentials
in external environment files. Run `make inventory` **on your own service host**
to replace my snapshot with your actual containers, sources and launchd definitions;
review the diff before publishing it. The scripts run locally on the host, so any
SSH alias works. My domains and service names are examples, not required settings.

## Make Codex use the tooling

```sh
python3 scripts/install-skill.py
```

This links the canonical [maintenance skill](skills/big-mac/SKILL.md) into the
current user's Codex skills directory. Run it on each machine where Codex operates.
The repo's [AGENTS.md](AGENTS.md) also directs agents to the skill and the targeted
commands. The skill is normally discovered in subsequent sessions; it can be
invoked explicitly as `$big-mac`.

## Public and private boundaries

Only allowlisted operational metadata and reusable scripts are published. Live
environment values, credentials, raw plists, resolved Compose configurations,
database contents, backup identities and migration plans stay private. The
inventory exposes service names, image versions, mount locations, variable names
and public tunnel hostnames so operators can understand the setup.

```sh
make check
git add .
make secrets                  # requires gitleaks; scans tracked working files + history
python3 scripts/check-host-secrets.py   # on the host: compares live values without logging them
git diff --cached --stat
```

Secret scanning also runs in CI. Never force-add ignored private files. The
snapshot is observed state, while `services/unblock/compose.yaml` is a complete
deployable recipe. Existing/private apps require their own source and private
configuration; source revisions and mount metadata alone cannot recreate them.

The optional [NixOS module](nix/README.md) provides Docker, tooling and unblock.
It is a starting point for a Linux migration, not a completed conversion of the
Mac's native ML services or a deployed NixOS host.
