# System Setup Automation

pyinfra-based automation for bootstrapping and managing a personal Fedora workstation.

## Requirements

- Fedora 45
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
```

Use `setup.sh` for normal runs; `task deploy` and `task dry` use the same wrapper.
Direct pyinfra invocation applies the deploy without bootstrapping tools or running
the wrapper's system upgrade.

## Development

```bash
task lint     # ruff + shellcheck + yamllint
task check    # validate operation calls + file/template sources (no sudo needed)
task dry      # dry-run the deploy
```

The Fedora package is `go-task`; the binary it installs is `task`.

## Release identity

At the start of `modules/init.py`, the installed `fedora-release-identity-*`
package is swapped to `fedora-release-identity-basic`. This works independently
of the original spin. If basic is already installed, no swap is queued; if no
identity is installed, basic is installed directly. This changes the release
identity without selecting or removing a desktop environment.

## Desktop

KDE Plasma and Hyprland are enabled in the example inventory. Desktop toggles control
installation only: disabling a desktop does not uninstall it or switch the display
manager. Shared desktop applications are selected in `packages/packages.py`,
including Dolphin and its plugins, Ark, KDE thumbnail providers, Okular, Kate,
KWrite, KCalc, Gwenview, and native media and productivity apps. Commented-out
selections remain available for manual editing. Desktop package groups can also
install their own applications.

Application defaults, URL handlers, and desktop/session settings belong in chezmoi.

Wayland compositors (Niri, Hyprland) share a single desktop shell — **Noctalia** — rather
than a collection of separate bar/launcher/notification daemons. Enable either or both via
`desktop_environments` in `inventory.py`. The hypr* stack comes from the
`lionheartp/Hyprland` COPR.

## Selections

Inventory describes host differences: desktop environments, development, gaming,
Tailscale, account details, and mount definitions. Package lists describe the
preferred software; individual applications do not have inventory switches.

- Development includes VSCodium, Zed, CLI tools, containers, and virtualization.
- Fonts always include the selected Nerd Fonts.
- A nonempty `storage_mounts` list enables CIFS support and network automounts.
- `local_mounts` defines local mounts; absent device UUIDs are skipped.
- NVIDIA hardware detection selects the driver and its kernel build prerequisites.

The former `zed`, `nerd_fonts`, and `synology` inventory keys are no longer used.
Existing installations are not removed when a selection is disabled.

## Package sources

Native package selections automatically enable their required repositories before
installation. There are no repository toggles in inventory. Sources are declared
in `PACKAGE_REPOSITORIES` in `packages/packages.py`; definitions and installation
ordering live in `packages/repos.py`. This mapping enables sources; binding and
priority policy lives separately in `packages/repo_policy.py`.

`PACKAGE_BINDINGS` restricts `steam` to `rpmfusion-nonfree-steam` and `codium` to
`gitlab.com_paulcarroty_vscodium_repo`. Other repositories, including ones added
later, cannot supply those package names. Bindings do not pin versions or bind
dependencies automatically. Add explicit package names to this mapping when a
package family needs the same restriction, and keep its `PACKAGE_REPOSITORIES`
entry consistent.

For unbound packages, lower repository priority numbers are preferred:

| Sources | Priority |
| --- | --- |
| Fedora and Updates | 10 |
| RPM Fusion and Fedora Cisco OpenH264 | 20 |
| Configured LibreWolf, VSCodium and NVIDIA repositories | 30 |
| Selected Hyprland COPR | 40 |
| Terra | 50 |
| Other repositories | 99 |

The policy is written to `/etc/dnf/repos.override.d/99-zz-fedora-setup.repo`
before setup's tooling installation and first upgrade, and at the start of a
direct pyinfra deploy. It also applies to ordinary DNF5 updates. Dry runs only
plan the file change. Existing exclusions are preserved; repository enabled
states are not changed by the policy. DNF command-line overrides can bypass it.

Priorities can prefer an older package and can expose dependency conflicts; they
do not guarantee that packages from different repositories are compatible.
Bindings prevent future source substitution but do not reinstall or downgrade
already-installed packages. If a bound source is unavailable, DNF cannot fall
back to another repository for that package; an update may leave it installed
without upgrading it.

- Detected NVIDIA hardware selects `nvidia-open` and NVIDIA's Fedora 44 CUDA repo.
- Development selects VSCodium from its repository and Zed from Terra.
- Hyprland selects its COPR. Niri itself comes from Fedora.
- Wayland session extras (`uwsm`, `sway-audio-idle-inhibit`) require Terra.
- The default font selection requires Terra.
- Gaming selects native `steam` and the `rpmfusion-nonfree-steam` repository
  supplied by `fedora-workstation-repositories`. Steam is not selected as a Flatpak.
- GitHub CLI and Tailscale use Fedora without adding their vendor repos.

Unused repositories are never disabled or removed. Commenting out a package
module also skips enabling its required repositories. Source policy remains active
independently of package selections.
Existing Flatpak installations are not automatically removed.

LibreOffice, GIMP, Inkscape, Firefox, Chromium, VLC, RawTherapee, and Darktable
use native Fedora packages. LibreWolf uses its upstream RPM repository.
Slack installs from the official RPM download. Its included daily cron script
configures the repository for subsequent DNF updates.
Bitwarden, HandBrake, Zen, Tor Browser Launcher, Discord, Spotify,
Gear Lever, and Camera Controls remain Flatpaks. Existing installations and
application data are not removed or migrated.

Package format selection follows upstream guidance where available; RPM
availability alone is not a reason to switch. See [Bitwarden's format comparison](https://bitwarden.com/help/desktop-app-feature-support/),
[HandBrake installation](https://handbrake.fr/docs/en/latest/get-handbrake/download-and-install.html),
[Zen installation](https://docs.zen-browser.app/guides/install-linux), and
[LibreWolf's RPM repository](https://librewolf.net/installation/rhel/).
See also [Slack's RPM installation and updates](https://slack.com/help/articles/212924728-Download-Slack-for-Linux--beta-).

Host configuration lives in ignored `inventory.py`; `inventory.example.py`
shows its structure.

Native codecs use RPM Fusion Free's full `ffmpeg`, VLC freeworld plugins, and
GStreamer plugins, plus Cisco OpenH264. `modules/multimedia.py` runs from the
package module before desktop apps. It replaces `ffmpeg-free` in one transaction,
or installs full FFmpeg when absent; subsequent runs skip the replacement.
The NVIDIA driver source is unchanged. This does not configure GPU video acceleration.

Secret portal preferences in the dotfiles use `oo7-portal;gnome-keyring;`.
Fedora 44 installs GNOME Keyring and its PAM module; Fedora 45+ selects
`oo7-daemon`, `oo7-portal`, and `pam_oo7`. Portal fallback selects an available
backend; it does not migrate secrets or retry failed requests through another backend.
Niri and Hyprland use `mate-polkit`, started by their dotfiles through
`wm-polkit-agent.service`. COSMIC keeps its own authentication agent.

## Validation

```bash
task lint
task check
./setup.sh --dry-run
```

Static checks run locally; no CI workflow is currently configured. A dry run
requires Fedora, the local inventory, sudo, and pyinfra. It plans changes without
applying them; convergence checks require mocked states or a subsequent real run.

## License

MIT. See [LICENSE](LICENSE).
