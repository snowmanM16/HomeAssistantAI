# Nexus AI for Home Assistant

Nexus AI is an intelligent AI assistant add-on for Home Assistant with memory, pattern recognition, and smart automation capabilities.

## Features

- 🤖 **AI-Powered Assistant**: Natural language interaction with your smart home using OpenAI's GPT models
- 🧠 **Memory System**: Remembers preferences and past interactions to provide personalized responses
- 📊 **Pattern Recognition**: Identifies usage patterns and suggests automations based on your behavior
- 🔄 **Automation Creation**: Generates and deploys Home Assistant automations with a single click
- 📅 **Calendar Integration**: Optional Google Calendar integration to be aware of your schedule
- 🌐 **Modern Web Interface**: Clean, responsive UI for interacting with the assistant

## Installation

### Installation via Home Assistant Add-on Store

1. In Home Assistant, navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Click the menu (three dots) in the top-right corner and select **Repositories**
3. Add this repository URL: `https://github.com/yourusername/nexus-ai-addon`
4. Find the "Nexus AI" add-on in the list and click install
5. Wait for the installation to complete
6. Configure your settings (see Configuration section)
7. Start the add-on
8. Click "OPEN WEB UI" to access the Nexus AI interface

### Manual Installation

If you prefer to install manually, you can clone this repository into your Home Assistant's `addons` directory:

```bash
cd /path/to/your/home_assistant/addons
git clone https://github.com/yourusername/nexus-ai-addon
```

Then restart Home Assistant and proceed with the installation from the Add-on Store.

## Configuration

After installation, you'll need to configure the add-on:

1. **OpenAI API Key**: You'll need an API key from OpenAI to use the AI capabilities
2. **Voice Processing**: Enable/disable voice commands and responses
3. **Google Calendar**: Enable/disable Google Calendar integration

## Usage

After starting the add-on:

1. Access the web interface via the "OPEN WEB UI" button in the add-on page
2. Connect to your Home Assistant instance when prompted
3. Start interacting with the assistant by typing or speaking
4. View and manage suggested automations in the Automations tab
5. Access settings and preferences in the Settings tab

## FAQ

**Q: Does this require an OpenAI API key?**  
A: Yes, Nexus AI uses OpenAI's GPT models to provide intelligent responses and analyze patterns. You'll need to provide your own API key in the add-on configuration.

**Q: Can it work offline without internet?**  
A: Currently, Nexus AI requires internet access for the OpenAI API. We're exploring options for local LLM support in future versions.

**Q: Will this consume a lot of API tokens?**  
A: Nexus AI is designed to be efficient with API usage. The amount of tokens used will depend on how frequently you interact with it and how complex your requests are.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Home Assistant team for creating an amazing smart home platform
- OpenAI for providing the AI models that power this assistant
