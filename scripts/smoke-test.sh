#!/bin/bash
# Smoke test: two chat turns that check conversation memory.

# 1. Start a new conversation
echo "--- Turn 1: Tell about dog ---"
RESP1=$(curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Eu tenho um cachorro que chama Dobby"}')

echo "Response 1: $RESP1"

CONV_ID=$(echo $RESP1 | sed -E 's/.*"conversation_id":"([^"]+)".*/\1/')
echo "Conversation ID: $CONV_ID"

if [ -z "$CONV_ID" ]; then
  echo "Failed to get conversation ID"
  exit 1
fi

# 2. Ask about the dog
echo -e "\n--- Turn 2: Ask name ---"
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"conversation_id\": \"$CONV_ID\", \"message\": \"Qual o nome do meu cachorro?\"}"
echo ""
