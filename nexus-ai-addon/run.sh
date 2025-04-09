#!/bin/bash
set -e

CONFIG_PATH=/data/options.json

# Get configuration variables
export OPENAI_API_KEY="$(jq --raw-output '.openai_api_key // empty' $CONFIG_PATH)"
export GOOGLE_CALENDAR_ENABLED="$(jq --raw-output '.google_calendar_enabled // false' $CONFIG_PATH)"
export GOOGLE_CALENDAR_CREDENTIALS="$(jq --raw-output '.google_calendar_credentials // empty' $CONFIG_PATH)"
export VOICE_ENABLED="$(jq --raw-output '.voice_enabled // false' $CONFIG_PATH)"
export LOG_LEVEL="$(jq --raw-output '.log_level // "info"' $CONFIG_PATH)"

# Set default supervisor token from env
export SUPERVISOR_TOKEN=${SUPERVISOR_TOKEN:-""}

# Create or validate data directory
mkdir -p /data/nexus/db
mkdir -p /data/nexus/chromadb
mkdir -p /data/nexus/logs

# Set up logging
echo "Starting Nexus AI with log level: $LOG_LEVEL"

# Start the FastAPI server
cd /app
exec python -m uvicorn nexus.main:app --host 0.0.0.0 --port 5000
