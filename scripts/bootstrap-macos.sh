#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != Darwin ]]; then
  echo 'This bootstrap is for macOS; see nix/ for Linux.' >&2
  exit 1
fi
if [[ "${1:---check}" == --install ]]; then
  command -v brew >/dev/null || { echo 'Install Homebrew from https://brew.sh first.' >&2; exit 1; }
  brew bundle --file Brewfile
  git submodule update --init --recursive
  cargo install --locked --path vendor/vanityctl --root "${VANITYCTL_INSTALL_ROOT:-$HOME/.local}"
  export PATH="${VANITYCTL_INSTALL_ROOT:-$HOME/.local}/bin:$PATH"
elif [[ "${1:---check}" != --check ]]; then
  echo 'Usage: scripts/bootstrap-macos.sh [--check|--install]' >&2
  exit 1
fi
for tool in git python3 docker vanityctl hostd cloudflared age; do
  command -v "$tool" || { echo "Missing: $tool" >&2; exit 1; }
done
docker info >/dev/null
echo 'Tooling ready. Use install-hostd.py on a fresh host, or vanityctl doctor on an existing host.'
