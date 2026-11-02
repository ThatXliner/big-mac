# NixOS migration starting point

This optional module enables Docker and host tools, and defines the portable
Ladder service. It is not a conversion of the entire Mac and has not been deployed
to NixOS. Existing Compose applications remain Compose applications; preserve
their config/data with the migration tooling before moving them.

Import `module.nix` from your existing, pinned NixOS configuration, or use the
flake's `nixosModules.default`:

```nix
services.big-mac = {
  enable = true;
  unblock.enable = true;
  unblock.environmentFile = "/var/lib/big-mac/secrets/unblock.env";
};
```

Provision that file privately with `USERPASS=your-user:your-password` and mode 0600
before enabling the service. The macOS Compose file calls this variable
`UNBLOCK_USERPASS`; Ladder itself uses `USERPASS`. Configure your own Cloudflare
tunnel to `http://localhost:8093`.

Port the launch agents individually to systemd units/timers. Apple MLX/MPS model
servers need a different backend on Linux, and macOS binary/virtualenv archives
must be rebuilt. `vanityctl` currently manages native processes with launchd;
do not assume its native backend supports systemd. `inventory/observed.json`
records the agents, schedules, local image dependencies and volume topology to
make that conversion explicit.
