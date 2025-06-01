# command_handlers/__init__.py
from .handle_exit import handle_exit
from .handle_help import handle_help
from .handle_go import handle_go
from .handle_talk import handle_talk
from .handle_who import handle_who
from .handle_whereami import handle_whereami
from .handle_npcs import handle_npcs
from .handle_areas import handle_areas
from .handle_listareas import handle_listareas
from .handle_stats import handle_stats
from .handle_session_stats import handle_session_stats
from .handle_clear import handle_clear
from .handle_hint import handle_hint # MODIFIED: Ensure these are present
from .handle_endhint import handle_endhint # MODIFIED: Ensure these are present
from .handle_inventory import handle_inventory
from .handle_give import handle_give
from .handle_receive import handle_receive
from .handle_profile import handle_profile
from .heandle_profile_for_npc import handle_profile_for_npc # Typo in original, kept for consistency if it exists
from .handle_history import handle_history

__all__ = [
    "handle_exit", "handle_help", "handle_go", "handle_talk", "handle_who",
    "handle_whereami", "handle_npcs", "handle_areas", "handle_listareas",
    "handle_stats", "handle_session_stats", "handle_clear", "handle_hint", "handle_endhint",
    "handle_inventory", "handle_give", "handle_receive", "handle_profile",
    "handle_profile_for_npc", "handle_history"
]