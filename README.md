# System Setup Automation

pyinfra-based automation for bootstrapping and managing a Fedora KDE Plasma desktop.

## Requirements

- Fedora 45 KDE Plasma Desktop
- uv + pyinfra (installed by `setup.sh` if missing)
- sudo access for system configuration

This is an opinionated personal workstation configuration, not a general-purpose
Fedora installer. Read the inventory and operations before running it. The deploy
updates packages, adds third-party repositories, changes system configuration,
installs passwordless polkit rules for members of `wheel`, and uses sudo throughout.

User-level configuration is intentionally out of scope. It is applied separately
with chezmoi, including Flatpak overrides and desktop/session configuration.

## Usage

Create the local inventory first. It is intentionally ignored by Git so hostnames,
mounts, device UUIDs, and account details are not published:

```bash
cp inventory.example.py inventory.py
$EDITOR inventory.py
```

```bash
./setup.sh                 # Full setup
./setup.sh --dry-run       # Dry run; requires pyinfra to already be installed
./setup.sh --skip-update   # Skip the system package update

# Run pyinfra directly (from the repo root — paths inside the deploy are relative)
pyinfra inventory.py deploy.py --sudo
pyinfra inventory.py deploy.py --sudo --dry
```

## Development

```bash
task lint     # ruff + shellcheck + yamllint
task check    # validate operation calls + file/template sources (no sudo needed)
task dry      # dry-run the deploy
```

The Fedora package is `go-task`; the binary it installs is `task`.

## Desktop

Wayland compositors (Niri, Hyprland) share a single desktop shell — **Noctalia** — rather
than a collection of separate bar/launcher/notification daemons. Enable either or both via
`desktop_environments` in `inventory.py`. The hypr* stack comes from the
`lionheartp/Hyprland` COPR.

## Package sources

The Fedora KDE Spin is the baseline. Desktop components, hardware integration,
development tools, and the applications shipped as part of that baseline remain
RPM packages. Additional GUI applications are installed from Flathub, including
Steam and codec-consuming media applications, so the host does not need a
third-party multimedia repository.

RPM packages resolve from Fedora plus only the third-party sources enabled in
`inventory.py`. The example inventory enables Fedora's OpenH264 repository and the
VSCodium repository; Terra, Negativo17 NVIDIA, COPRs, RPM Fusion, GitHub CLI,
Tailscale, and the remaining Negativo17 repositories are explicit opt-ins. VSCodium
is installed as the native `codium` RPM when development tooling is enabled.
`modules/repos.py` reconciles every toggle before additional packages are installed.

Each dnf group in `packages/packages.py` is split by source: `NAME_<REPO>` holds
what only that repo carries. The deploy includes those packages only while their
source repository is enabled. Known incompatible repository combinations fail
before any repository configuration is changed.

Host configuration (hostname, feature flags, repo toggles, mounts, user) lives in
the ignored `inventory.py`; `inventory.example.py` documents the publishable shape.

For NVIDIA systems, this deploy uses Negativo17's standalone repository and its
`akmod-nvidia` package. Secure Boot requires enrolling the akmods Machine Owner Key;
that interactive firmware step is not automated here. Do not combine this source
with Terra NVIDIA, RPM Fusion NVIDIA, or NVIDIA's CUDA repository.

## Validation

```bash
task lint
task check
./setup.sh --dry-run
```

The static checks run in CI. A dry run requires Fedora, the local inventory, sudo,
and pyinfra, so it remains a local pre-deployment check.

## License

MIT. See [LICENSE](LICENSE).
