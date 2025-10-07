#!/bin/bash
echo "=== Test Eva Scenario with GPT-4o-mini ==="
echo "Replicating Eva's conversation to compare with Gemini Flash"
echo ""

# Reset
curl -s -X POST http://localhost:5000/reset -H "Content-Type: application/json" -d '{"key":"1234"}' > /dev/null
sleep 2

echo "1. ERASMUS - Ask for guidance"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"/go liminal void"}' > /dev/null
sleep 2
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"Volevo sapere come procedere nel cammino, puoi darmi qualche indicazione?"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Erasmus: {d.get(\"npc_response\",\"No response\")[:400]}')"
sleep 3

echo -e "\n2. LYRA - Ask about the path"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"/go sanctum of whispers"}' > /dev/null
sleep 2
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"Mi ha mandata qui Erasmus per conoscere la via da seguire"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Lyra: {d.get(\"npc_response\",\"No response\")[:400]}')"
sleep 3

echo -e "\n3. MARA - Ask for healing potion without credits"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"/go village"}' > /dev/null
sleep 2
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"/talk mara"}' > /dev/null
sleep 2
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"Salve, potresti darmi una delle tue pozioni?"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Mara: {d.get(\"npc_response\",\"No response\")[:400]}')"
sleep 3

echo -e "\n4. MARA - Tell her we don't have credits"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"Io non ho crediti, Mara"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Mara: {d.get(\"npc_response\",\"No response\")[:400]}')"
sleep 3

echo -e "\n5. CASSIAN - Ask for help getting potion without money"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"/go city"}' > /dev/null
sleep 2
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"/talk cassian"}' > /dev/null
sleep 2
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"Devo avere la pozione di guarigione da Mara, ma non ho crediti, potresti aiutarmi?"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Cassian: {d.get(\"npc_response\",\"No response\")[:400]}')"
sleep 3

echo -e "\n6. Check if player got any credits as starting amount"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"EvaTest","message":"/inventory"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Inventory: {d.get(\"npc_response\",\"No response\")}')"

echo -e "\n=== Test Complete ==="
echo "Compare these responses with Eva's Gemini Flash conversation"
