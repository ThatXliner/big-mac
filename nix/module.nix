{ config, lib, pkgs, ... }:
let
  cfg = config.services.big-mac;
in {
  options.services.big-mac = {
    enable = lib.mkEnableOption "big-mac host tooling and Docker";
    unblock = {
      enable = lib.mkEnableOption "Ladder on loopback (publish with your own tunnel)";
      port = lib.mkOption { type = lib.types.port; default = 8093; };
      environmentFile = lib.mkOption {
        type = lib.types.str;
        default = "/var/lib/big-mac/secrets/unblock.env";
        description = "Runtime-only file containing USERPASS=user:password. Never put secret text in Nix.";
      };
      image = lib.mkOption {
        type = lib.types.str;
        default = "ghcr.io/everywall/ladder@sha256:cf30c32ac046a5554a4e829f46546d68ed6056986ba5ba83c65a5a705828d5fe";
      };
    };
  };
  config = lib.mkIf cfg.enable {
    virtualisation.docker.enable = true;
    environment.systemPackages = with pkgs; [ age git jq python3 cloudflared ];
    virtualisation.oci-containers = lib.mkIf cfg.unblock.enable {
      backend = "docker";
      containers.unblock = {
        image = cfg.unblock.image;
        ports = [ "127.0.0.1:${toString cfg.unblock.port}:8080" ];
        environmentFiles = [ cfg.unblock.environmentFile ];
        environment = {
          PORT = "8080";
          RULESET = "https://raw.githubusercontent.com/everywall/ladder-rules/main/ruleset.yaml";
          LOG_URLS = "false";
          NOLOGS = "true";
          EXPOSE_RULESET = "false";
        };
        extraOptions = [ "--read-only" "--cap-drop=ALL" "--security-opt=no-new-privileges:true" "--tmpfs=/tmp:size=16m,mode=1777" ];
      };
    };
  };
}
