"""Generic Fedora release and identity — run before other modules."""

import shlex
import sys

from pyinfra.context import host
from pyinfra.facts.rpm import RpmPackages
from pyinfra.facts.server import Command
from pyinfra.operations import dnf, server

BASIC_IDENTITY = "fedora-release-identity-basic"
release_packages = host.get_fact(
    Command, command="rpm -q --whatprovides system-release --qf '%{NAME}\\n'"
).splitlines()
if len(release_packages) != 1:
    sys.exit(f"Expected one system-release provider, found: {release_packages}")

identities = sorted(
    package
    for package in host.get_fact(RpmPackages)
    if package.startswith("fedora-release-identity-")
)
if len(identities) > 1:
    sys.exit(f"Expected one Fedora release identity, found: {identities}")

if identities and identities[0] != BASIC_IDENTITY:
    server.shell(
        name="Switch Fedora release identity to basic",
        commands=[f"dnf swap -y {shlex.quote(identities[0])} {BASIC_IDENTITY}"],
    )
elif not identities:
    dnf.packages(
        name="Install Fedora basic release identity",
        packages=[BASIC_IDENTITY],
    )

if release_packages[0] != "fedora-release":
    server.shell(
        name="Switch to generic Fedora release",
        commands=[f"dnf swap -y {shlex.quote(release_packages[0])} fedora-release"],
    )
