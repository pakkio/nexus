# consequence_system.py
from typing import Dict, Any, List
import random

def show_philosophical_consequences(state: Dict[str, Any], npc_name: str, player_response: str) -> None:
    """Show consequences of player's philosophical choices"""
    TF = state.get('TerminalFormatter')
    if not TF:
        return
        
    profile = state.get('player_profile_cache', {})
    philosophical_leaning = profile.get('philosophical_leaning', 'neutral')
    veil_perception = profile.get('veil_perception', 'neutral_curiosity')
    
    # Map NPCs to their philosophical alignments
    npc_alignments = {
        'Alto Giudice Theron': 'progressist',
        'Theron': 'progressist',
        'Lyra': 'conservator',
        'Boros': 'conservator',
        'Cassian': 'opportunist',
        'Garin': 'neutral_craftsman',
        'Mara': 'neutral_healer'
    }
    
    npc_alignment = npc_alignments.get(npc_name, 'neutral')
    
    # Check for philosophical alignment shifts
    if philosophical_leaning != 'neutral':
        alignment_messages = get_alignment_consequences(philosophical_leaning, npc_alignment, npc_name)
        if alignment_messages:
            print(f"{TF.CYAN}🔮 {random.choice(alignment_messages)}{TF.RESET}")
    
    # Check for specific trigger words that show consequences
    response_lower = player_response.lower()
    
    consequence_triggers = {
        'oblio': show_oblivion_consequences,
        'velo': show_veil_consequences,
        'darius': show_theron_brother_consequences,
        'memoria': show_memory_consequences,
        'sussurri': show_whispers_consequences
    }
    
    for trigger, consequence_func in consequence_triggers.items():
        if trigger in response_lower:
            consequence_func(state, npc_name, philosophical_leaning)
            break

def get_alignment_consequences(player_leaning: str, npc_alignment: str, npc_name: str) -> List[str]:
    """Get consequence messages based on philosophical alignment"""
    
    if player_leaning == 'progressist':
        if npc_alignment == 'progressist':
            return [
                f"{npc_name} sembra apprezzare la tua crescente comprensione dell'Oblio...",
                f"Un bagliore di approvazione negli occhi di {npc_name}...",
                f"{npc_name} annuisce, riconoscendo un compagno di viaggio filosofico..."
            ]
        elif npc_alignment == 'conservator':
            return [
                f"{npc_name} mostra una leggera tristezza per la tua scelta di percorso...",
                f"Percepisci una sottile tensione nel modo in cui {npc_name} ti guarda...",
                f"{npc_name} sembra preoccupato per la direzione del tuo viaggio spirituale..."
            ]
    
    elif player_leaning == 'conservator':
        if npc_alignment == 'conservator':
            return [
                f"{npc_name} sorride, vedendo in te un custode della memoria...",
                f"Un senso di solidarietà si diffonde tra voi due...",
                f"{npc_name} sembra sollevato dalla tua fedeltà al Velo..."
            ]
        elif npc_alignment == 'progressist':
            return [
                f"{npc_name} sospira, vedendo in te qualcuno ancora legato al passato...",
                f"Un'ombra di delusione attraversa il volto di {npc_name}...",
                f"{npc_name} scuote la testa, dispiaciuto per la tua resistenza al cambiamento..."
            ]
    
    return []

def show_oblivion_consequences(state: Dict[str, Any], npc_name: str, player_leaning: str) -> None:
    """Show consequences when player mentions oblivion"""
    TF = state.get('TerminalFormatter')
    
    messages = {
        'progressist': [
            "🌀 L'aria intorno a voi sembra vibrare di possibilità...",
            "🌀 Senti una strana liberazione nell'pronunciare quella parola...",
            "🌀 Il Velo stesso sembra sussurrare in risposta..."
        ],
        'conservator': [
            "🛡️ Un brivido di paura attraversa la tua spina dorsale...",
            "🛡️ Le parole sembrano pesare come pietre nella tua bocca...",
            "🛡️ Il Velo si stringe protettivamente intorno ai tuoi pensieri..."
        ],
        'neutral': [
            "⚖️ Senti il peso di scelte importanti davanti a te...",
            "⚖️ L'equilibrio del mondo sembra tremare leggermente...",
            "⚖️ Una tensione sottile si diffonde nell'aria..."
        ]
    }
    
    message_list = messages.get(player_leaning, messages['neutral'])
    print(f"{TF.DIM}{random.choice(message_list)}{TF.RESET}")

def show_veil_consequences(state: Dict[str, Any], npc_name: str, player_leaning: str) -> None:
    """Show consequences when player mentions the veil"""
    TF = state.get('TerminalFormatter')
    
    messages = {
        'conservator': [
            "✨ Una sensazione di calore e protezione ti avvolge...",
            "✨ Il mondo sembra più stabile e sicuro intorno a voi...",
            "✨ Senti la presenza rassicurante della memoria antica..."
        ],
        'progressist': [
            "⛓️ Le parole sembrano pesanti, come catene invisibili...",
            "⛓️ Una sensazione di claustrofobia ti attraversa brevemente...",
            "⛓️ Il peso del passato grava sulle tue spalle..."
        ]
    }
    
    if player_leaning in messages:
        print(f"{TF.DIM}{random.choice(messages[player_leaning])}{TF.RESET}")

