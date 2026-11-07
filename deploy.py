"""Main deploy: Fedora system setup."""

import sys

from pyinfra.context import host
from pyinfra.facts.server import LinuxDistribution
from pyinfra.local import include
from pyinfra.operations import server

os_info = host.get_fact(LinuxDistribution)
if os_info.get("release_meta", {}).get("ID") != "fedora":
    sys.exit("This deploy only supports Fedora")

hostname = host.data.get("hostname")
if not hostname:
    sys.exit("hostname must be defined in host data")

include("modules/repo_policy.py")

server.hostname(
    name="Set system hostname",
    hostname=hostname,
)

include("modules/init.py")

include("modules/system.py")

include("modules/hardware.py")

include("modules/storage.py")

include("modules/packages.py")

include("modules/user_account.py")
