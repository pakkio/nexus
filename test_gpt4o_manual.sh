#!/bin/bash
echo "=== GPT-4o-mini NPC Dialog Test ==="
echo ""

# Reset
echo "Resetting..."
curl -s -X POST http://localhost:5000/reset -H "Content-Type: application/json" -d '{"key":"1234"}' > /dev/null
sleep 2

# Test 1: Navigate and greet Syra
echo "Test 1: Navigate to Ancient Ruins and meet Syra"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"Test1","message":"/go ancient ruins"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Location: {d.get(\"current_area\")}')"
sleep 2

echo ""
echo "Test 2: Greet Syra"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"Test1","message":"Hello Syra, what brings travelers to you?"}' | python3 -c "import sys, json; d=json.load(sys.stdin); resp=d.get('npc_response',''); print(f'Syra: {resp[:300]}')"
sleep 3

echo ""
echo "Test 3: Ask about trading requirements"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"Test1","message":"What do you need for a trade?"}' | python3 -c "import sys, json; d=json.load(sys.stdin); resp=d.get('npc_response',''); print(f'Syra: {resp[:300]}')"
sleep 3

echo ""
echo "Test 4: Try trading without items"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"Test1","message":"I want to complete the trade"}' | python3 -c "import sys, json; d=json.load(sys.stdin); resp=d.get('npc_response',''); print(f'Syra: {resp[:300]}')"
sleep 3

echo ""
echo "=== Test with Irenna (Teleporter) ==="
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"Test2","message":"/go city"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Location: {d.get(\"current_area\")}')"
sleep 2

echo ""
echo "Test: Ask Irenna about teleportation"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"Test2","message":"Can you teleport me to the Ancient Ruins?"}' | python3 -c "import sys, json; d=json.load(sys.stdin); resp=d.get('npc_response',''); offered=d.get('teleport_offered',False); print(f'Irenna: {resp[:300]}\nTeleport Offered: {offered}')"

echo ""
echo "=== Test Complete ==="
