#!/bin/bash

# Execute the passed command
if [ "$1" = "uvicorn" ]; then
    # Run uvicorn via python module to avoid shebang interpreter issues
    # and ensure we use the venv's python
    exec /app/.venv/bin/python -m "$@"
else
    exec "$@"
fi
