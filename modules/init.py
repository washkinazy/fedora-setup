"""Release identity — run before other modules."""

import shlex
import sys

from pyinfra.context import host
from pyinfra.facts.rpm import RpmPackages
from pyinfra.operations import dnf, server

BASIC_IDENTITY = "fedora-release-identity-basic"
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
