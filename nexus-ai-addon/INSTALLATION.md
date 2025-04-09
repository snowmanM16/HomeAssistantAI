# Nexus AI Installation Guide

This guide provides detailed steps for installing Nexus AI on your Home Assistant system.

## Option 1: Installation via Home Assistant Add-on Store

This is the recommended and easiest way to install Nexus AI.

### Step 1: Add the Repository

1. In Home Assistant, navigate to **Settings** → **Add-ons**
2. Click the menu (three dots) in the top-right corner 
3. Select **Repositories**
4. Add the repository URL: `https://github.com/yourusername/nexus-ai-addon`
5. Click **Add**

### Step 2: Install the Add-on

1. After adding the repository, click on **Add-on Store**
2. Refresh the page if Nexus AI doesn't appear immediately
3. Find **Nexus AI** in the list of add-ons
4. Click on it, then click **Install**
5. Wait for the installation to complete

### Step 3: Configuration

1. Once installed, go to the **Configuration** tab
2. Enter your OpenAI API key
3. Configure other options as needed:
   - Voice enablement
   - Google Calendar integration
4. Click **Save**

### Step 4: Start the Add-on

1. Go to the **Info** tab
2. Click **Start**
3. Enable **Start on boot** and **Watchdog** for automatic startup and monitoring
4. Click **Open Web UI** to access Nexus AI

## Option 2: Manual Installation

For advanced users who want to install manually.

### Prerequisites

- Home Assistant Supervised or Home Assistant OS
- Access to the host system
- Git installed

### Step 1: Clone the Repository

```bash
# Connect to your Home Assistant host
ssh homeassistant@your-ha-ip

# Navigate to the add-ons directory
cd /addons

# Clone the repository
git clone https://github.com/yourusername/nexus-ai-addon.git nexus-ai
```

### Step 2: Install via Add-on Store

1. In Home Assistant, navigate to **Settings** → **Add-ons**
2. Click the **Check for updates** button (refresh icon)
3. **Nexus AI** should appear in the local add-ons section
4. Click on it and follow the installation steps above (Step 2-4 from Option 1)

## Option 3: HACS Installation (Custom Integration)

For users who prefer to install as a custom integration through HACS.

Please see [HACS_INSTALLATION.md](HACS_INSTALLATION.md) for detailed instructions.

## Troubleshooting

### Common Issues

1. **Add-on not appearing in store:**
   - Make sure you've added the correct repository URL
   - Try refreshing the page or check for updates
   - Restart Home Assistant

2. **Installation errors:**
   - Check the logs for specific error messages
   - Ensure you have enough disk space
   - Make sure your Home Assistant instance meets the requirements

3. **Connection issues:**
   - Verify your Home Assistant URL and token are correct
   - Check network connectivity
   - Ensure your Home Assistant instance is accessible

4. **OpenAI API errors:**
   - Verify your API key is correct
   - Check your OpenAI account status and billing
   - Make sure you have access to the required models

### Getting Help

If you encounter issues not covered in this guide:

1. Check the [GitHub repository](https://github.com/yourusername/nexus-ai-addon) for known issues
2. Open a new issue with detailed information about your problem
3. Include logs, your Home Assistant version, and steps to reproduce the issue

## Updating

To update Nexus AI:

1. In Home Assistant, navigate to **Settings** → **Add-ons** → **Nexus AI**
2. Click on the **Update** button if an update is available
3. The add-on will automatically restart after updating
