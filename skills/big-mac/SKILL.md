---
name: big-mac
description: Operate or migrate the SSH big-mac host using its infrastructure repo and vanityctl. Use for its Docker services, launchd jobs, Cloudflare tunnels, maintenance and setup.
---

The public source of operational knowledge is `ThatXliner/big-mac`, normally at
`~/Developer/big-mac` on SSH host `big-mac`. Other installations can use their own
checkout and SSH alias. Run host commands over SSH, not on the client Mac.

1. Read `docs/operations.md` in the checkout for ownership exceptions. Get the
   concise live index with `vanityctl agent-context` and inspect the requested
   target with `vanityctl status NAME --json`. Use `scripts/manage.py list` and
   `docs/services.md` to find services outside the registry; avoid broad searches.
2. Use `vanityctl` for registered workloads. `start` runs Compose **start**, so
   initial creation or a Compose config change needs targeted
   `python3 scripts/manage.py up PROJECT`. Do not use global `vanityctl apply`
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
Keep the canonical skill here; `scripts/install-skill.py` links it into Codex.
