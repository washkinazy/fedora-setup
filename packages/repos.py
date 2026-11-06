"""Repository definitions required by the selected native packages."""

import subprocess
import sys

COPR_HOST = "copr.fedorainfracloud.org"
TERRA_URL = "https://repos.fyralabs.com/terra$releasever"


def _terra_release(package):
    return f"--nogpgcheck --repofrompath 'terra,{TERRA_URL}' {package}"


REPOS = {
    "rpmfusion_free": {
        "kind": "rpm",
        "id": "rpmfusion-free",
        "siblings": ["rpmfusion-free-updates"],
        "install": (
            "https://mirrors.rpmfusion.org/free/fedora/"
            "rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm"
        ),
    },
    "fedora_cisco_openh264": {
        "kind": "builtin",
        "id": "fedora-cisco-openh264",
        "prerequisites": ["fedora-repos"],
    },
    "librewolf": {
        "kind": "repofile",
        "id": "librewolf",
        "url": "https://repo.librewolf.net/librewolf.repo",
    },
    "rpmfusion_nonfree_steam": {
        "kind": "builtin",
        "id": "rpmfusion-nonfree-steam",
        "prerequisites": ["fedora-workstation-repositories"],
    },
    "terra": {
        "kind": "rpm",
        "id": "terra",
        "install": _terra_release("terra-release"),
    },
    "copr_hyprland": {
        "kind": "copr",
        "copr": "lionheartp/Hyprland",
    },
    "vscodium": {
        "kind": "commands",
        "id": "gitlab.com_paulcarroty_vscodium_repo",
        "install": [
            (
                "printf '%s\\n' '[gitlab.com_paulcarroty_vscodium_repo]' "
                "'name=gitlab.com_paulcarroty_vscodium_repo' "
                "'baseurl=https://paulcarroty.gitlab.io/vscodium-deb-rpm-repo/rpms/' "
                "'enabled=1' 'gpgcheck=1' 'repo_gpgcheck=1' "
                "'gpgkey=https://gitlab.com/paulcarroty/"
                "vscodium-deb-rpm-repo/raw/master/pub.gpg' "
                "'metadata_expire=1h' > /etc/yum.repos.d/vscodium.repo"
            ),
        ],
    },
    "nvidia_cuda": {
        "kind": "repofile",
        "id": "cuda-fedora44-x86_64",
        "url": (
            "https://developer.download.nvidia.com/compute/cuda/repos/"
            "fedora44/x86_64/cuda-fedora44.repo"
        ),
    },
}


def repo_id(repo):
    """Return the primary dnf repo id for a REPOS entry."""
    if repo["kind"] == "copr":
        owner, project = repo["copr"].split("/", 1)
        return f"copr:{COPR_HOST}:{owner}:{project}"
    return repo["id"]


def repo_ids(repo):
    """Return every repo id a REPOS entry controls: the primary first, then siblings."""
    return [repo_id(repo), *repo.get("siblings", [])]


def _enable_setopt(repo):
    """One `config-manager setopt` that enables every id the entry controls."""
    settings = " ".join(f"{rid}.enabled=1" for rid in repo_ids(repo))
    return f"dnf config-manager setopt {settings}"


def repo_states():
    """Return {repo_id: "enabled" | "disabled"} for every repo dnf knows about."""
    result = subprocess.run(
        ["dnf", "repolist", "--all"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.exit(
            f"dnf repolist could not read the repo configuration: {result.stderr.strip()}\n"
            "Fix the config before deploying; guessing here re-registers repos."
        )

    states = {}
    for line in result.stdout.splitlines():
        fields = line.split()
        # Repository names may contain spaces; parse only the first and last columns.
        if len(fields) >= 2 and fields[-1] in ("enabled", "disabled"):
            states[fields[0]] = fields[-1]
    return states


def enable_commands(repo, registered):
    """Commands that make a repo enabled, given whether dnf already knows it."""
    kind = repo["kind"]
    if kind == "copr":
        return [f"dnf copr enable -y {repo['copr']}"]
    if registered or kind == "builtin":
        return [_enable_setopt(repo)]
    if kind == "rpm":
        return [f"dnf install -y {repo['install']}"]
    if kind == "repofile":
        return [f"dnf config-manager addrepo --from-repofile={repo['url']}"]
    if kind == "commands":
        return repo["install"]
    sys.exit(f"Unknown repo kind {kind!r} in packages/repos.py")


# Cache planned repository state per host.
_planned_states = {}


def ensure_package_repositories(packages):
    """Enable sources required by a package selection."""
    from pyinfra.context import host
    from pyinfra.operations import dnf, server

    from packages.packages import PACKAGE_REPOSITORIES

    required = sorted({PACKAGE_REPOSITORIES[p] for p in packages if p in PACKAGE_REPOSITORIES})
    if required:
        if host.name not in _planned_states:
            _planned_states[host.name] = repo_states()
        states = _planned_states[host.name]
        pending = [
            key
            for key in required
            if any(states.get(rid) != "enabled" for rid in repo_ids(REPOS[key]))
        ]
        if pending:
            dnf.packages(name="Install DNF repository plugins", packages=["dnf5-plugins"])
            for key in pending:
                repo = REPOS[key]
                rid = repo_id(repo)
                if rid not in states and repo.get("prerequisites"):
                    dnf.packages(
                        name=f"Install {rid} repository definition",
                        packages=repo["prerequisites"],
                    )
                server.shell(
                    name=f"Enable {rid} repository",
                    commands=enable_commands(repo, registered=rid in states),
                )
                states.update(dict.fromkeys(repo_ids(repo), "enabled"))
            server.shell(name="Refresh DNF cache", commands=["dnf makecache --refresh"])


def install_packages(*, name, packages, **kwargs):
    """Enable sources required by this selection, then queue its DNF install."""
    from pyinfra.operations import dnf

    ensure_package_repositories(packages)
    return dnf.packages(name=name, packages=packages, **kwargs)
