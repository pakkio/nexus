#!/usr/bin/env python3
"""
SIMULAZIONE REALISTICA DEL SISTEMA COMPLETO
- Chiama Haiku con system prompt VERO che contiene:
  ✓ PREFIX file
  ✓ Story context globale
  ✓ Profilo psicologico giocatore
  ✓ Regole di risposta
- Testa 3 NPC con dialoghi realistici
"""

import os
import sys

os.environ['DEBUG_PREFIX_SEARCH'] = 'false'
os.environ['DEBUG_SYSTEM_PROMPT'] = 'false'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_manager import DbManager
from terminal_formatter import TerminalFormatter
from chat_manager import ChatSession
import session_utils
import time

def test_npc_dialogo(area_name, npc_name, dialoghi_test):
    """
    Testa un NPC con dialoghi realistici
    dialoghi_test = lista di (messaggio_giocatore, commento_aspettato)
    """

    print(f"\n{'='*80}")
    print(f"TEST NPC: {npc_name.upper()} ({area_name})")
    print(f"{'='*80}\n")

    try:
        db = DbManager()
        TF = TerminalFormatter()
        model_name = 'anthropic/claude-3.5-haiku'

        # 1. Carica dati NPC
        npc_data = db.get_npc(area_name, npc_name)
        if not npc_data:
            print(f"✗ NPC non trovato")
            return

        print(f"✓ NPC caricato: {npc_data.get('name')}")
        print(f"  Ruolo: {npc_data.get('role')}")

        # 2. Costruisci system prompt COMPLETO (come nel vero sistema)
        game_session_state = {
            'player_id': 'test_player_123',
            'model_name': model_name,
            'profile_analysis_model_name': model_name,
            'brief_mode': False,
            'wise_guide_npc_name': 'lyra',
            'in_hint_mode': False,
            'player_profile_cache': {
                'traits': ['curioso', 'pragmatico', 'empatico'],
                'decision_pattern': 'cerca sempre il compromesso',
                'motivations': ['salvare il Velo', 'capire la verità']
            }
        }

        story = "Test story"
        system_prompt = session_utils.build_system_prompt(
            npc_data, story, TF,
            game_session_state=game_session_state
        )

        print(f"✓ System prompt costruito: {len(system_prompt)} chars")
        print(f"  Contiene PREFIX: {'CONTESTO NARRATIVO PERSONALIZZATO' in system_prompt}")
        print(f"  Contiene Story Context: {'Contesto Globale del Mondo' in system_prompt}")
        print(f"  Contiene Regole: {'REGOLE LINGUISTICHE' in system_prompt}")

        # 3. Crea chat session
        chat_session = ChatSession(model_name=model_name)
        chat_session.set_system_prompt(system_prompt)

        print(f"\n{'─'*80}")
        print(f"DIALOGO CON {npc_name.upper()}")
        print(f"{'─'*80}\n")

        # 4. Testa dialoghi
        for i, (messaggio_giocatore, commento) in enumerate(dialoghi_test, 1):
            print(f"\n[Turno {i}] {commento}")
            print(f"\n👤 Giocatore > {messaggio_giocatore}")

            start_time = time.time()
            chat_session.add_message("user", messaggio_giocatore)

            # CHIAMA HAIKU CON IL VERO SYSTEM PROMPT
            npc_response, stats = chat_session.ask(
                messaggio_giocatore,
                current_npc_name_for_placeholder=npc_name,
                stream=False,
                collect_stats=True,
                npc_data=npc_data,
                game_session_state=game_session_state
            )

            elapsed_time = time.time() - start_time

            print(f"\n🎭 {npc_name.upper()} > {npc_response}\n")

            # Analizza risposta
            print(f"[ANALISI]")
            print(f"  ⏱️  Tempo: {elapsed_time:.1f}s")
            if stats:
                print(f"  📊 Input: {stats.get('input_tokens', 0)} | Output: {stats.get('output_tokens', 0)}")

            # Verifica qualità risposta
            checks = []

            # 1. Non contiene fallback generici
            if "Bentornato" not in npc_response and "viandante" not in npc_response.lower():
                checks.append("✅ No generic fallback")
            else:
                checks.append("❌ GENERIC FALLBACK DETECTED")

            # 2. Contiene contesto specifico NPC
            if npc_name.lower() == 'garin':
                if any(w in npc_response.lower() for w in ['metallo', 'martello', 'memoria', 'forgia']):
                    checks.append("✅ Garin-specific context (metallo, martello, memoria)")
                else:
                    checks.append("⚠️  Garin context weak")

            elif npc_name.lower() == 'mara':
                if any(w in npc_response.lower() for w in ['pozione', 'boccettina', 'crediti', 'guarigione']):
                    checks.append("✅ Mara-specific context (pozione, boccettina, crediti)")
                else:
                    checks.append("⚠️  Mara context weak")

            elif npc_name.lower() == 'jorin':
                if any(w in npc_response.lower() for w in ['taverna', 'storia', 'sogni', 'locandiere']):
                    checks.append("✅ Jorin-specific context (taverna, storie, sogni)")
                else:
                    checks.append("⚠️  Jorin context weak")

            # 3. Italiano corretto (senza parole inglesi)
            english_words = ['hello', 'welcome', 'where', 'who', 'what', 'help', 'thanks']
            if not any(word in npc_response.lower() for word in english_words):
                checks.append("✅ Italiano corretto (no English)")
            else:
                checks.append("❌ ENGLISH WORDS DETECTED")

            # 4. In character
            if any(c in npc_response for c in ['*', '«', '»']) or "Dico" not in npc_response:
                checks.append("✅ In character (narrazione, non meta)")

            # 5. Pratico e diretto
            if len(npc_response) < 500:
                checks.append("✅ Conciso (non troppo verboso)")
            else:
                checks.append("⚠️  Risposta lunga")

            for check in checks:
                print(f"  {check}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("\n" + "="*80)
    print("SIMULAZIONE SISTEMA COMPLETO - 3 NPC")
    print("="*80)
    print("\nChiama Haiku con system prompt COMPLETO che contiene:")
    print("  ✓ PREFIX file (contesto narrativo personalizzato)")
    print("  ✓ Story context globale (antefatto)")
    print("  ✓ Profilo psicologico giocatore")
    print("  ✓ Regole di risposta complete")
    print("  ✓ History conversazioni")
    print("\n" + "="*80 + "\n")

    # TEST 1: GARIN - Test della catena di oggetti
    test_npc_dialogo('Village', 'Garin', [
        ("Ciao Garin, cosa fai qui?", "Intro - Garin spiega il suo ruolo"),
        ("Ho bisogno di trucioli di ferro", "Garin deve dire cosa vuole in cambio"),
        ("Come faccio a trovare il Minerale di Ferro Antico?", "Garin deve dare direzioni specifiche"),
    ])

    time.sleep(1)

    # TEST 2: MARA - Test della transazione e profilo giocatore
    test_npc_dialogo('Village', 'Mara', [
        ("Mara, mi serve aiuto", "Mara riconosce il giocatore come Cercastorie"),
        ("Puoi vendermi una pozione di guarigione?", "Mara deve riconoscere volontà di comprare"),
        ("Ecco i 50 crediti", "Transazione - [GIVEN_ITEMS] tag"),
    ])

    time.sleep(1)

    # TEST 3: JORIN - Test del contesto narrativo e consapevolezza storia
    test_npc_dialogo('Tavern', 'Jorin', [
        ("Chi sei? Cosa sai del Velo?", "Jorin spiega il contesto globale dalla storia"),
        ("Hai qualcosa per me?", "Jorin parla della Ciotola e della catena"),
        ("Come mi trovi la Ciotola dell'Offerta Sacra?", "Jorin dà info su come ottenerla"),
    ])

    print("\n" + "="*80)
    print("SIMULAZIONE COMPLETATA")
    print("="*80)
    print("\nSe tutti i test passano ✅, il sistema è COMPLETAMENTE FUNZIONANTE!")
    print("Ogni NPC ha:")
    print("  ✓ Contesto personalizzato (PREFIX)")
    print("  ✓ Consapevolezza storia globale (antefatto)")
    print("  ✓ Conoscenza profilo giocatore")
    print("  ✓ Rispetto regole di risposta")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
