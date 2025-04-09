#!/usr/bin/with-contenv bashio
# ==============================================================================
# Initialize Nexus AI
# ==============================================================================
bashio::log.info "Initializing Nexus AI..."

# Data directory
data_dir=$(bashio::config 'data_directory')
mkdir -p "${data_dir}"

# Log level
log_level=$(bashio::config 'log_level')
bashio::log.level "${log_level}"

bashio::log.info "Preparation complete!"
