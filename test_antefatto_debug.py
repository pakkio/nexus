#!/usr/bin/env python3
"""Debug script to see the full prompt"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from session_utils import build_system_prompt
from terminal_formatter import TerminalFormatter

try:
    with open('ilpercorsodelcercastorie', 'r', encoding='utf-8') as f:
        full_story = f.read()
except FileNotFoundError:
    print("❌ ilpercorsodelcercastorie file not found!")
    sys.exit(1)

mock_npc = {
    'name': 'Syra',
    'role': 'Custode delle Rovine',
    'area': 'Ancient Ruins',
    'motivation': 'Completare la propria trasformazione nel Velo',
    'goal': 'Ricevere la Ciotola Sacra',
    'playerhint': 'Portami la Ciotola Sacra e ti aiuterò',
    'dialogue_hooks': 'Senti il peso del silenzio? È il peso delle parole mai dette.',
    'veil_connection': 'Custodisce il Cristallo di Memoria Antica',
    'default_greeting': 'Benvenuto nelle Rovine Antiche, Cercastorie.',
}

mock_game_state = {
    'player_id': 'test_player',
    'player_profile_cache': {},
    'profile_analysis_model_name': 'mistralai/mistral-7b-instruct:free',
    'model_name': 'google/gemma-2-9b-it:free',
    'wise_guide_npc_name': None,
    'brief_mode': False,
    'db': None,
    'last_npc_conversation_history': [
        {"role": "user", "content": "Ciao Erasmus"},
        {"role": "assistant", "content": "Benvenuto al Vuoto Liminale, Cercastorie."},
    ],
    'last_npc_name': 'Erasmus',
}

prompt = build_system_prompt(
    npc=mock_npc,
    story=full_story,
    TF=TerminalFormatter,
    game_session_state=mock_game_state,
    llm_wrapper_func_for_distill=None
)

print("FULL PROMPT:")
print("="*80)
print(prompt)
print("="*80)
print(f"\nTotal size: {len(prompt)} chars")
print(f"\nSearching for key strings:")
print(f"  'Il Cercastorie': {('Il Cercastorie' in prompt)}")
print(f"  'Sei Syra': {('Sei Syra' in prompt)}")
print(f"  'CONTESTO NARRATIVO CONDENSATO': {('CONTESTO NARRATIVO CONDENSATO' in prompt)}")
print(f"  'Erasmus': {('Erasmus' in prompt)}")
print(f"  'LINGUA OBBLIGATORIA': {('LINGUA OBBLIGATORIA' in prompt)}")
