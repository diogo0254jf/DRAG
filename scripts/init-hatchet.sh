#!/bin/bash
set -e

echo "🔧 Initializing Hatchet..."

# Create encryption keys directory if it doesn't exist
mkdir -p /keys

# Check if encryption keys already exist
if [ ! -f "/keys/master.key" ] || [ ! -f "/keys/private_ec256.key" ] || [ ! -f "/keys/public_ec256.key" ]; then
    echo "🔐 Generating encryption keys..."
    /hatchet/hatchet-admin keyset create-local-keys --key-dir /keys
    echo "Encryption keys generated successfully"
else
    echo "Encryption keys already exist"
fi

# Wait for PostgreSQL to be ready (using simple sleep since depends_on handles readiness)
echo "Waiting for PostgreSQL..."
sleep 5
echo "PostgreSQL should be ready"

# Run database migrations using quickstart command
echo "🗄️  Running database migrations..."
/hatchet/hatchet-admin quickstart --skip-config --generated-config-dir /tmp 2>&1 | grep -v "config file" || true
echo "Database migrations completed"

echo "Hatchet initialization complete!"
