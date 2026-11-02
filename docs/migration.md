# Moving the host

The public repo is the operations layer and service map. Private application
configuration, custom images, model files and databases must travel separately.
No passwords, JWTs, tunnel certificates, environment files, database dumps or raw
plists are checked in. The inventory is a point-in-time map, not a complete
backup or a declaration to recreate every historical container.

## Export while the old host still works

Install `age` on the service host. Generate an age identity on a separate trusted
recovery machine (`age-keygen -o backup.agekey`), keep it mode 0600, and store a
second protected copy. Give the service host only the public recipient printed
by `age-keygen -y backup.agekey`. Losing that private identity loses the backups.

On the old host, create and review a private plan:

```sh
python3 scripts/migration.py plan
# Inspect local/migration-plan.json privately. Add missing application/config/data
# paths, especially external disks, nonstandard secret files and model caches.
```

The plan contains Compose input locations, Git source directories and revisions,
launchd files/executables, bind mounts, named volumes and Docker images. It also
includes known native model/Minecraft state and network configuration roots.
Paths are editable: review them before running exports, both to include missing
dependencies and to avoid archiving unrelated files. Config exports include the
plan for recovery. Source exports include untracked changes and `.git`, but
exclude `node_modules`, virtualenvs, `.next`, Rust `target` and Python bytecode;
reinstall those dependencies from app lockfiles on the new host.

Set `BACKUP_RECIPIENT` to your public age recipient, then:

```sh
python3 scripts/migration.py config --recipient "$BACKUP_RECIPIENT" --output "$HOME/Backups/big-mac/config.tar.gz.age"
python3 scripts/migration.py sources --recipient "$BACKUP_RECIPIENT" --output "$HOME/Backups/big-mac/sources.tar.gz.age"
python3 scripts/migration.py images --recipient "$BACKUP_RECIPIENT" --output "$HOME/Backups/big-mac/images.tar.age"
python3 scripts/migration.py databases --recipient "$BACKUP_RECIPIENT" --output "$HOME/Backups/big-mac/databases"
```

Each producer streams directly into age; no plaintext archive is written.
An existing output file is never overwritten. Failed partial outputs are removed.
Use a new dated destination for each run. Keep copies on a separate device/storage
location and record checksums (`shasum -a 256 ...`) before the old host disappears.

The database command discovers running PostgreSQL containers by `PG_MAJOR` and
uses `pg_dumpall` through local container authentication. Verify the expected
clusters are present; a nonstandard database may need its own command. If local
authentication is disabled, use that application's existing backup procedure.
Coordinate application writes during the final dumps, and test restoring them.
Other databases, Redis persistence and application-upload directories require
their own checks; a SQL dump alone is not a complete application backup.

Several current images only exist locally as `local-security/...` rebuilds.
Export images before losing the host, and preserve their build sources (including
the security-update directories) in the source/private plan. `docker save` archives
image layers and configuration, which can themselves contain private values;
the image export is encrypted too. Images and compiled native dependencies can
be architecture-specific.

## Cold data export and cutover

Choose a maintenance window. Stop scheduled writers, auto-deployers and native
model/Minecraft processes deliberately, then stop the affected application and
database stacks. The script never stops production services for you. For the
full cold data export it refuses to proceed while any Docker container runs;
also verify native writers are stopped before asserting `--writers-stopped`.

```sh
python3 scripts/migration.py data --writers-stopped \
  --volume-helper YOUR_INSTALLED_IMAGE_WITH_TAR \
  --recipient "$BACKUP_RECIPIENT" --output "$HOME/Backups/big-mac/data"
```

Use an already installed, trusted helper image containing `tar`, preferably
pinned by digest, and compatible with volume ownership/metadata. The helper has
no network and mounts one volume read-only. Bind/native data and each named volume
get separate encrypted archives. Review nested/overlapping paths in the plan to
avoid duplicate exports. Preserve file owners, permissions, ACLs and extended
attributes when the application depends on them; these generic tar exports do
not replace an application's specialized backup procedure. Root-owned files may
require a privileged export using the already reviewed plan.

## Restore and verify before changing DNS

1. Bootstrap the new Mac's tooling, or prepare Linux separately. Clone this repo
   with its pinned submodule. Restore each encrypted archive into a private
   **staging directory** first. Archive members use old absolute paths with the
   leading slash removed; review them before copying to the new host.
2. Map the old user home to the new home. Review absolute paths in Compose bind
   mounts, plists, `.env` and vanityctl fragments; examples use your own account
   and domain. Keep originals for rollback. Reinstall language dependencies and
   native binaries for the new OS/architecture. Source archives preserve local
   app changes that a fresh Git clone would miss.
3. Restore images with `age -d -i backup.agekey images.tar.age | docker load`.
   Restore bind data and named volumes with their original ownership, or use
   logical SQL restores into clean databases. Do not combine a physical database
   data directory with an incompatible major version. Reuse the original cluster
   credentials/JWT signing secrets when existing sessions/data require them.
4. Restore private config and the registry. Run `vanityctl config validate` and
   `vanityctl doctor`. Load native agents individually after inspecting their
   restored plist and dependencies; never blindly bootstrap all historical files.
   Restore system daemons separately with administrator privileges. Reauthorize
   Tailscale and macOS permissions as needed; those device identities are not
   created by the public bootstrap.
5. Bring up one Compose project at a time with `scripts/manage.py up PROJECT`.
   Verify DB connections, auth, uploads, jobs, application health and local ports.
   Verify login and a real proxy request for unblock. Validate Cloudflare ingress
   and test the new tunnel before switching the public route. Avoid simultaneously
   running old and new scrapers, deployers or scheduled import jobs.
6. Switch traffic, observe the applications, then keep the old host and encrypted
   exports until restore tests and the cutover pass. A failed check means restore
   the prior routing and keep the old services available.

Example decrypt-to-staging (on a trusted machine, with private directory access):

```sh
mkdir -m 700 restore-staging
age -d -i backup.agekey config.tar.gz.age | tar -xzf - -C restore-staging
```

No production data migration or test restoration is performed merely by creating
this repository. See [the NixOS notes](../nix/README.md) for the optional Linux
starting point and the Apple-specific workloads that still need porting.
