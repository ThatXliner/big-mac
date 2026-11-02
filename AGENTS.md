# Working on big-mac

Read [skills/big-mac/SKILL.md](skills/big-mac/SKILL.md) before host operations.
Use the scripts and `vanityctl` so each session does not rediscover the host.
The checked-in inventory is an observation, not authority to reconcile every
service. Refresh live status for the requested target before changing it.

Keep credentials, environment values, logs, resolved Compose output, migration
plans and backups outside Git. The public inventory exporter is allowlisted.
Run `make check` and `make secrets` before publishing changes; inspect the staged
diff as well. Do not expand exporter fields to whole Docker/launchd objects.

When you say you'll implement something, actually do it.
When working on UI, ask Claude to design the interface.
