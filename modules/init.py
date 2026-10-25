"""Kernel build prerequisites — must run before all other modules."""

from pyinfra.operations import dnf

dnf.packages(
    name="Install kernel build prerequisites",
    packages=[
        "kernel-devel-matched",
        "dkms",
    ],
)
