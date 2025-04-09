# Nexus AI for Home Assistant

Nexus AI is an intelligent assistant add-on for Home Assistant that provides natural language interaction, smart home control, memory, and calendar integration.

## Features

- 🧠 Natural language processing using OpenAI GPT-4o
- 💾 Persistent memory with context awareness
- 🏠 Control your smart home through natural language
- 📅 Google Calendar integration
- 🎤 Optional voice input/output capabilities
- 📱 Web interface accessible from Home Assistant

## Installation

### Option 1: Home Assistant Add-on Store

1. In Home Assistant, navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Click the three dots in the upper right corner and select **Repositories**
3. Add this repository URL: `https://github.com/yourusername/nexus-ai-addon`
4. Find "Nexus AI" in the add-on store and click **Install**

### Option 2: Manual Installation

1. Copy the `nexus-ai-addon` folder to your Home Assistant `/addons` directory
2. Restart Home Assistant
3. Navigate to **Settings** → **Add-ons** → **Local Add-ons**
4. Find "Nexus AI" and click **Install**

## Configuration

After installation, you need to configure the add-on:

1. Set your OpenAI API key (required)
2. Enable Google Calendar integration (optional)
3. Enable voice processing (optional)

Example configuration:

```yaml
openai_api_key: "sk-..."
google_calendar_enabled: true
google_calendar_credentials: "{...}" # JSON credentials from Google Cloud Console
voice_enabled: false
log_level: "info"
