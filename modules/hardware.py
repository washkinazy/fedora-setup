"""Hardware-specific configuration: GPU drivers, peripheral fixes."""

import subprocess
import sys

from pyinfra.context import host
from pyinfra.operations import dnf, files, systemd

from packages.packages import NVIDIA

repos = host.data.get("repos") or {}

# lspci device classes that identify a graphics adapter.
GPU_CLASSES = ("VGA compatible controller", "3D controller", "Display controller")

# Repo toggles the NVIDIA driver resolves from; see NVIDIA in packages/packages.py.
NVIDIA_REPOS = ("negativo17_nvidia",)


def _gpu_vendors():
    """Return the set of GPU vendors present on the PCI bus.

    Only display-class devices are considered, so an audio or bridge device from
    the same vendor cannot pull in a graphics driver. `lspci` comes from
    pciutils, which @core pulls in, so a missing binary means something is wrong
    with the system rather than an absent GPU — fail loudly instead of silently
    installing no driver at all.
    """
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


# Ensure the systemd sleep-hook directory exists before any hook is deployed.
# (Scripts here are run by systemd-sleep(8); they are not units, so no
# daemon-reload is needed after deploying them.)
files.directory(
    name="Create systemd sleep hooks directory",
    path="/usr/lib/systemd/system-sleep",
    user="root",
    group="root",
    mode="0755",
)

# --- GPU drivers ---
# Only NVIDIA needs a package here: amdgpu and i915/xe are in-tree, Mesa comes
# with @base-graphical and the firmware is in PACKAGES. A machine with no NVIDIA
# card installs nothing from this section.

gpu_vendors = _gpu_vendors()

if "nvidia" in gpu_vendors:
    # The driver comes from Negativo17's standalone NVIDIA repository.
    # This checks the toggles rather than live dnf state: modules/repos.py
    # registers whatever is toggled on earlier in this same run, so live state
    # is stale on a first deploy, while a toggle that is off means nothing will
    # ever provide the packages — stop before dnf fails halfway through.
    missing = [key for key in NVIDIA_REPOS if not repos.get(key)]
    if missing:
        sys.exit(
            f"NVIDIA GPU detected but repo toggle(s) {missing} are off in inventory.py;"
            " the driver resolves from negativo17_nvidia (see NVIDIA in packages/packages.py)"
        )

    dnf.packages(
        name="Install NVIDIA open driver (Negativo17 akmods)",
        packages=NVIDIA,
    )

    # Keeps the driver resident when no client has the device open, which avoids
    # repeated re-initialisation. Unit ships with the nvidia-persistenced package.
    # Enable only (`running=None`): starting it fails until the freshly built
    # akmod is actually loaded, which happens on the next boot.
    systemd.service(
        name="Enable NVIDIA persistence daemon",
        service="nvidia-persistenced",
        running=None,
        enabled=True,
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
