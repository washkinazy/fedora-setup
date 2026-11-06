"""User account: group membership and account full name (GECOS)."""

from pyinfra.context import host
from pyinfra.operations import server

user_config = host.data.get("user_config") or {}
user_groups = host.data.get("user_groups") or []
username = user_config.get("username", "")

# Preserve supplementary groups and existing home-directory ownership.
if username:
    server.user(
        name="Configure user account",
        user=username,
        groups=user_groups,
        append=True,
        comment=user_config.get("full_username") or None,
        ensure_home=False,
    )
