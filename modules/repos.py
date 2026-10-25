"""Third-party package repositories, reconciled with the `repos` toggles in host data.

Runs before every module that installs packages, since the NAME_<REPO> halves of
the package lists resolve from here. A toggle set to True registers and enables
the repo; False disables it if dnf already knows it, and otherwise leaves it
alone. Nothing here removes a repo file.
"""

from pyinfra.context import host
from pyinfra.operations import dnf, server

from packages.repos import REPOS, disable_commands, enable_commands, repo_ids, repo_states

toggles = host.data.get("repos") or {}

# `dnf copr` and `dnf config-manager` are plugins, and fedora-workstation-repositories
# carries the .repo definitions for Fedora's blessed third-party sources (all
# disabled). Both have to exist before anything below can register a repo.
dnf.packages(
    name="Install dnf plugins and workstation repo definitions",
    packages=["dnf5-plugins", "fedora-workstation-repositories"],
)

# One `dnf repolist` for every repo rather than a subprocess per check.
states = repo_states()
repos_changed = False

for key, repo in REPOS.items():
    # An entry controls its primary id plus any siblings the same release package
    # registers (rpmfusion-*-updates). "Registered" is judged on the primary;
    # enabled/disabled has to hold for every id, or a sibling keeps serving
    # packages after the toggle goes off.
    rid, *_ = ids = repo_ids(repo)
    registered = rid in states
    id_states = [states.get(i) for i in ids]

    if toggles.get(key, False):
        if not all(s == "enabled" for s in id_states):
            server.shell(
                name=f"Enable {rid} repository",
                commands=enable_commands(repo, registered=registered),
            )
            repos_changed = True
    elif any(s == "enabled" for s in id_states):
        server.shell(
            name=f"Disable {rid} repository",
            commands=disable_commands(repo),
        )

# Refresh only when a repo was actually added or enabled, so every install after
# this point resolves against metadata that includes it.
if repos_changed:
    server.shell(
        name="Refresh DNF cache",
        commands=["dnf makecache --refresh"],
    )
