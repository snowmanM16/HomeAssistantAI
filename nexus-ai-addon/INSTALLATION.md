# Installation Guide for Nexus AI Add-on

## Requirements

- Home Assistant with Supervisor (Home Assistant OS, Home Assistant Supervised, etc.)
- Internet connection for initial setup
- Optional: OpenAI API key for advanced AI features

## Installation Methods

### Method 1: Add-on Repository

1. Navigate to your Home Assistant instance
2. Go to **Settings** → **Add-ons** → **Add-on Store**
3. Click the three dots in the upper right corner and select **Repositories**
4. Add the URL `https://github.com/yourusername/nexus-ai-addon` and click **Add**
5. Find the "Nexus AI" add-on and click it
6. Click **Install**

### Method 2: Manual Installation

If you prefer to manually install the add-on:

1. SSH into your Home Assistant host
2. Navigate to the add-on directory:
   ```bash
   cd /addons
   ```
3. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/nexus-ai-addon
   ```
4. Restart Home Assistant
5. Go to **Settings** → **Add-ons** → **Add-on Store**
6. Find "Nexus AI" in the list of local add-ons
7. Click **Install**

## Post-Installation Setup

After installing the add-on:

1. Configure the add-on options:
   - Set your desired log level
   - Optionally provide your OpenAI API key for cloud-based AI processing
   - Configure local LLM settings if you prefer to use local language models

2. Start the add-on

3. Open the Nexus AI web interface:
   - The interface will be available as a sidebar item
   - Alternatively, you can access it directly via the URL provided in the add-on info

4. Complete the initial setup:
   - Configure your Home Assistant connection settings
   - Set up other integrations (like Google Calendar)
   - Customize your preferences

## Troubleshooting

If you encounter any issues during installation:

- Check the add-on logs for specific error messages
- Ensure your Home Assistant instance meets the requirements
- Verify that you have proper internet connectivity
- Make sure you have sufficient free disk space (at least 1GB recommended)

For more detailed troubleshooting, refer to the [DOCS.md](DOCS.md) file.