def show_theron_brother_consequences(state: Dict[str, Any], npc_name: str, player_leaning: str) -> None:
    """Show consequences when Theron's brother is mentioned"""
    TF = state.get('TerminalFormatter')
    
    if npc_name in ['Theron', 'Alto Giudice Theron']:
        messages = [
            "💔 Un'onda di dolore profondo attraversa gli occhi di Theron...",
            "💔 Le mani di Theron tremano leggermente al ricordo...",
            "💔 La voce di Theron si incrina quasi impercettibilmente..."
        ]
        print(f"{TF.DIM}{random.choice(messages)}{TF.RESET}")
    else:
        # Other NPCs react to hearing about this tragedy
        messages = [
            f"😔 {npc_name} abbassa lo sguardo con rispetto per il dolore di Theron...",
            f"😔 Un momento di silenzio in memoria di una vita perduta...",
            f"😔 {npc_name} sembra comprendere il peso di quella perdita..."
        ]
        print(f"{TF.DIM}{random.choice(messages)}{TF.RESET}")

def show_memory_consequences(state: Dict[str, Any], npc_name: str, player_leaning: str) -> None:
    """Show consequences when memory is discussed"""
    TF = state.get('TerminalFormatter')
    
    profile = state.get('player_profile_cache', {})
    recent_experiences = profile.get('key_experiences_tags', [])
    
    if 'memory_corruption' in recent_experiences or 'sussurri_exposure' in recent_experiences:
        print(f"{TF.DIM}🌫️ I tuoi stessi ricordi sembrano incerti mentre parli...{TF.RESET}")
    else:
        memories_msg = [
            "💭 I ricordi danzano ai margini della tua coscienza...",
            "💭 Senti il peso di tutto ciò che hai dimenticato...",
            "💭 La memoria è come sabbia tra le dita..."
        ]
        print(f"{TF.DIM}{random.choice(memories_msg)}{TF.RESET}")

def show_whispers_consequences(state: Dict[str, Any], npc_name: str, player_leaning: str) -> None:
    """Show consequences when whispers are mentioned"""
    TF = state.get('TerminalFormatter')
    
    # Check if player has sussurri resistance
    veil_perception = state.get('player_profile_cache', {}).get('veil_perception', 'neutral')
    
    if player_leaning == 'progressist':
        print(f"{TF.DIM}🌀 I Sussurri sembrano... familiari... quasi invitanti...{TF.RESET}")
    elif veil_perception in ['protective_trust', 'neutral_curiosity']:
        print(f"{TF.DIM}🛡️ Senti il Velo rafforzarsi intorno alla tua mente...{TF.RESET}")
    else:
        print(f"{TF.DIM}👻 Un brivido gelido corre lungo la tua schiena...{TF.RESET}")

def track_relationship_changes(state: Dict[str, Any], npc_name: str, interaction_result: str) -> None:
    """Track and show relationship changes with NPCs based on philosophical alignment"""
    TF = state.get('TerminalFormatter')
    profile = state.get('player_profile_cache', {})
    
    # Initialize relationship tracking if not present
    if 'npc_relationships' not in profile:
        profile['npc_relationships'] = {}
    
    current_relationship = profile['npc_relationships'].get(npc_name, 0)
    philosophical_leaning = profile.get('philosophical_leaning', 'neutral')
    
    # Calculate relationship change based on philosophical alignment
    npc_alignments = {
        'Alto Giudice Theron': 'progressist',
        'Theron': 'progressist',
        'Lyra': 'conservator',
        'Boros': 'conservator',
        'Cassian': 'opportunist'
    }
    
    npc_alignment = npc_alignments.get(npc_name, 'neutral')
    relationship_delta = 0
    
    if philosophical_leaning == npc_alignment and philosophical_leaning != 'neutral':
        relationship_delta = 1
        relationship_msg = f"💚 {npc_name} sembra più aperto verso di te..."
    elif philosophical_leaning != 'neutral' and npc_alignment != 'neutral' and philosophical_leaning != npc_alignment:
        relationship_delta = -1
        relationship_msg = f"💔 Una sottile distanza si crea tra te e {npc_name}..."
    else:
        return  # No change
    
    # Update and show relationship change
    new_relationship = max(-5, min(5, current_relationship + relationship_delta))
    if new_relationship != current_relationship:
        profile['npc_relationships'][npc_name] = new_relationship
        state['player_profile_cache'] = profile
        print(f"{TF.CYAN}{relationship_msg}{TF.RESET}")
        
        # Show major relationship milestones
        if abs(new_relationship) >= 3:
            if new_relationship >= 3:
                print(f"{TF.GREEN}✨ {npc_name} ti considera un alleato fidato{TF.RESET}")
            elif new_relationship <= -3:
                print(f"{TF.RED}⚡ {npc_name} guarda con sospetto le tue scelte{TF.RESET}")