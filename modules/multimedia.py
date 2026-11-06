"""Native multimedia codecs."""

from pyinfra.context import host
from pyinfra.facts.rpm import RpmPackages
from pyinfra.operations import server

from packages.packages import MULTIMEDIA
from packages.repos import ensure_package_repositories, install_packages

ensure_package_repositories(MULTIMEDIA)
installed = host.get_fact(RpmPackages)

if "ffmpeg-free" in installed:
    server.shell(
        name="Replace Fedora FFmpeg with full FFmpeg",
        commands=["dnf swap -y ffmpeg-free ffmpeg --allowerasing"],
    )
elif "ffmpeg" not in installed:
    install_packages(
        name="Install full FFmpeg",
        packages=["ffmpeg"],
        extra_install_args="--allowerasing",
    )

install_packages(
    name="Install multimedia codecs",
    packages=[package for package in MULTIMEDIA if package != "ffmpeg"],
)
