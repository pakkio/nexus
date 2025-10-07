#!/bin/bash
echo "=== Testing Natural Language Payment ==="

# Reset
curl -s -X POST http://localhost:5000/reset -H "Content-Type: application/json" -d '{"key":"1234"}' > /dev/null
sleep 2

# Go to village
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"NaturalTest","message":"/go village"}' > /dev/null
sleep 2

# Talk to Mara
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"NaturalTest","message":"/talk mara"}' > /dev/null
sleep 2

echo ""
echo "Test 1: Natural language purchase - 'Ti do 50 crediti, mi vendi la pozione?'"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"NaturalTest","message":"Ti do 50 crediti, mi vendi la pozione?"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Mara: {d.get(\"npc_response\",\"No response\")[:300]}\n\nSystem: {d.get(\"system_messages\",[])}')"
sleep 3

echo ""
echo "Check inventory after purchase:"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"NaturalTest","message":"/inventory"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('npc_response',''))"
sleep 2

echo ""
echo "=== Test 2: New player with different natural language ==="
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"NaturalTest2","message":"/go village"}' > /dev/null
sleep 2
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"NaturalTest2","message":"/talk mara"}' > /dev/null
sleep 2

echo ""
echo "Test with: 'Voglio comprare la pozione di guarigione'"
curl -s -X POST http://localhost:5000/api/chat -H "Content-Type: application/json" -d '{"player_id":"NaturalTest2","message":"Voglio comprare la pozione di guarigione"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Mara: {d.get(\"npc_response\",\"No response\")[:300]}\n\nSystem: {d.get(\"system_messages\",[])}')"

echo ""
echo "=== Test Complete ==="
