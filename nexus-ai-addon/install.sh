#!/usr/bin/env bash

set -e

echo "================================================================"
echo "Nexus AI Add-on Installation"
echo "================================================================"

# Check if running on Home Assistant
if [ ! -d "/config" ] || [ ! -d "/usr/share/hassio" ]; then
  echo "This script should be run on a Home Assistant instance."
  echo "This is an add-on for Home Assistant, not a standalone application."
  exit 1
fi

# Check if add-ons directory exists
if [ ! -d "/config/addons" ]; then
  echo "Creating add-ons directory..."
  mkdir -p /config/addons
fi

# Check if Nexus AI add-on is already installed
if [ -d "/config/addons/nexus-ai" ]; then
  echo "Nexus AI add-on is already installed. Updating..."
  rm -rf /config/addons/nexus-ai
fi

# Clone the repository
echo "Cloning Nexus AI add-on repository..."
git clone https://github.com/yourusername/nexus-ai-addon.git /config/addons/nexus-ai

echo "================================================================"
echo "Installation complete!"
echo ""
echo "To use Nexus AI:"
echo "1. Go to Home Assistant"
echo "2. Navigate to Settings -> Add-ons -> Reload"
echo "3. You should see 'Nexus AI' in the add-on store"
echo "4. Install and configure the add-on"
echo "================================================================"
