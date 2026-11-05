# Operations

Run commands on the service host, from this checkout. `vanityctl agent-context`
gives a concise service index. `vanityctl agent-context NAME --json` gives focused
operational context; `vanityctl discover QUERY --json` finds existing unregistered
resources without changing them. `scripts/manage.py` handles existing Compose,
native launchd, and standalone Docker targets using the same inventory.

```sh
python3 scripts/manage.py list
python3 scripts/manage.py status
vanityctl status unblock --json
vanityctl logs unblock --lines 30
vanityctl restart unblock
python3 scripts/manage.py status launchd:com.bryanhu.cloudflared
```

`manage.py status` without a target lists all Docker states as well as registered
services. Native jobs require the explicit `launchd:LABEL` form; root-owned agents
use the system domain and may need administrator privileges for mutations.
Standalone containers use `container:NAME`. Logs and launchctl output can contain
private data and should not be committed.

## Registry and ownership

The live registry is `~/.vanityctl/config.yaml` plus
`~/.vanityctl/services/*.yaml`. It contains private paths/config and stays off
Git; the public repo provides examples, setup scripts and the observed inventory.
The pinned `vendor/vanityctl` submodule is the implementation and documentation.
Updating it does not silently upgrade the installed binary.

The initial setup added all seven previously unregistered Compose projects,
bringing the registry to 19 Compose projects and two existing process entries.
Registration only writes additive fragments and validates them. It does not
recreate containers or change their original Compose files. To register a newly
discovered existing stack:

```sh
python3 scripts/manage.py refresh
python3 scripts/register-compose.py             # show plan
python3 scripts/register-compose.py --execute   # additive registration
python3 scripts/catalog.py
```

Already registered entries retain their configuration, including extra overlays.
The inventory records Compose files from container labels, which can differ from
the registry. Check `vanityctl describe NAME --json` privately before reconciling
a stack. In particular, Quillium's registry includes a relay overlay while some
container labels only identify the base file. Preserve the registry's file order.
qbot references a security image override outside its app directory.

### Cloudflare ownership mismatch

At the initial snapshot, `cloudflare-tunnel` and `cloudflare-ollama` in vanityctl
were stopped. The live primary tunnel was owned by the separate user agent
`com.bryanhu.cloudflared`. Legacy generated plists also exist, including a
Supabase tunnel. Installed files alone do not prove that a service runs.
Use `launchctl print gui/$(id -u)/LABEL` and inspect the existing process before
changing tunnel ownership. The unblock installation restarted only the live
`com.bryanhu.cloudflared` agent to load its additive route.

### Startup and updates

Docker's restart policies and existing launch agents remain the startup owners.
`vanityctl start` invokes Compose `start`, which cannot create a missing container.
Initial creation and config/image changes use targeted `vanityctl up`, which
re-reads Compose environment files and preserves registered overlay order:

```sh
vanityctl up unblock
```

The unblock image is pinned to the tested digest. To update, pull and inspect the
new image, set `LADDER_IMAGE` in the private service `.env`, run targeted `up`, and
run both health checks. Roll back by restoring the prior image value and repeating
targeted `up`. Rules are downloaded on startup from Ladder's upstream ruleset;
set `LADDER_RULESET` to a commit-pinned URL or local maintained source if rules
must be immutable too. Avoid automatic mass image pulls: many existing images are
local security rebuilds, and several app repos contain uncommitted changes.

## Unblock

Ladder is reachable at `https://unblock.bryanhu.com`. Its port is bound to loopback
and reached through the existing tunnel. The current deployment allows anonymous
access, as requested by the operator. Set `UNBLOCK_USERPASS=` in the private `.env`
to disable basic auth, or set `UNBLOCK_USERPASS=username:password` to enable it,
then run targeted `up`. Setup on a fresh host generates
a unique login in `services/unblock/.env` with mode 0600, and URL access logging
is disabled. Retrieve credentials privately over SSH; do not paste the `.env`
into tickets or public logs.

```sh
python3 scripts/check-unblock.py
python3 scripts/check-unblock.py --url https://unblock.bryanhu.com
```

These check the configured access mode, the form, and a real proxied page.
Some sites still block automated clients or never serve full content; an
installation health check cannot guarantee results for every publisher.

To add a route to an existing local tunnel on another host:

```sh
python3 scripts/tunnel-route.py unblock.example.com 8093 --restart-label YOUR.EXISTING.LABEL
```

The script preserves unrelated routes, backs up the original config beside it,
validates ingress, and creates DNS without overwriting unrelated DNS records.
It supports the conventional local config with a final `http_status:404` ingress.
For rollback, restore the indicated config backup, restart that agent, and remove
only the newly created DNS record through your Cloudflare account. Other tunnel
routes can briefly reconnect during an agent restart.

### Redirect aliases

`https://12ft.bryanhu.com` permanently redirects to `https://unblock.bryanhu.com`,
preserving the path, query string and HTTP method (308). The loopback server on
port 8094 is the registered native service `unblock-alias`, supervised by
vanityctl/launchd. It writes no access logs and uses the existing primary tunnel.

```sh
vanityctl agent-context unblock-alias --json
vanityctl status unblock-alias --json
curl -I https://12ft.bryanhu.com/
```

To reproduce this on a new host, or create your own alias, choose an unused port
and your destination origin, then add the incoming hostname to your existing
tunnel:

```sh
python3 scripts/setup-redirect.py unblock-alias https://unblock.example.com --port 8094
python3 scripts/tunnel-route.py 12ft.example.com 8094 --restart-label YOUR.EXISTING.LABEL
```

The setup helper records the Python executable and service paths for the current
host in its private vanityctl registry. It starts only the named redirect. Keep
that service running when moving the tunnel; the NixOS example does not yet
include this optional alias. To remove it, stop `unblock-alias` with vanityctl,
remove its registry fragment, and remove only its DNS record and tunnel ingress.

## Public metadata and secrets

`scripts/inventory.py` exports image references/digests, mount topology, port
bindings, Compose file locations, environment **key names**, Git source revisions,
launchd executables/schedules, and loopback tunnel destinations. It never exports
environment values, command arguments, arbitrary Docker labels, logs or tunnel
credentials. Refresh and review it before committing.

Use `make check` and `make secrets` before publishing. Gitleaks checks the main
repo history and tracked working files, including staged files before the first
commit. The submodule is a separately maintained public repository. `.gitignore`
is a convenience, not a confidentiality boundary: never force-add private state.
