"""Third-party DNF repositories and the state check that gates their registration.

Lives under packages/ rather than modules/ because pyinfra include()s the files in
modules/ rather than importing them, so nothing there can be shared. modules/repos.py
walks REPOS and reconciles each entry with its toggle in host data (`repos` in
inventory.py); the NAME_<REPO> halves of the lists in packages/packages.py record
which packages depend on which entry.

Every registration goes through `server.shell`, which pyinfra cannot make
idempotent. `repo_states()` is what stops them re-running, and what gates the
`dnf makecache` that follows a repo being added.
"""

import subprocess
import sys

COPR_HOST = "copr.fedorainfracloud.org"
TERRA_URL = "https://repos.fyralabs.com/terra$releasever"


def _terra_release(package):
    """`dnf install` arguments that fetch a Terra release package from the repo URL.

    Every terra-release-* package lives in the base terra repo, so they go through
    --repofrompath rather than the terra.repo file: that file may have been written
    moments earlier in the same run, and Terra sets skip_if_unavailable, so a
    not-yet-loaded repo is skipped silently and the install reports "No match for
    argument".
    """
    return f"--nogpgcheck --repofrompath 'terra,{TERRA_URL}' {package}"


# Keyed by the toggle name used in inventory.py. `kind` selects how the repo is
# registered when absent:
#   builtin  — the .repo file ships with fedora-repos, disabled; just flip enabled=1
#   rpm      — `dnf install -y <install>`: a release RPM that drops the .repo file(s),
#              given as a URL or as a package name plus the --repofrompath to find it
#   copr     — dnf copr enable
#   repofile — dnf config-manager addrepo --from-repofile
#   commands — fixed setup commands for a vendor that publishes repo contents but
#              no standalone .repo file
# `id` is the repo id as `dnf repolist` prints it; for COPRs it is derived from
# `copr` (owner/project) since dnf names those repos itself. `siblings` lists
# further repo ids the same release package registers enabled — they are toggled
# together with `id`, otherwise disabling the toggle leaves packages resolving
# from the sibling.
REPOS = {
    # Shipped by fedora-workstation-repositories and switched on when "third-party
    # repositories" is enabled in Discover/GNOME Software. Both serve RPM Fusion
    # nonfree packages that collide with the selected NVIDIA driver source, so they
    # are listed first and toggled off, and get disabled before anything else is
    # registered.
    "rpmfusion_nonfree_steam": {
        "kind": "builtin",
        "id": "rpmfusion-nonfree-steam",
    },
    "rpmfusion_nonfree_nvidia_driver": {
        "kind": "builtin",
        "id": "rpmfusion-nonfree-nvidia-driver",
    },
    "rpmfusion_free": {
        "kind": "rpm",
        "id": "rpmfusion-free",
        "siblings": ["rpmfusion-free-updates"],
        "install": (
            "https://mirrors.rpmfusion.org/free/fedora/"
            "rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm"
        ),
    },
    "rpmfusion_nonfree": {
        "kind": "rpm",
        "id": "rpmfusion-nonfree",
        "siblings": ["rpmfusion-nonfree-updates"],
        "install": (
            "https://mirrors.rpmfusion.org/nonfree/fedora/"
            "rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm"
        ),
    },
    # Terra (Fyra Labs) — https://docs.terrapkg.com/. The base repo, then its
    # subrepos, each registered by a terra-release-<name> package that lives in the
    # base repo — so `terra` stays first, since REPOS is walked in order. Terra's
    # docs warn the subrepos can conflict with Fedora and RPM Fusion packages.
    "terra": {
        "kind": "rpm",
        "id": "terra",
        "install": _terra_release("terra-release"),
    },
    # Legacy Terra NVIDIA source. Retained so a False toggle actively disables it
    # during migration to Negativo17; no package group resolves from it now.
    "terra_nvidia": {
        "kind": "rpm",
        "id": "terra-nvidia",
        "install": _terra_release("terra-release-nvidia"),
    },
    # Patched versions of packages Fedora also ships (RARLAB unrar among them).
    "terra_extras": {
        "kind": "rpm",
        "id": "terra-extras",
        "install": _terra_release("terra-release-extras"),
    },
    # Patched, codec-complete Mesa.
    "terra_mesa": {
        "kind": "rpm",
        "id": "terra-mesa",
        "install": _terra_release("terra-release-mesa"),
    },
    # Codecs; Terra marks this one unstable. negativo17_multimedia covers ffmpeg.
    "terra_multimedia": {
        "kind": "rpm",
        "id": "terra-multimedia",
        "install": _terra_release("terra-release-multimedia"),
    },
    "fedora_cisco_openh264": {
        "kind": "builtin",
        "id": "fedora-cisco-openh264",
    },
    "copr_niri": {
        "kind": "copr",
        "copr": "yalter/niri",
    },
    # The COPR the Hyprland wiki points Fedora at (a fork of solopasha/hyprland
    # with extra packages). Nothing hypr* except the hyprcursor/hyprutils libraries
    # is in Fedora proper. It also carries kitty, qt6ct, nwg-look, waypaper and
    # uwsm, which then resolve from whichever repo has the newer build.
    "copr_hyprland": {
        "kind": "copr",
        "copr": "lionheartp/Hyprland",
    },
    "gh_cli": {
        "kind": "repofile",
        "id": "gh-cli",
        "url": "https://cli.github.com/packages/rpm/gh-cli.repo",
    },
    # VSCodium documents this repo definition inline rather than publishing a
    # standalone .repo file. Write the documented RPM repository definition
    # when it is not registered yet; dnf imports the configured signing key.
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
    "tailscale": {
        "kind": "repofile",
        "id": "tailscale-stable",
        "url": "https://pkgs.tailscale.com/stable/fedora/tailscale.repo",
    },
    # Negativo17's standalone NVIDIA repository. This supplies the matching
    # userspace, CUDA runtime, and akmod packages without enabling its multimedia
    # repository. Do not combine it with another NVIDIA packaging source.
    "negativo17_nvidia": {
        "kind": "repofile",
        "id": "fedora-nvidia",
        "url": "https://negativo17.org/repos/fedora-nvidia.repo",
    },
    # negativo17's Spotify repackaging — https://negativo17.org/spotify-client/.
    # Self-contained: needs no other third-party repo, and uses the system ffmpeg
    # for local-file playback when one is installed.
    "negativo17_spotify": {
        "kind": "repofile",
        "id": "fedora-spotify",
        "url": "https://negativo17.org/repos/fedora-spotify.repo",
    },
    # negativo17's multimedia stack — https://negativo17.org/multimedia/. Supplies
    # the full ffmpeg (with NVENC, linked against the same nvidia-driver-cuda-libs
    # naming the standalone Negativo17 NVIDIA repo uses) and its own builds of vlc, libva, the
    # gstreamer plugins and more, all versioned to win over Fedora's. Its author
    # states it is NOT compatible with RPM Fusion, so both rpmfusion_* toggles
    # must be off while this one is on.
    "negativo17_multimedia": {
        "kind": "repofile",
        "id": "fedora-multimedia",
        "url": "https://negativo17.org/repos/fedora-multimedia.repo",
    },
}


