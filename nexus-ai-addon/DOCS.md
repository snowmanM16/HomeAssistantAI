# Home Assistant Add-on: Nexus AI

## Installation

Follow these steps to get the add-on installed on your system:

1. Navigate in your Home Assistant frontend to **Settings** -> **Add-ons** -> **Add-on Store**.
2. Click the 3-dots menu in the upper right and select **Repositories**.
3. Add the URL of this repository and click **Add**.
4. Find the "Nexus AI" add-on and click it.
5. Click on the "INSTALL" button.

## How to use

1. Set your OpenAI API key in the configuration (if using OpenAI).
2. Start the add-on.
3. Click the "OPEN WEB UI" button to open the Nexus AI web interface.
4. In the Nexus AI web interface, configure your Home Assistant connection using a long-lived access token.

### OpenAI API Key

To use the cloud-based AI features, you need an OpenAI API key:

1. Create an account or log in at [OpenAI's platform](https://platform.openai.com/)
2. Navigate to the [API keys section](https://platform.openai.com/api-keys)
3. Create a new API key
4. Copy the key and paste it in the add-on configuration

### Local AI Models (Optional)

If you prefer not to use OpenAI, you can enable the local model option in the configuration.

## Configuration

Example add-on configuration:

```yaml
log_level: info
openai_api_key: sk-abcdefghijklmnopqrstuvwxyz1234567890
use_local_model: false
local_model_path: ""
memory_persistence: true
data_directory: /data/nexus
```

### Option: `log_level`

The `log_level` option controls the level of log output by the add-on and can
be changed to be more or less verbose, which might be useful when you are
dealing with an unknown issue. Possible values are:

- `trace`: Show every detail, like all called internal functions.
- `debug`: Shows detailed debug information.
- `info`: Normal (usually) interesting events.
- `warning`: Exceptional occurrences that are not errors.
- `error`: Runtime errors that do not require immediate action.
- `fatal`: Something went terribly wrong. Add-on becomes unusable.

Please note that each level automatically includes log messages from a
more severe level, e.g., `debug` also shows `info` messages. By default,
the `log_level` is set to `info`, which is the recommended setting unless
you are troubleshooting.

### Option: `openai_api_key`

This option allows you to specify your OpenAI API key for cloud-based AI features.
Leave empty if you're using a local model.

### Option: `use_local_model`

Set to `true` to use a local LLM instead of OpenAI's cloud services.

### Option: `local_model_path`

The path to your local model file when using a local model.

### Option: `memory_persistence`

Enable or disable persistent memory storage. When enabled, Nexus AI will remember
preferences and patterns between restarts.

### Option: `data_directory`

The directory where Nexus AI stores its data. Default is `/data/nexus`.

## Support

Got questions?

You have several options to get them answered:

- The [Home Assistant Discord Chat Server][discord].
- The Home Assistant [Community Forum][forum].
- Join the [Reddit subreddit][reddit] in [/r/homeassistant][reddit]

In case you've found an issue, please [open an issue on our GitHub][issue].

[discord]: https://discord.gg/c5DvZ4e
[forum]: https://community.home-assistant.io
[issue]: https://github.com/yourusername/nexus_ai/issues
[reddit]: https://reddit.com/r/homeassistant
