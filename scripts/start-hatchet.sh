#!/bin/bash
set -e

# Run initialization
/scripts/init-hatchet.sh

# Start the Hatchet engine
echo "🚀 Starting Hatchet Engine..."
exec /hatchet/hatchet-engine
