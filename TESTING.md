# Testing Nexus AI Without Home Assistant Approval

Since getting approval for the official Home Assistant add-on store can take time, here are several methods to test Nexus AI during development:

## Method 1: Custom Repository

This is the easiest approach that doesn't require approval:

1. Create a GitHub repository with your Nexus AI code
2. In your Home Assistant instance, go to **Settings** → **Add-ons** → **Add-on Store**
3. Click the three dots in the upper right corner and select **Repositories**
4. Add the URL to your GitHub repository and click **Add**
5. The Nexus AI add-on will appear in your add-on store
6. Install and test it like any other add-on

Note: Your repository must be public on GitHub for this to work.

## Method 2: Local Development

You can run the core Nexus AI application directly without Home Assistant:

1. Clone your repository
2. Set up a Python environment with the required dependencies
3. Run the Nexus AI application directly

This won't have all the Home Assistant integration features, but you can test the core functionality.

## Method 3: Manual Add-on Installation

You can manually install the add-on in your Home Assistant instance:

1. SSH into your Home Assistant host
2. Navigate to the add-on directory:
   ```bash
   cd /addons
   ```
3. Create a directory for your add-on:
   ```bash
   mkdir -p nexus_ai
   ```
4. Copy all files from your repository to this directory
5. Restart Home Assistant
6. Go to **Settings** → **Add-ons** → **Add-on Store**
7. Find "Nexus AI" in the list of local add-ons
8. Install and test it

## Testing Home Assistant Integration

To test the Home Assistant API integration:

1. Get a long-lived access token from your Home Assistant profile
2. Configure it in the Nexus AI settings
3. Test the connection through the Nexus AI web interface

## Testing OpenAI Integration

To test the OpenAI integration:

1. Get an OpenAI API key from https://platform.openai.com
2. Configure it in the Nexus AI add-on settings
3. Test AI features through the Nexus AI web interface

## Troubleshooting Common Issues

- **Add-on not appearing**: Make sure your repository follows the correct structure with config.json in the root
- **Installation errors**: Check the Home Assistant supervisor logs
- **Connection issues**: Verify your Home Assistant URL and long-lived access token
- **AI features not working**: Confirm your OpenAI API key is valid and has sufficient credits

## Ready for Production

When your add-on is fully tested and ready for wider distribution, you can:

1. Submit it to the Home Assistant Community Add-ons repository
2. Apply for inclusion in the official Home Assistant add-on store
