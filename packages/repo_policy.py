"""Persistent DNF5 package bindings and repository priorities."""

from packages.repos import REPOS, repo_ids

POLICY_PATH = "/etc/dnf/repos.override.d/99-zz-fedora-setup.repo"

PACKAGE_BINDINGS = {
    "steam": "rpmfusion_nonfree_steam",
    "codium": "vscodium",
}

# Lower values are preferred; release and update repositories share a priority.
REPOSITORY_PRIORITIES = {
    "*": 99,
    "fedora": 10,
    "fedora-debuginfo": 10,
    "fedora-source": 10,
    "updates*": 10,
    "rpmfusion-*": 20,
    "fedora-cisco-openh264": 20,
    "librewolf": 30,
    "gitlab.com_paulcarroty_vscodium_repo": 30,
    "copr:copr.fedorainfracloud.org:lionheartp:Hyprland*": 40,
    "terra*": 50,
}


def other_repository_patterns(allowed, prefix=""):
    """Match every repository ID except the explicitly allowed IDs."""
    if prefix and prefix not in allowed:
        yield prefix
    suffixes = [rid[len(prefix) :] for rid in allowed if rid.startswith(prefix)]
    next_chars = sorted({suffix[0] for suffix in suffixes if suffix})
    if not next_chars:
        yield prefix + "?*"
        return
    # Put '-' first so it is literal inside the glob character class.
    chars = "".join(sorted(next_chars, key=lambda char: (char != "-", char)))
    yield prefix + "[!" + chars + "]*"
    for char in next_chars:
        yield from other_repository_patterns(allowed, prefix + char)


def render_policy():
    from packages.packages import PACKAGE_REPOSITORIES

    sections = {rid: {"priority": str(value)} for rid, value in REPOSITORY_PRIORITIES.items()}
    for package, source in sorted(PACKAGE_BINDINGS.items()):
        if PACKAGE_REPOSITORIES.get(package) != source:
            raise ValueError(f"Binding for {package} disagrees with its required repository")
        for pattern in other_repository_patterns(repo_ids(REPOS[source])):
            options = sections.setdefault(pattern, {})
            options["excludepkgs"] = ",".join(filter(None, (options.get("excludepkgs"), package)))

    return "# Managed by fedora-setup: packages/repo_policy.py\n\n" + "\n".join(
        f"[{rid}]\n" + "".join(f"{key}={value}\n" for key, value in options.items())
        for rid, options in sections.items()
    )


if __name__ == "__main__":
    print(render_policy(), end="")
