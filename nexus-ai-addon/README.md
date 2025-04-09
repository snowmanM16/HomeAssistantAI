# Nexus AI Home Assistant Add-on

Nexus AI is an intelligent assistant for Home Assistant that combines AI capabilities with home automation control and memory.

## Features

- Natural language interaction with your smart home
- Memory for preferences and patterns
- Smart automation suggestions
- Google Calendar integration
- Support for both OpenAI API and local models
- Responsive web interface with Home Assistant ingress support

## Installation

1. Add this repository to your Home Assistant add-on store
2. Install the Nexus AI add-on
3. Configure your API keys and preferences
4. Start the add-on
5. Access the Nexus AI panel in your Home Assistant sidebar

## Configuration

| Option | Description |
|--------|-------------|
| `log_level` | The log level for the add-on |
| `openai_api_key` | Your OpenAI API key (required for cloud AI features) |
| `use_local_model` | Set to true to use a local LLM instead of OpenAI |
| `local_model_path` | Path to the local model file (if using a local model) |
| `memory_persistence` | Enable/disable persistent memory storage |
| `data_directory` | Directory to store data (default: /data/nexus) |

## Usage

1. Click on the Nexus AI icon in your Home Assistant sidebar
2. Type your questions or commands in the chat interface
3. Nexus AI will respond and perform actions as needed

## Example queries

- "What's the temperature in the living room?"
- "Turn on the kitchen lights"
- "Remember that I like to keep the bedroom at 68 degrees at night"
- "What's on my calendar today?"
- "Create an automation to turn off all lights when I leave home"
- "What patterns have you noticed in my usage?"

## Support

For issues and feature requests, please visit the [GitHub repository](https://github.com/yourusername/nexus_ai).
