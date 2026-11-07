"""Hardware-specific configuration: GPU drivers, peripheral fixes."""

import subprocess
import sys

from pyinfra.operations import files

from packages.packages import NVIDIA, NVIDIA_BUILD_PACKAGES
from packages.repos import install_packages

GPU_CLASSES = ("VGA compatible controller", "3D controller", "Display controller")


def _gpu_vendors():
    """Return the set of GPU vendors present on the PCI bus."""
    result = subprocess.run(["lspci"], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        sys.exit("lspci failed — cannot detect GPUs (is pciutils installed?)")

    vendors = set()
    for line in result.stdout.splitlines():
        if not any(gpu_class in line for gpu_class in GPU_CLASSES):
            continue
        lowered = line.lower()
        if "nvidia" in lowered:
            vendors.add("nvidia")
        if "amd" in lowered or "ati " in lowered or "advanced micro devices" in lowered:
            vendors.add("amd")
        if "intel" in lowered:
            vendors.add("intel")
    return vendors


files.directory(
    name="Create systemd sleep hooks directory",
    path="/usr/lib/systemd/system-sleep",
    user="root",
    group="root",
    mode="0755",
)

# --- GPU drivers ---

gpu_vendors = _gpu_vendors()

if "nvidia" in gpu_vendors:
    install_packages(
        name="Install NVIDIA kernel build prerequisites",
        packages=NVIDIA_BUILD_PACKAGES,
    )

    install_packages(
        name="Install RPM Fusion NVIDIA driver and open kernel module",
        packages=NVIDIA,
    )

# --- Logitech mouse resume fix ---

files.put(
    name="Deploy Logitech mouse resume fix",
    src="files/rebind-logitech-mouse.sh",
    dest="/usr/lib/systemd/system-sleep/rebind-logitech-mouse.sh",
    user="root",
    group="root",
    mode="0755",
)
