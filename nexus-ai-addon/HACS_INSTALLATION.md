# Installing Nexus AI with HACS

This guide will help you install Nexus AI as a custom integration using the Home Assistant Community Store (HACS).

## Prerequisites

1. Home Assistant installed and running
2. HACS installed (see [HACS installation guide](https://hacs.xyz/docs/installation/installation) if you don't have it yet)

## Installation Steps

### Step 1: Add Nexus AI Repository to HACS

1. Open Home Assistant
2. Navigate to HACS (in the sidebar)
3. Click on "Integrations"
4. Click the three dots in the top-right corner
5. Select "Custom repositories"
6. Add the following information:
   - Repository: `https://github.com/yourusername/nexus-ai-addon`
   - Category: "Integration"
7. Click "Add"

### Step 2: Install Nexus AI Integration

1. After adding the repository, click on "Integrations" in HACS
2. Search for "Nexus AI"
3. Click on "Nexus AI"
4. Click on "Install"
5. Restart Home Assistant when prompted

### Step 3: Configure Nexus AI

1. After restarting, go to "Settings" > "Devices & Services"
2. Click the "+ Add Integration" button in the bottom-right
3. Search for "Nexus AI" and select it
4. Follow the configuration steps:
   - Enter your OpenAI API key
   - Configure additional settings as needed

### Step 4: Access Nexus AI

Once configured, you can access Nexus AI in two ways:

1. As a panel in the Home Assistant sidebar
2. Through the Nexus AI card that you can add to any dashboard

## Updating Nexus AI

To update Nexus AI when new versions are released:

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Look for Nexus AI in the list of installed integrations
4. If an update is available, you'll see an update button
5. Click "Update" and restart Home Assistant when prompted

## Support

If you encounter any issues with the installation or have questions:

- Check the [Nexus AI GitHub repository](https://github.com/yourusername/nexus-ai-addon) for known issues
- Open a new issue on GitHub if you can't find a solution
