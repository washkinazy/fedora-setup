# Repository guidance

This is a pyinfra deploy for a Fedora 45 KDE Plasma workstation. It manages
system packages and configuration on the local host. User configuration is
managed separately with chezmoi; do not add user Flatpak overrides or dotfiles
here.

## Execution flow

`setup.sh` validates Fedora and the local inventory, ensures pyinfra is present,
keeps the sudo timestamp alive, optionally updates the system, and runs:

```bash
pyinfra inventory.py deploy.py --sudo
```

`deploy.py` validates inventory data and includes modules in this order:

1. `modules/init.py` — kernel build prerequisites
2. `modules/system.py` — DNF, mDNS, sysctl, and zram configuration
3. `modules/repos.py` — third-party repository reconciliation
4. `modules/hardware.py` — detected NVIDIA hardware and the Logitech sleep hook
5. `modules/storage.py` — optional Synology and local disk mounts
6. `modules/packages.py` — RPM and Flatpak applications and optional features
7. `modules/user_account.py` — group membership and GECOS name

The inventory is intentionally local and ignored. Keep publishable defaults in
`inventory.example.py`; never commit `inventory.py`.

## Package and repository rules

- Fedora KDE Plasma Desktop is the baseline. Keep core desktop integration and
  command-line tools native; additional GUI applications generally use Flatpak.
- Repository definitions live in `packages/repos.py`. Every definition has a
  matching inventory toggle and is reconciled before package installation.
- Package lists live in `packages/packages.py`. A package available only from a
  third-party source belongs in a `NAME_<REPO>` list and is selected with
  `with_repo_packages`.
- Terra base supplies the configured Nerd Fonts, Zed, `uwsm`, and
  `sway-audio-idle-inhibit` when enabled.
- The standalone Negativo17 NVIDIA repository supplies `akmod-nvidia` and the
  matching driver packages. Do not combine it with Terra NVIDIA, RPM Fusion
  NVIDIA, Negativo17 multimedia, or NVIDIA's CUDA repository.
- `terra_nvidia` is a migration-only toggle retained so an existing repo can be
  disabled. It must remain false; use `negativo17_nvidia` instead.
- Niri also exists in Fedora; its COPR is optional and only supplies a newer
  build. GitHub CLI and Tailscale likewise remain installable from Fedora while
  their vendor repositories are off.
- Hyprland and its COPR are supported by the code but disabled in both
  inventories.
- Flatpak permissions are owned by the separate dotfiles repository. Do not add
  `flatpak override` operations here.

## Operational rules

- This inventory is `@local`. Plan-time subprocess checks are therefore local by
  design.
- Prefer fact-driven pyinfra operations. Guard unavoidable `server.shell`
  operations so the second deploy converges.
- Use `_if=[operation.did_change]` for runtime guards. Use `.will_change` only
  for operation arguments that must be resolved while building the deploy.
- Do not manage libvirtd as continuously running; it is socket activated.
- Local storage is mounted below `/storage`; Synology mounts are below
  `/synology`.
- Secure Boot MOK enrollment is interactive and remains outside this deploy.

## Verification

Run before committing:

```bash
task lint
task check
./setup.sh --dry-run
```

Run the dry deploy twice when changing idempotency-sensitive operations. The
second run should report no changes.
