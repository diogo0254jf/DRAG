#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Hatchet configuration - use internal Docker hostname
HATCHET_INTERNAL_URL="http://hatchet:8080"
HATCHET_ADMIN_EMAIL="${HATCHET_ADMIN_EMAIL:-admin@example.com}"
HATCHET_ADMIN_PASSWORD="${HATCHET_ADMIN_PASSWORD:-Admin123!!}"
MAX_RETRIES=60
RETRY_INTERVAL=2

# Function to wait for Hatchet and get token
init_hatchet_token() {
    echo -e "${YELLOW}Waiting for Hatchet to be ready...${NC}"

    # Wait for Hatchet API to be available using internal hostname
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -s -f "${HATCHET_INTERNAL_URL}/api/v1/users/login" -X POST \
            -H "Content-Type: application/json" \
            -d "{\"email\": \"${HATCHET_ADMIN_EMAIL}\", \"password\": \"${HATCHET_ADMIN_PASSWORD}\"}" \
            > /dev/null 2>&1; then
            echo -e "${GREEN}Hatchet is ready!${NC}"
            break
        fi
        
        if [ $i -eq $MAX_RETRIES ]; then
            echo -e "${RED}Hatchet failed to start after ${MAX_RETRIES} attempts${NC}"
            return 1
        fi
        
        echo "   Attempt $i/$MAX_RETRIES - waiting ${RETRY_INTERVAL}s..."
        sleep $RETRY_INTERVAL
    done

    # Check if we already have a valid token
    if [ -n "$HATCHET_CLIENT_TOKEN" ]; then
        # Validate token by checking the grpc_broadcast_address claim
        TOKEN_GRPC=$(echo "$HATCHET_CLIENT_TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | grep -o '"grpc_broadcast_address":"[^"]*"' | cut -d'"' -f4 || echo "")
        
        if [ "$TOKEN_GRPC" = "hatchet:7077" ]; then
            echo -e "${GREEN}Existing token is valid (grpc: $TOKEN_GRPC)${NC}"
            return 0
        else
            echo -e "${YELLOW}Existing token has wrong grpc_broadcast_address: $TOKEN_GRPC${NC}"
            echo -e "${YELLOW}   Expected: hatchet:7077 - generating new token...${NC}"
        fi
    fi

    # Login and get session cookie using internal hostname (cookie domain matches)
    echo -e "${YELLOW}🔐 Logging into Hatchet...${NC}"
    LOGIN_RESPONSE=$(curl -s -v -c /tmp/cookies.txt \
        "${HATCHET_INTERNAL_URL}/api/v1/users/login" -X POST \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"${HATCHET_ADMIN_EMAIL}\", \"password\": \"${HATCHET_ADMIN_PASSWORD}\"}")
    
    echo "   Login response: $LOGIN_RESPONSE"

    # Get tenant ID using cookie
    echo -e "${YELLOW}📋 Getting tenant information...${NC}"
    TENANT_RESPONSE=$(curl -s -b /tmp/cookies.txt "${HATCHET_INTERNAL_URL}/api/v1/users/current/tenants")
    echo "   Tenant response: $TENANT_RESPONSE"
    
    # Try different JSON parsing approaches
    TENANT_ID=$(echo "$TENANT_RESPONSE" | sed 's/.*"tenantId":"\([^"]*\)".*/\1/' | head -1)
    
    # If that didn't work, try another approach
    if [ -z "$TENANT_ID" ] || [ "$TENANT_ID" = "$TENANT_RESPONSE" ] || [ "$TENANT_ID" = "null" ]; then
        # Try extracting from rows array
        TENANT_ID=$(echo "$TENANT_RESPONSE" | grep -o '"tenantId":"[^"]*"' | head -1 | cut -d'"' -f4)
    fi

    if [ -z "$TENANT_ID" ] || [ "$TENANT_ID" = "null" ]; then
        echo -e "${YELLOW}Could not get tenant from API, trying default tenant ID...${NC}"
        # Use default tenant ID from hatchet-lite
        TENANT_ID="707d0855-80ab-4e1f-a156-f1c4546cbf52"
    fi

    echo -e "${GREEN}   Tenant ID: $TENANT_ID${NC}"

    # Create API token
    echo -e "${YELLOW}Creating API token...${NC}"
    TOKEN_NAME="worker-token-$(date +%s)"
    TOKEN_RESPONSE=$(curl -s -b /tmp/cookies.txt \
        "${HATCHET_INTERNAL_URL}/api/v1/tenants/${TENANT_ID}/api-tokens" -X POST \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"${TOKEN_NAME}\"}")
    
    echo "   Token response: $TOKEN_RESPONSE"

    NEW_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

    if [ -z "$NEW_TOKEN" ]; then
        echo -e "${RED}Failed to create token${NC}"
        echo "   Full response: $TOKEN_RESPONSE"
        return 1
    fi

    echo -e "${GREEN}New token created successfully!${NC}"
    
    # Validate the new token
    NEW_TOKEN_GRPC=$(echo "$NEW_TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | grep -o '"grpc_broadcast_address":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
    echo -e "${GREEN}   Token grpc_broadcast_address: $NEW_TOKEN_GRPC${NC}"
    
    export HATCHET_CLIENT_TOKEN="$NEW_TOKEN"
    
    # Cleanup
    rm -f /tmp/cookies.txt
    return 0
}

# Init Hatchet token for worker AND api commands (both need to interact with Hatchet)
if [[ "$*" == *"worker"* ]] || [[ "$*" == *"hatchet"* ]] || [[ "$*" == *"uvicorn"* ]]; then
    init_hatchet_token || exit 1
fi

echo -e "${GREEN}Starting application...${NC}"

# Execute the passed command
if [ "$1" = "uvicorn" ]; then
    exec /app/.venv/bin/python -m "$@"
else
    exec "$@"
fi
