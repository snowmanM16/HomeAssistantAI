# Nexus AI Add-on for Home Assistant

## Overview

Nexus AI is an intelligent AI assistant for Home Assistant that enhances your smart home with advanced pattern recognition and automation capabilities. It uses artificial intelligence to learn from your habits and preferences, suggest automations, and provide natural language interaction with your smart home.

## Features

- 🤖 Natural language interface for controlling your smart home
- 🔍 Pattern recognition to detect habits and preferences
- ⚡ Automated suggestion and creation of Home Assistant automations
- 🧠 Long-term memory storage for user preferences and habits
- 📅 Google Calendar integration for context-aware assistance
- 🔄 Self-learning capabilities that improve over time

## Installation

### Option 1: Add-on Installation

1. Navigate to your Home Assistant instance.
2. Go to **Settings** → **Add-ons** → **Add-on Store**.
3. Click the three dots in the upper right corner and select **Repositories**.
4. Add the URL `https://github.com/yourusername/nexus-ai-addon` and click **Add**.
5. Find "Nexus AI" in the list of add-ons and click on it.
6. Click **Install** and wait for the installation to complete.
7. Configure the add-on (see Configuration section below).
8. Start the add-on.
9. Check the logs to make sure everything is working correctly.

### Option 2: Installation through HACS

1. Make sure you have [HACS](https://hacs.xyz/) installed.
2. Go to HACS in your Home Assistant instance.
3. Click on **Integrations**.
4. Click the three dots in the upper right corner and select **Custom repositories**.
5. Add the URL `https://github.com/yourusername/nexus-ai-addon` with category **Integration**.
6. Click **Add**.
7. Search for "Nexus AI" and install it.
8. Restart Home Assistant.
9. Go to **Settings** → **Devices & Services** → **Add Integration** and search for "Nexus AI".
10. Follow the configuration steps.

## Configuration

### Add-on Configuration Options

| Option | Description |
|--------|-------------|
| `log_level` | The log level for the add-on (trace/debug/info/warning/error/critical) |
| `use_local_llm` | Whether to use a local language model instead of OpenAI |
| `local_llm_url` | URL to a local LLM server (like Llama) if `use_local_llm` is true |
| `data_retention_days` | Number of days to keep historical data (1-365) |

### Initial Setup

After installing the add-on:

1. Open the Nexus AI web interface (it will be available as a sidebar item).
2. Go to the **Settings** tab.
3. Configure your Home Assistant connection:
   - The URL should be your internal Home Assistant URL (e.g., `http://homeassistant.local:8123`).
   - Create a [Long-Lived Access Token](https://developers.home-assistant.io/docs/auth_api/#long-lived-access-token) in your Home Assistant profile and enter it here.
4. Configure AI settings:
   - Enter your OpenAI API key if you want to use OpenAI's services.
   - Alternative: Enable "Use Local LLM" in the add-on configuration if you prefer local processing.
5. (Optional) Set up Google Calendar integration for calendar-aware assistance.

## Usage

### Chat Interface

The main interface is a chat where you can interact with Nexus AI using natural language. Example commands:

- "Turn on the living room lights"
- "Set the thermostat to 72 degrees"
- "When does the sun set today?"
- "Remember that I prefer the temperature at 68 degrees at night"
- "Create an automation to turn off all lights when I leave home"

### Automation Management

Nexus AI will detect patterns in your usage and suggest automations. You can:

- View, accept, or dismiss suggested automations
- Manage existing automations
- Ask Nexus AI to create custom automations

### Memory Management

Nexus AI maintains a memory of your preferences and important information:

- View and edit stored memories
- Manually add important information
- Set user preferences that Nexus AI should remember

## Troubleshooting

### Connection Issues

- Ensure your Home Assistant URL is correct and accessible from the add-on.
- Verify your long-lived access token is valid and has the necessary permissions.
- Check the add-on logs for any connection errors.

### AI Processing Issues

- If using OpenAI, check that your API key is valid and has sufficient credits.
- If using a local LLM, ensure the LLM server is running and accessible.
- Try adjusting the log level to "debug" for more detailed logs.

### Database Issues

- The add-on stores data in `/data/nexus`. If you're experiencing database issues, you can try resetting by stopping the add-on, renaming this folder, and starting again.

## Support

- Report issues on GitHub: [https://github.com/yourusername/nexus-ai-addon/issues](https://github.com/yourusername/nexus-ai-addon/issues)
- Ask questions in the Home Assistant community forums

## Credits

Nexus AI is developed and maintained by [Your Name].

## License

This project is licensed under the MIT License - see the LICENSE file for details.
