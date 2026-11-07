"""Apply package source policy before any package transactions."""

from io import StringIO

from pyinfra.operations import files

from packages.repo_policy import POLICY_PATH, render_policy

files.directory(
    name="Create DNF repository override directory",
    path="/etc/dnf/repos.override.d",
    user="root",
    group="root",
    mode="0755",
)

files.put(
    name="Configure package bindings and repository priorities",
    src=StringIO(render_policy()),
    dest=POLICY_PATH,
    user="root",
    group="root",
    mode="0644",
)
