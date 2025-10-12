#!/bin/bash
echo "=== Test Brief Mode ==="
echo "Testing /brief command and concise NPC responses"
echo ""

# Reset
curl -s -X POST http://localhost:5000/reset -H "Content-Type: application/json" -d '{"key":"1234"}' > /dev/null
sleep 2

echo "1. Go to Forest and talk to Elira"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"BriefTest","message":"/go forest"}' > /dev/null
sleep 2
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"BriefTest","message":"/talk elira"}' > /dev/null
sleep 2

echo -e "\n2. Normal mode - greeting (should be verbose)"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"BriefTest","message":"Ciao Elira"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Elira: {d.get(\"npc_response\",\"No response\")}')"
sleep 4

echo -e "\n3. Activate brief mode"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"BriefTest","message":"/brief on"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'System: {d.get(\"npc_response\",\"No response\")}')"
sleep 2

echo -e "\n4. Brief mode - ask question (should be concise, 50-80 words)"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"BriefTest","message":"Cosa devo fare per avere il seme?"}' | python3 -c "import sys, json; d=json.load(sys.stdin); r=d.get('npc_response',''); print(f'Elira: {r}'); print(f'\nWord count: {len(r.split())} words')"
sleep 4

echo -e "\n5. Brief mode - show compassion (should give item with minimal text)"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"BriefTest","message":"Mi impegno ad aiutare la foresta"}' | python3 -c "import sys, json; d=json.load(sys.stdin); r=d.get('npc_response',''); print(f'Elira: {r}'); print(f'\nWord count: {len(r.split())} words')"
sleep 4

echo -e "\n6. Check inventory"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"BriefTest","message":"/inventory"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Inventory: {d.get(\"npc_response\",\"No response\")}')"

echo -e "\n7. Deactivate brief mode"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"BriefTest","message":"/brief off"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'System: {d.get(\"npc_response\",\"No response\")}')"

echo -e "\n=== Test Complete ==="
echo "Expected results:"
echo "  - Brief mode responses should be 50-80 words"
echo "  - No poetic descriptions in brief mode"
echo "  - Item transfer still works in brief mode"
