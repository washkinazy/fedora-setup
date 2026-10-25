"""User account: group membership and account full name (GECOS)."""

from pyinfra.context import host
from pyinfra.operations import server

user_config = host.data.get("user_config") or {}
user_groups = host.data.get("user_groups") or []
username = user_config.get("username", "")

# server.user rather than shelling out to usermod/chfn: it is fact-driven, so it
# emits usermod only when the groups are not already a subset and the comment
# actually differs. The shell version had no state check and so reported changed
# on every single run, forever.
#
# append=True is required — without it the secondary group list is replaced
# rather than added to. ensure_home=False because this deploy does not manage the
# home directory; left at its default the operation would also chown it to
# user:group, which would re-group the home if the primary group ever differed.
if username:
    server.user(
        name="Configure user account",
        user=username,
        groups=user_groups,
        append=True,
        comment=user_config.get("full_username") or None,
        ensure_home=False,
    )
