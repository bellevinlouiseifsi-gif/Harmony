"""
Discord Music Bot Configuration
"""
import os

# Discord Bot Token - Get from https://discord.com/developers/applications
# 1. Go to Discord Developer Portal
# 2. Create a new application
# 3. Go to "Bot" section
# 4. Copy the token
# Set via environment variable DISCORD_BOT_TOKEN or fly secrets
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")



# Bot settings
BOT_PREFIX = "/"
BOT_NAME = "Musica Bot"

# Optional: Guild-specific settings
# GUILD_ID = your_guild_id_here

# Voice settings
MAX_QUEUE_SIZE = 1000
DEFAULT_VOLUME = 0.5
