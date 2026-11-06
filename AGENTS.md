# Project scope

This pyinfra deploy manages system packages and configuration on a local Fedora
host. User configuration, session startup, and Flatpak overrides belong in the
separate chezmoi dotfiles repository.

- Keep publishable defaults in `inventory.example.py`; never commit `inventory.py`.
- Preserve intentional feature selections and commented-out code unless asked
  to change them.
- Use inventory toggles for broad host features, not individual apps or fonts.
- Change future selections without adding cleanup of previous installations.
- Keep comments concise. Avoid package descriptions, service commentary, and
  notes that repeat the code.

# Implementation

- Package selections live in `packages/packages.py`; repository definitions live
  in `packages/repos.py`. Map third-party packages in `PACKAGE_REPOSITORIES` and
  use `install_packages` to enable their sources before installation.
- Repositories follow package selections, not inventory toggles. Never disable
  or remove repositories merely because they are no longer selected.
- Choose native packages versus Flatpak using upstream guidance, not RPM
  availability alone. Verify availability for the target Fedora release.
- Prefer fact-driven pyinfra operations. Guard shell operations so repeated
  deploys converge.
- Use `_if=[operation.did_change]` for runtime guards. Reserve `.will_change`
  for arguments resolved while building the deploy.
- The inventory is `@local`; plan-time subprocess checks inspect the local host.
- Respect socket-activated services; do not force libvirtd to remain running.

# Validation

Run checks appropriate to the change:

```bash
task lint
task check
./setup.sh --dry-run
```

The dry run requires sudo access. It does not apply changes, so repeating it
cannot establish convergence. Test idempotency with mocked states or, when a
real deployment is authorized, verify that a subsequent run has no unexpected
changes. Report checks blocked by the environment.
