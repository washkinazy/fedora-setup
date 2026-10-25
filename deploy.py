"""Main deploy: Fedora system setup."""

import sys

from pyinfra.context import host
from pyinfra.facts.server import LinuxDistribution
from pyinfra.local import include
from pyinfra.operations import server

from packages.repos import validate_repo_configuration

# Reject invalid combinations before any operation is queued or applied.
configuration_errors = validate_repo_configuration(
    host.data.get("repos") or {},
    host.data.get("desktop_environments") or {},
)
if configuration_errors:
    sys.exit("Invalid inventory.py configuration:\n- " + "\n- ".join(configuration_errors))

# Validate Fedora. `name` is the pretty name ("Fedora Linux"); the os-release
# ID is the stable identifier, so match on that.
os_info = host.get_fact(LinuxDistribution)
if os_info.get("release_meta", {}).get("ID") != "fedora":
    sys.exit("This deploy only supports Fedora")

hostname = host.data.get("hostname")
if not hostname:
    sys.exit("hostname must be defined in host data")

# Set hostname
server.hostname(
    name="Set system hostname",
    hostname=hostname,
)

# Kernel build prerequisites (needed by NVIDIA akmods, DKMS modules)
include("modules/init.py")

# System-level configuration (dnf.conf, sysctl, zram)
include("modules/system.py")

# Third-party repos — must precede every module that installs packages, since
# the NAME_<REPO> halves of the package lists resolve from them
include("modules/repos.py")

# Hardware-specific (NVIDIA, peripheral fixes — gated internally)
include("modules/hardware.py")

# Storage mounts (Synology NAS, local disks — gated internally)
include("modules/storage.py")

# Packages (base, desktop, Tailscale, development, gaming — gated internally)
include("modules/packages.py")

# User account configuration (group membership, account full name)
include("modules/user_account.py")
