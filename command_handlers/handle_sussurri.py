# command_handlers/handle_sussurri.py
from typing import Dict, Any
from command_handler_utils import HandlerResult, _add_profile_action
import time
import random

def handle_sussurri(args_str: str, state: Dict[str, Any]) -> HandlerResult:
    """
    Debug command to show/trigger Sussurri (Whispers) decay effects.
    Usage: /sussurri [check|trigger]
    """
    TF = state['TerminalFormatter']
    db = state['db']
    player_id = state['player_id']
    
    args = args_str.strip().lower()
    
    if not args or args == "check":
        # Show current decay status
        print(f"\n{TF.BRIGHT_MAGENTA}{TF.BOLD}--- Sussurri dell'Oblio Status ---{TF.RESET}")
        
        # Check conversation decay
        chat_session = state.get('chat_session')
        if chat_session and hasattr(chat_session, 'messages'):
            current_time = time.time()
            decay_threshold = 300  # 5 minutes
            
            oldest_message_time = None
            for msg in chat_session.messages:
                if hasattr(msg, 'timestamp') and msg.timestamp:
                    if oldest_message_time is None or msg.timestamp < oldest_message_time:
                        oldest_message_time = msg.timestamp
            
            if oldest_message_time:
                age = current_time - oldest_message_time
                decay_level = min(100, int((age / decay_threshold) * 100))
                
                print(f"{TF.MAGENTA}Current Conversation:{TF.RESET}")
                print(f"  Age: {int(age/60)}m {int(age%60)}s")
                print(f"  Decay Level: {decay_level}%")
                
                if decay_level > 80:
                    print(f"  {TF.RED}⚠️ Severe memory corruption detected{TF.RESET}")
                elif decay_level > 50:
                    print(f"  {TF.YELLOW}⚠️ Moderate whispers interference{TF.RESET}")
                elif decay_level > 20:
                    print(f"  {TF.DIM}Minor whispers detected{TF.RESET}")
                else:
                    print(f"  {TF.GREEN}Memory intact{TF.RESET}")
        else:
            print(f"{TF.DIM}No active conversation to analyze{TF.RESET}")
            
        # Show player resistance based on profile
        profile = state.get('player_profile_cache', {})
        veil_perception = profile.get('veil_perception', 'neutral')
        philosophical_leaning = profile.get('philosophical_leaning', 'neutral')
        
        print(f"\n{TF.MAGENTA}Your Resistance:{TF.RESET}")
        resistance = calculate_sussurri_resistance(veil_perception, philosophical_leaning)
        print(f"  Base Resistance: {resistance}%")
        print(f"  Veil Perception: {veil_perception.replace('_', ' ').title()}")
        print(f"  Philosophy: {philosophical_leaning.title()}")
        
    elif args == "trigger":
        # Manually trigger decay effect for testing
        if not state.get('chat_session'):
            print(f"{TF.YELLOW}No active conversation to affect{TF.RESET}")
        else:
            print(f"{TF.MAGENTA}🌀 I Sussurri dell'Oblio si intensificano...{TF.RESET}")
            
            # Apply memory corruption effect
            corruption_messages = [
                "Le parole iniziano a sfumarsi nella tua mente...",
                "Chi stavi parlando? Il nome sembra sfuggirti...",
                "I dettagli della conversazione diventano nebulosi...",
                "Un'eco distante sussurra: 'Dimentica... è più facile...'"
            ]
            
            print(f"{TF.DIM}{random.choice(corruption_messages)}{TF.RESET}")
            
            # Mark conversation as corrupted
            state['sussurri_corruption_applied'] = True
            _add_profile_action(state, "Experienced Sussurri memory corruption")
    else:
        print(f"{TF.YELLOW}Usage: /sussurri [check|trigger]{TF.RESET}")
        
    return {**state, 'status': 'ok', 'continue_loop': True}

def calculate_sussurri_resistance(veil_perception: str, philosophical_leaning: str) -> int:
    """Calculate player's resistance to Sussurri based on their beliefs"""
    base_resistance = 50
    
    # Veil perception affects resistance
    veil_bonuses = {
        'protective_trust': 20,
        'neutral_curiosity': 0,
        'growing_doubt': -10,
        'active_skepticism': -20
    }
    
    # Philosophical leaning affects resistance
    philosophy_bonuses = {
        'conservator': 25,  # Pro-Veil = strong resistance
        'neutral': 0,
        'progressist': -25  # Pro-Oblivion = weak resistance
    }
    
    resistance = base_resistance
    resistance += veil_bonuses.get(veil_perception, 0)
    resistance += philosophy_bonuses.get(philosophical_leaning, 0)
    
    return max(0, min(100, resistance))

def apply_sussurri_decay(state: Dict[str, Any]) -> Dict[str, Any]:
    """Apply Sussurri decay effects to ongoing conversations"""
    chat_session = state.get('chat_session')
    if not chat_session or not hasattr(chat_session, 'messages'):
        return state
        
    current_time = time.time()
    decay_threshold = 300  # 5 minutes
    
    # Calculate conversation age
    oldest_message_time = None
    for msg in chat_session.messages:
        if hasattr(msg, 'timestamp') and msg.timestamp:
            if oldest_message_time is None or msg.timestamp < oldest_message_time:
                oldest_message_time = msg.timestamp
    
    if not oldest_message_time:
        return state
        
    age = current_time - oldest_message_time
    if age < 120:  # Less than 2 minutes, no decay
        return state
        
    # Calculate decay level
    decay_level = min(100, int((age / decay_threshold) * 100))
    
    # Get player resistance
    profile = state.get('player_profile_cache', {})
    veil_perception = profile.get('veil_perception', 'neutral')
    philosophical_leaning = profile.get('philosophical_leaning', 'neutral')
    resistance = calculate_sussurri_resistance(veil_perception, philosophical_leaning)
    
    # Apply resistance
    effective_decay = max(0, decay_level - resistance)
    
    if effective_decay > 70 and not state.get('sussurri_corruption_applied'):
        TF = state.get('TerminalFormatter')
        corruption_messages = [
            f"{TF.DIM}🌀 I Sussurri dell'Oblio distorcono i tuoi ricordi di questa conversazione...{TF.RESET}",
            f"{TF.DIM}🌀 Le parole si dissolvono nella nebbia della dimenticanza...{TF.RESET}",
            f"{TF.DIM}🌀 Un eco lontano: 'Lascia andare... è più facile dimenticare...'{TF.RESET}"
        ]
        print(random.choice(corruption_messages))
        state['sussurri_corruption_applied'] = True
        
        # Add to profile
        _add_profile_action(state, "Memory corrupted by Sussurri dell'Oblio")
        
    return state