def validate_repo_configuration(toggles, desktop_envs):
    """Return configuration errors that should stop a deploy before operations run."""
    errors = []

    unknown = sorted(set(toggles) - set(REPOS))
    if unknown:
        errors.append(f"unknown repo toggle(s) {unknown}; see REPOS in packages/repos.py")

    enabled_rpmfusion = sorted(
        key for key, enabled in toggles.items() if key.startswith("rpmfusion_") and enabled
    )
    if toggles.get("negativo17_multimedia") and enabled_rpmfusion:
        errors.append(
            "negativo17_multimedia is incompatible with enabled RPM Fusion repo(s) "
            f"{enabled_rpmfusion}"
        )

    conflicting_nvidia_repos = sorted(
        key
        for key in ("rpmfusion_nonfree", "rpmfusion_nonfree_nvidia_driver", "terra_nvidia")
        if toggles.get(key)
    )
    if toggles.get("negativo17_nvidia") and conflicting_nvidia_repos:
        errors.append(
            "negativo17_nvidia cannot be combined with another NVIDIA package source: "
            f"{conflicting_nvidia_repos}"
        )

    if toggles.get("terra_nvidia"):
        errors.append(
            "terra_nvidia is retained only to disable an existing legacy repo; "
            "use negativo17_nvidia instead"
        )

    if toggles.get("negativo17_nvidia") and toggles.get("negativo17_multimedia"):
        errors.append(
            "negativo17_multimedia already contains the NVIDIA packages; disable "
            "negativo17_nvidia when using the multimedia repository"
        )

    enabled_terra_subrepos = sorted(
        key for key, enabled in toggles.items() if key.startswith("terra_") and enabled
    )
    if enabled_terra_subrepos and not toggles.get("terra"):
        errors.append(f"Terra subrepo(s) require the base terra repo: {enabled_terra_subrepos}")

    if desktop_envs.get("hyprland") and not toggles.get("copr_hyprland"):
        errors.append("the Hyprland desktop requires the copr_hyprland repository")

    return errors


def repo_id(repo):
    """Return the primary dnf repo id for a REPOS entry."""
    if repo["kind"] == "copr":
        owner, project = repo["copr"].split("/", 1)
        return f"copr:{COPR_HOST}:{owner}:{project}"
    return repo["id"]


def repo_ids(repo):
    """Return every repo id a REPOS entry controls: the primary first, then siblings."""
    return [repo_id(repo), *repo.get("siblings", [])]


def _setopt(repo, enabled):
    """One `config-manager setopt` that flips every id the entry controls."""
    flag = 1 if enabled else 0
    settings = " ".join(f"{rid}.enabled={flag}" for rid in repo_ids(repo))
    return f"dnf config-manager setopt {settings}"


def repo_states():
    """Return {repo_id: "enabled" | "disabled"} for every repo dnf knows about.

    Exits when dnf cannot read its configuration. A parse failure means the repo
    list is unknown, not that every repo is absent, and callers respond to an
    absent repo by registering it — `addrepo` then fails on the existing file and
    the release RPMs are re-fetched for nothing.
    """
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
        # `repo id | repo name | status`; the name may contain spaces, so only the
        # first and last columns are trusted. The header row fails the status test.
        if len(fields) >= 2 and fields[-1] in ("enabled", "disabled"):
            states[fields[0]] = fields[-1]
    return states


def enable_commands(repo, registered):
    """Commands that make a repo enabled, given whether dnf already knows it.

    A freshly registered release RPM or repofile ships its repos enabled, so the
    registration alone is enough there; only an already-known repo needs setopt.
    """
    kind = repo["kind"]
    if kind == "copr":
        return [f"dnf copr enable -y {repo['copr']}"]
    if registered or kind == "builtin":
        return [_setopt(repo, enabled=True)]
    if kind == "rpm":
        return [f"dnf install -y {repo['install']}"]
    if kind == "repofile":
        return [f"dnf config-manager addrepo --from-repofile={repo['url']}"]
    if kind == "commands":
        return repo["install"]
    sys.exit(f"Unknown repo kind {kind!r} in packages/repos.py")


def disable_commands(repo):
    """Commands that disable a registered repo without removing it."""
    if repo["kind"] == "copr":
        return [f"dnf copr disable {repo['copr']}"]
    return [_setopt(repo, enabled=False)]
