#!/usr/bin/with-contenv bashio

# Get config
CONFIG_PATH=/data/options.json
LOG_LEVEL=$(bashio::config 'log_level')
USE_LOCAL_LLM=$(bashio::config 'use_local_llm')
LOCAL_LLM_URL=$(bashio::config 'local_llm_url')
DATA_RETENTION_DAYS=$(bashio::config 'data_retention_days')

# Set log level
bashio::log.level "${LOG_LEVEL}"

# Create required directories
mkdir -p /data/nexus

# Set environment variables
export LOG_LEVEL="${LOG_LEVEL}"
export DATA_DIR="/data/nexus"
export DATABASE_URL="sqlite:////data/nexus/database.sqlite"

# Configure OpenAI API key if set
OPENAI_API_KEY=$(bashio::config 'openai_api_key' '')
if [[ ! -z "${OPENAI_API_KEY}" ]]; then
    export OPENAI_API_KEY="${OPENAI_API_KEY}"
fi

# Configure local LLM usage
export USE_LOCAL_LLM="${USE_LOCAL_LLM}"
export LOCAL_LLM_URL="${LOCAL_LLM_URL}"
export DATA_RETENTION_DAYS="${DATA_RETENTION_DAYS}"

# Enable ingress for Nexus AI
INGRESS_PORT=$(bashio::addon.ingress_port)
export PORT="${INGRESS_PORT}"

# Start the Nexus AI application with ingress support
cd /app
exec python3 -m nexus.main --host 0.0.0.0 --port "${INGRESS_PORT}"
