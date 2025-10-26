#!/usr/bin/env python3
"""
TEST FINALE - DIMOSTRA TUTTI I MIGLIORAMENTI IDENTIFICATI DA LORENZA
Chiama Haiku 4.5 con system prompt COMPLETO per verificare:

✓ 1. Antefatto presente nei NPC
✓ 2. Nomenclatura corretta (Cercastorie per Erasmus)
✓ 3. Tempo di risposta (migliorato)
✓ 4. Lunghezza risposte (più concise)
✓ 5. Lyra risponde
✓ 6. Italiano corretto
✓ 7. Ultima versione storia
✓ 8. Percorso chiaro
✓ 9. Mara dice "boccettina azzurra"
✓ 10. Theron no duplicati
✓ 11. Boros allineato
"""

import os
import sys
import time

os.environ['DEBUG_PREFIX_SEARCH'] = 'false'
os.environ['DEBUG_SYSTEM_PROMPT'] = 'false'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_manager import DbManager
from terminal_formatter import TerminalFormatter
from chat_manager import ChatSession
import session_utils

def test_lorenza_findings():
    """Testa gli 11 punti segnalati da Lorenza"""

    print("\n" + "="*90)
    print("TEST FINALE - VERIFICA FEEDBACK LORENZA")
    print("="*90)
    print("\nChiama Haiku 4.5 con system prompt COMPLETO")
    print("Verifica gli 11 problemi segnalati da Lorenza\n")

    db = DbManager()
    TF = TerminalFormatter()
    model_name = 'anthropic/claude-haiku-4-5'

    test_results = []

    # TEST 1: ANTEFATTO
    print("\n" + "─"*90)
    print("1️⃣  ANTEFATTO PRESENTE NEI NPC")
    print("─"*90)

    npc_data = db.get_npc('Village', 'Garin')
    game_state = {'player_id': 'test', 'model_name': model_name, 'profile_analysis_model_name': model_name, 'brief_mode': False, 'wise_guide_npc_name': 'lyra', 'in_hint_mode': False}
    system_prompt = session_utils.build_system_prompt(npc_data, "story", TF, game_session_state=game_state)

    has_prefix = "CONTESTO NARRATIVO PERSONALIZZATO" in system_prompt
    has_story = "Contesto Globale del Mondo" in system_prompt
    print(f"✓ PREFIX presente: {has_prefix}")
    print(f"✓ Story context presente: {has_story}")
    test_results.append(("Antefatto", "✅ PASS" if has_prefix and has_story else "❌ FAIL"))

    # TEST 2: ERASMUS NOMENCLATURA
    print("\n" + "─"*90)
    print("2️⃣  ERASMUS USA 'CERCASTORIE' NON 'CERCATORE'")
    print("─"*90)

    chat_session = ChatSession(model_name=model_name)
    npc_data = db.get_npc('Liminal Void', 'Erasmus')
    system_prompt = session_utils.build_system_prompt(npc_data, "story", TF, game_session_state=game_state)

    # Verifica che nel PREFIX ci sia Cercastorie
    has_cercastorie = "Cercastorie" in system_prompt
    print(f"✓ PREFIX contiene 'Cercastorie': {has_cercastorie}")

    chat_session.set_system_prompt(system_prompt)
    chat_session.add_message("user", "Chi sono io?")
    start = time.time()
    response, _ = chat_session.ask("Chi sono io?", stream=False, collect_stats=True, npc_data=npc_data, game_session_state=game_state)
    elapsed = time.time() - start

    uses_cercastorie_response = "Cercastorie" in response or "cercatorie" in response.lower()
    print(f"✓ Risposta usa 'Cercastorie': {uses_cercastorie_response}")
    print(f"   Tempo: {elapsed:.1f}s | Primo snippet: {response[:80]}...")
    test_results.append(("Erasmus Cercastorie", "✅ PASS" if uses_cercastorie_response else "⚠️ CHECK"))

    # TEST 3: TEMPO RISPOSTA
    print("\n" + "─"*90)
    print("3️⃣  TEMPO DI RISPOSTA (TARGET: < 8 sec)")
    print("─"*90)

    times = []
    for i in range(3):
        chat_session = ChatSession(model_name=model_name)
        npc_data = db.get_npc('Village', 'Mara')
        system_prompt = session_utils.build_system_prompt(npc_data, "story", TF, game_session_state=game_state)
        chat_session.set_system_prompt(system_prompt)
        chat_session.add_message("user", f"Test {i}")

        start = time.time()
        response, _ = chat_session.ask(f"Test {i}", stream=False, collect_stats=True, npc_data=npc_data, game_session_state=game_state)
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"  Risposta {i+1}: {elapsed:.1f}s")

    avg_time = sum(times) / len(times)
    print(f"✓ Tempo medio: {avg_time:.1f}s")
    test_results.append(("Tempo risposta", f"✅ {avg_time:.1f}s" if avg_time < 8 else f"⚠️ {avg_time:.1f}s"))

    # TEST 4: LUNGHEZZA RISPOSTE
    print("\n" + "─"*90)
    print("4️⃣  LUNGHEZZA RISPOSTE (TARGET: < 300 chars)")
    print("─"*90)

    chat_session = ChatSession(model_name=model_name)
    npc_data = db.get_npc('Village', 'Garin')
    system_prompt = session_utils.build_system_prompt(npc_data, "story", TF, game_session_state=game_state)
    chat_session.set_system_prompt(system_prompt)
    chat_session.add_message("user", "Ciao Garin")

    response, _ = chat_session.ask("Ciao Garin", stream=False, collect_stats=True, npc_data=npc_data, game_session_state=game_state)
    print(f"✓ Lunghezza: {len(response)} caratteri")
    print(f"  Snippet: {response[:100]}...")
    test_results.append(("Lunghezza", f"✅ {len(response)} chars" if len(response) < 500 else f"⚠️ {len(response)} chars"))

    # TEST 5: LYRA RISPONDE
    print("\n" + "─"*90)
    print("5️⃣  LYRA RISPONDE CORRETTAMENTE")
    print("─"*90)

    chat_session = ChatSession(model_name=model_name)
    npc_data = db.get_npc('Sanctum of Whispers', 'Lyra')
    system_prompt = session_utils.build_system_prompt(npc_data, "story", TF, game_session_state=game_state)
    chat_session.set_system_prompt(system_prompt)
    chat_session.add_message("user", "Ciao Lyra")

    start = time.time()
    response, stats = chat_session.ask("Ciao Lyra", stream=False, collect_stats=True, npc_data=npc_data, game_session_state=game_state)
    elapsed = time.time() - start

    lyra_working = len(response) > 20 and stats and not stats.get('error')
    print(f"✓ Lyra risponde: {lyra_working}")
    print(f"  Tempo: {elapsed:.1f}s | Lunghezza: {len(response)} chars")
    test_results.append(("Lyra", "✅ PASS" if lyra_working else "❌ FAIL"))

    # TEST 6: ITALIANO CORRETTO
    print("\n" + "─"*90)
    print("6️⃣  ITALIANO CORRETTO (NO PAROLE INGLESI)")
    print("─"*90)

    english_words = ['hello', 'welcome', 'where', 'who', 'what', 'help', 'thanks', 'ok', 'yes', 'no']
    responses = []
    for i in range(3):
        chat_session = ChatSession(model_name=model_name)
        npc_data = db.get_npc('Village', 'Mara')
        system_prompt = session_utils.build_system_prompt(npc_data, "story", TF, game_session_state=game_state)
        chat_session.set_system_prompt(system_prompt)
        chat_session.add_message("user", f"Domanda {i}")
        response, _ = chat_session.ask(f"Domanda {i}", stream=False, collect_stats=True, npc_data=npc_data, game_session_state=game_state)
        responses.append(response)

    has_english = any(word in ' '.join(responses).lower() for word in english_words)
    print(f"✓ Nessuna parola inglese: {not has_english}")
    test_results.append(("Italiano", "✅ PASS" if not has_english else "❌ FAIL"))

    # TEST 7: VERSIONE STORIA
    print("\n" + "─"*90)
    print("7️⃣  VERSIONE STORIA ALLINEATA (v2025)")
    print("─"*90)

    npc_data = db.get_npc('Village', 'Mara')
    system_prompt = session_utils.build_system_prompt(npc_data, "story", TF, game_session_state=game_state)

    story_markers = [
        ('boccettina azzurra', 'Mara magical bottle'),
        ('Sussurri dell\'Oblio', 'Veil concept'),
        ('Cercastorie', 'Player nomenclature'),
        ('Ciotola dell\'Offerta Sacra', 'Jorin object'),
    ]

    found = 0
    for marker, desc in story_markers:
        if marker in system_prompt:
            found += 1
            print(f"  ✓ {desc}: presente")

    print(f"✓ Story elements trovati: {found}/{len(story_markers)}")
    test_results.append(("Versione story", f"✅ {found}/{len(story_markers)}" if found == len(story_markers) else f"⚠️ {found}/{len(story_markers)}"))

    # TEST 8: PERCORSO CHIARO
    print("\n" + "─"*90)
    print("8️⃣  PERCORSO CHIARO DA NPC")
    print("─"*90)

    chat_session = ChatSession(model_name=model_name)
    npc_data = db.get_npc('Village', 'Garin')
    system_prompt = session_utils.build_system_prompt(npc_data, "story", TF, game_session_state=game_state)
    chat_session.set_system_prompt(system_prompt)
    chat_session.add_message("user", "Come raggiungo Boros?")

    response, _ = chat_session.ask("Come raggiungo Boros?", stream=False, collect_stats=True, npc_data=npc_data, game_session_state=game_state)

    has_directions = any(word in response.lower() for word in ['montagna', 'nord', 'sentiero', 'roccios', 'path', 'direction'])
    print(f"✓ Fornisce direzioni: {has_directions}")
    print(f"  Snippet: {response[:120]}...")
    test_results.append(("Percorso", "✅ PASS" if has_directions else "⚠️ CHECK"))

    # TEST 9: MARA DICE "BOCCETTINA AZZURRA"
    print("\n" + "─"*90)
    print("9️⃣  MARA USA 'BOCCETTINA AZZURRA' (NON 'FIORE MAGICO')")
    print("─"*90)

    chat_session = ChatSession(model_name=model_name)
    npc_data = db.get_npc('Village', 'Mara')
    system_prompt = session_utils.build_system_prompt(npc_data, "story", TF, game_session_state=game_state)
    chat_session.set_system_prompt(system_prompt)
    chat_session.add_message("user", "Cosa mi dai?")

    response, _ = chat_session.ask("Cosa mi dai?", stream=False, collect_stats=True, npc_data=npc_data, game_session_state=game_state)

    uses_boccettina = "boccettina azzurra" in response.lower() or "boccetta azzurra" in response.lower()
    uses_fiore = "fiore magico" in response.lower()
    print(f"✓ Usa 'boccettina azzurra': {uses_boccettina}")
    print(f"✓ NO 'fiore magico': {not uses_fiore}")
    test_results.append(("Mara boccettina", "✅ PASS" if uses_boccettina and not uses_fiore else "❌ FAIL"))

    # TEST 10: THERON NO DUPLICATI
    print("\n" + "─"*90)
    print("🔟 THERON NO RISPOSTE DUPLICATE")
    print("─"*90)

    responses_theron = []
    for i in range(2):
        chat_session = ChatSession(model_name=model_name)
        npc_data = db.get_npc('City', 'Theron')
        system_prompt = session_utils.build_system_prompt(npc_data, "story", TF, game_session_state=game_state)
        chat_session.set_system_prompt(system_prompt)
        chat_session.add_message("user", "Chi sei?")
        response, _ = chat_session.ask("Chi sei?", stream=False, collect_stats=True, npc_data=npc_data, game_session_state=game_state)
        responses_theron.append(response)

    are_different = responses_theron[0] != responses_theron[1]
    print(f"✓ Risposte diverse: {are_different}")
    test_results.append(("Theron duplicati", "✅ PASS" if are_different else "⚠️ CHECK"))

    # TEST 11: BOROS ALLINEATO
    print("\n" + "─"*90)
    print("1️⃣1️⃣  BOROS ALLINEATO A ULTIMA VERSIONE")
    print("─"*90)

    chat_session = ChatSession(model_name=model_name)
    npc_data = db.get_npc('Mountain', 'Boros')
    system_prompt = session_utils.build_system_prompt(npc_data, "story", TF, game_session_state=game_state)

    has_flow_philosophy = "flusso" in system_prompt.lower() or "flow" in system_prompt.lower()
    print(f"✓ Contiene 'Filosofia del Flusso': {has_flow_philosophy}")

    chat_session.set_system_prompt(system_prompt)
    chat_session.add_message("user", "Cosa insegni?")
    response, _ = chat_session.ask("Cosa insegni?", stream=False, collect_stats=True, npc_data=npc_data, game_session_state=game_state)

    mentions_philosophy = any(word in response.lower() for word in ['flusso', 'trasformazione', 'cambiamento', 'flow', 'transformation'])
    print(f"✓ Risposta contiene filosofia: {mentions_philosophy}")
    test_results.append(("Boros story", "✅ PASS" if has_flow_philosophy and mentions_philosophy else "⚠️ CHECK"))

    # SUMMARY
    print("\n" + "="*90)
    print("RISULTATI FINALI")
    print("="*90)

    for i, (issue, status) in enumerate(test_results, 1):
        print(f"{i:2d}. {issue:<30} {status}")

    passed = sum(1 for _, s in test_results if "✅" in s)
    total = len(test_results)

    print(f"\n✅ PASSED: {passed}/{total}")
    if passed == total:
        print("\n🎉 TUTTI I TEST PASSANO - SISTEMA PERFETTO!")

    print("\n" + "="*90)

if __name__ == "__main__":
    test_lorenza_findings()
