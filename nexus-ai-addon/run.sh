#!/usr/bin/env bashio

CONFIG_PATH=/data/options.json

# Get configuration values
export LOG_LEVEL=$(bashio::config 'log_level')
export DATA_DIR=/data
export LOGS_DIR=/data/logs
export VOICE_ENABLED=$(bashio::config 'voice_enabled')
export GOOGLE_CALENDAR_ENABLED=$(bashio::config 'google_calendar_enabled')
export OPENAI_API_KEY=$(bashio::config 'openai_api_key')

# Create required directories
mkdir -p /data/db
mkdir -p /data/chromadb
mkdir -p /data/logs

# Display startup message
bashio::log.info "Starting Nexus AI..."
bashio::log.info "Log level: ${LOG_LEVEL}"
bashio::log.info "Data directory: ${DATA_DIR}"
bashio::log.info "Voice enabled: ${VOICE_ENABLED}"
bashio::log.info "Google Calendar enabled: ${GOOGLE_CALENDAR_ENABLED}"

# Check for API key
if [ -z "${OPENAI_API_KEY}" ]; then
  bashio::log.warning "OpenAI API key not provided. AI capabilities will be limited."
fi

# Run the application
cd /opt/nexus-ai
python -m uvicorn nexus.main:app --host 0.0.0.0 --port 8099