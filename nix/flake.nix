{
  description = "Optional NixOS starting point for big-mac's portable services";
  outputs = { self }: {
    nixosModules.default = import ./module.nix;
  };
}
