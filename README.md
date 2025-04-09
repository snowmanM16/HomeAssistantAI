# Nexus AI for Home Assistant

This repository contains Nexus AI, an intelligent assistant for Home Assistant that uses AI to enhance your smart home experience.

## Testing & Development Installation

### Method: Custom Add-on Repository

You don't need approval to test this as a custom repository:

1. In your Home Assistant instance, go to **Settings** → **Add-ons** → **Add-on Store**
2. Click the three dots in the upper right corner and select **Repositories**
3. Add the URL to this repository and click **Add**
4. The Nexus AI add-on will appear in your add-on store
5. Install and test it like any other add-on

### Project Structure

This repository follows the standard Home Assistant add-on repository structure:

- `nexus-ai-addon/` - Contains the add-on files
  - `config.json` - Add-on configuration
  - `Dockerfile` - Container definition
  - `run.sh` - Startup script
  - Other supporting files

## Features

- 🤖 Natural language interface for controlling your smart home
- 🔍 Pattern recognition to detect habits and preferences
- ⚡ Automated suggestion and creation of Home Assistant automations
- 🧠 Long-term memory storage for user preferences
- 📅 Google Calendar integration for context-aware assistance

## Documentation

See the [DOCS.md](nexus-ai-addon/DOCS.md) file for detailed documentation.

## License

This project is licensed under the MIT License - see the [LICENSE](nexus-ai-addon/LICENSE) file for details.
