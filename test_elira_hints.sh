#!/bin/bash
echo "=== Test Elira with [Hints] and Summary ==="
echo "Testing that Elira shows hints and accepts verbal compassion proof"
echo ""

# Reset
curl -s -X POST http://localhost:5000/reset -H "Content-Type: application/json" -d '{"key":"1234"}' > /dev/null
sleep 2

echo "1. Go to Forest and talk to Elira"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"/go forest"}' > /dev/null
sleep 2
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"/talk elira"}' > /dev/null
sleep 2

echo -e "\n2. First greeting - should show hints in []"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"Ciao Elira"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Elira: {d.get(\"npc_response\",\"No response\")}')"
sleep 3

echo -e "\n3. Ask about the Blight Sample - should show [Hint: Non serve trovarlo fisicamente...]"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"E dove trovo questo Blight Sample?"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Elira: {d.get(\"npc_response\",\"No response\")}')"
sleep 3

echo -e "\n4. Tell her we care about the forest (verbal proof) - should accept and give Seed"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"Mi impegno ad aiutare la foresta, Elira. Sento la sofferenza degli alberi."}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Elira: {d.get(\"npc_response\",\"No response\")}')"
sleep 3

echo -e "\n5. Check inventory - should have Seme della Foresta"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"/inventory"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Inventory: {d.get(\"npc_response\",\"No response\")}')"

echo -e "\n=== Test Complete ==="
echo "Expected results:"
echo "  - Elira should show [Hint: ...] in her responses"
echo "  - She should accept verbal compassion proof"
echo "  - Player should receive Seme della Foresta"
