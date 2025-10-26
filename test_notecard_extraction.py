#!/usr/bin/env python3
"""Test notecard extraction from NPC responses."""

from chat_manager import extract_notecard_from_response

# Test 1: Simple notecard
print("=" * 80)
print("TEST 1: Simple notecard extraction")
print("=" * 80)

response1 = """Benvenuto, cercastorie! Ho qualcosa per te.
[notecard=Pergamena_Test|# Titolo\n\nContenuto della pergamena\nSeconda riga]
Spero ti piaccia!"""

cleaned, name, content = extract_notecard_from_response(response1)
print(f"Original: {response1[:50]}...")
print(f"Cleaned: {cleaned}")
print(f"Notecard Name: {name}")
print(f"Notecard Content: {content[:50]}...")
print(f"✓ Test 1 passed!\n")

# Test 2: Lyra's actual notecard with embedded newlines
print("=" * 80)
print("TEST 2: Lyra's complex notecard")
print("=" * 80)

response2 = """Sì... posso sentire le memorie antiche nel cristallo. Hai fatto bene a portarmelo. Ecco il Telaio dell'Eco - ora potremo comunicare con i Tessitori perduti. E questo... questo è Filo della Memoria, tessuto dal tuo atto di preservazione. [notecard=Pergamena_Preservazione_Memoria|# PERGAMENA DI PRESERVAZIONE DELLA MEMORIA\n\n## Il Velo e i Tessitori\n\nI Tessitori crearono il Velo per proteggere la memoria dall'Oblio.\nMa il Velo si indebolisce. I Sussurri dell'Oblio guadagnano forza.\n\n## La Crisi Attuale\n\nOgni giorno il Velo perde filamenti. Le memorie svaniscono.\nI Tessitori hanno sacrificato tutto per mantenerlo.\nOra il loro potere sta cedendo.\n\n## Le Tre Scelte\n\n1. PRESERVARE - Rinnovare il Velo, mantenere lo status quo\n2. TRASFORMARE - Evolvere il Velo, permettere il cambiamento\n3. DISSOLVERE - Accettare l'Oblio, abbracciare la trasformazione\n\n## La Tua Importanza\n\nTu, Cercastorie, sei il catalizzatore.\nLe tue scelte determineranno il destino di Eldoria.\nNon è solo una questione di potere - è di saggezza.\n\nImpara da coloro che incontri.\nAscolti i Sussurri ma non lasciarti dominare.\nScegli con il cuore, non con la paura.]"""

cleaned2, name2, content2 = extract_notecard_from_response(response2)
print(f"Notecard Name: {name2}")
print(f"Content Length: {len(content2)} chars")
print(f"Content starts with: {content2[:60]}...")
print(f"Cleaned response: {cleaned2}")
print(f"✓ Test 2 passed!\n")

# Test 3: No notecard
print("=" * 80)
print("TEST 3: Response without notecard")
print("=" * 80)

response3 = "Ciao cercastorie! Benvenuto a Eldoria. Non ho documenti per te."
cleaned3, name3, content3 = extract_notecard_from_response(response3)
print(f"Original: {response3}")
print(f"Cleaned: {cleaned3}")
print(f"Name: '{name3}' (should be empty)")
print(f"Content: '{content3}' (should be empty)")
assert name3 == ""
assert content3 == ""
print(f"✓ Test 3 passed!\n")

# Test 4: Multiple notecards (should extract first one)
print("=" * 80)
print("TEST 4: Multiple notecards (extracts first)")
print("=" * 80)

response4 = """First part [notecard=First|content1] middle part [notecard=Second|content2] end"""
cleaned4, name4, content4 = extract_notecard_from_response(response4)
print(f"First notecard name: {name4}")
print(f"First notecard content: {content4}")
print(f"Cleaned response: {cleaned4}")
assert name4 == "First"
assert content4 == "content1"
assert "[notecard=Second" in cleaned4  # Second notecard still in cleaned response
print(f"✓ Test 4 passed!\n")

print("=" * 80)
print("✅ ALL TESTS PASSED!")
print("=" * 80)
