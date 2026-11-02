---
name: big-mac
description: Operate or migrate the SSH big-mac host using its infrastructure repo and vanityctl. Use for its Docker services, launchd jobs, Cloudflare tunnels, maintenance and setup.
---

The public source of operational knowledge is `ThatXliner/big-mac`, normally at
`~/Developer/big-mac` on SSH host `big-mac`. Other installations can use their own
checkout and SSH alias. Run host commands over SSH, not on the client Mac.

1. Read `docs/operations.md` in the checkout for ownership exceptions. Get the
   focused context with `vanityctl agent-context NAME --json` and inspect the requested
   target with `vanityctl status NAME --json`. If its name is unknown, use
   `vanityctl list --json` and `vanityctl discover QUERY --json` before consulting
   `docs/services.md` or searching the host. Discovery never adopts resources.
2. Use `vanityctl` for registered workloads. `start` runs Compose **start**, so
   initial creation or a Compose config change needs targeted
   `vanityctl up PROJECT`. The Python wrapper now delegates to the same command.
   Do not use global `vanityctl apply`
   as a discovery step. Existing custom image tags may be local security rebuilds;
   preserve them until their build provenance is understood.
3. For unmanaged native services, target the inventoried label with
   `python3 scripts/manage.py status launchd:LABEL` (or `restart`). Installed
   plists can be stale; check the live launchctl domain before restarting. The
   live main Cloudflare tunnel is `com.bryanhu.cloudflared`, while older
   vanityctl Cloudflare entries were stopped at the initial snapshot. Do not
   start those old entries and create duplicate tunnels.
4. After an authorized change, verify the target locally and via its public
   route. For unblock, use `scripts/check-unblock.py`, then the same command with
   `--url https://unblock.bryanhu.com`. Credentials stay in the host's ignored
   `services/unblock/.env`; health checks do not print them.
5. Refresh public metadata with `python3 scripts/manage.py refresh`, then
   `python3 scripts/catalog.py`. Review the diff and run the checks before pushing.

For a move or backup, read `docs/migration.md` and use `scripts/migration.py`.
For a fresh Mac, follow the README bootstrap. For Linux, read `nix/README.md`;
the NixOS module covers host tooling and unblock, not every native Mac workload.
Keep the canonical host skill here; `scripts/install-skill.py` links it into Codex.
The reusable upstream operations skill is at `vendor/vanityctl/skills/vanityctl/SKILL.md`;
`vanityctl install --codex-skill` installs it alongside this host-specific skill.
