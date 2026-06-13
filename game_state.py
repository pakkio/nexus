from dataclasses import dataclass, field, fields
import dataclasses
from typing import Any, Callable, Dict, List, Optional


@dataclass
class GameState:
    db: Any = None
    story: str = ""
    current_area: Optional[str] = None
    current_npc: Optional[Dict[str, Any]] = None
    chat_session: Any = None
    model_name: str = ""
    profile_analysis_model_name: str = ""
    use_stream: bool = False
    auto_show_stats: bool = False
    debug_mode: bool = False
    player_id: str = ""
    player_inventory: List[str] = field(default_factory=list)
    player_credits_cache: int = 0
    player_profile_cache: Dict[str, Any] = field(default_factory=dict)
    ChatSession: Any = None
    TerminalFormatter: Any = None
    format_stats: Callable = field(default_factory=lambda: lambda *a, **kw: "")
    llm_wrapper_func: Callable = field(default_factory=lambda: lambda *a, **kw: "")
    npc_made_new_response_this_turn: bool = False
    actions_this_turn_for_profile: List[str] = field(default_factory=list)
    in_hint_mode: bool = False
    stashed_chat_session: Any = None
    stashed_npc: Optional[Dict[str, Any]] = None
    hint_cache: Dict[str, Any] = field(default_factory=dict)
    wise_guide_npc_name: Optional[str] = None
    nlp_command_interpretation_enabled: bool = False
    nlp_command_confidence_threshold: float = 0.7
    nlp_command_debug: bool = False
    mappa_personaggi_luoghi: str = ""
    percorso_narratore_tappe: str = ""
    percorso_narratore_condensed: str = ""
    system_messages_buffer: List[str] = field(default_factory=list)
    game_system_instance: Any = None
    item_given_to_npc_this_turn: Dict[str, Any] = field(default_factory=dict)
    notecard_extracted: Dict[str, Any] = field(default_factory=dict)
    plot_flags: Dict[str, Any] = field(default_factory=dict)
    player_info: Dict[str, Any] = field(default_factory=dict)
    continue_loop: bool = True
    status: str = "ok"
    in_lyra_hint_mode: bool = False
    system_message_for_ui: str = ""
    distilled_insights_cache: Dict[str, Any] = field(default_factory=dict)
    last_npc_conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    last_npc_name: str = ""
    teleport_offered_this_turn: bool = False
    teleport_target_npc: Optional[str] = None

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def pop(self, key: str, default: Any = None) -> Any:
        if not hasattr(self, key):
            return default
        value = getattr(self, key)
        # Reset field to its dataclass default
        for f in fields(self):
            if f.name == key:
                if f.default_factory is not None and f.default_factory is not dataclasses.MISSING:
                    setattr(self, key, f.default_factory())
                elif f.default is not dataclasses.MISSING:
                    setattr(self, key, f.default)
                else:
                    setattr(self, key, None)
                break
        else:
            setattr(self, key, None)
        return value

    def __iter__(self):
        for field_info in self.__dataclass_fields__:
            yield field_info

    def keys(self):
        return self.__dataclass_fields__.keys()

    def __contains__(self, key: str) -> bool:
        return key in self.__dataclass_fields__ or hasattr(self, key)