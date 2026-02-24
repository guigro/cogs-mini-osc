#!/bin/bash

echo "🧪 Tests cURL pour les requêtes POST vers l'OSC HTTP Webapp"
echo "============================================================"

BASE_URL="http://127.0.0.1:5009"

echo ""
echo "📝 Test POST avec JSON:"
echo "curl -X POST $BASE_URL/send_osc \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"address\": \"/test\", \"args\": [\"hello\", \"world\"]}'"

curl -X POST $BASE_URL/send_osc \
  -H "Content-Type: application/json" \
  -d '{"address": "/test", "args": ["hello", "world"]}'

echo ""
echo ""
echo "📝 Test GET pour comparaison:"
echo "curl '$BASE_URL/send_osc?address=/test&arg0=hello&arg1=world'"

curl "$BASE_URL/send_osc?address=/test&arg0=hello&arg1=world"

echo ""
echo ""
echo "📝 Test POST route quiz1:"
echo "curl -X POST $BASE_URL/send_osc \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"address\": \"/quiz1\", \"args\": [\"start\", \"set1\"]}'"

curl -X POST $BASE_URL/send_osc \
  -H "Content-Type: application/json" \
  -d '{"address": "/quiz1", "args": ["start", "set1"]}'

echo ""
echo ""
echo "✅ Tests terminés"