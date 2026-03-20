"""
Discord Music Bot - Main Entry Point
"""

import asyncio
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

import config
from music_cog import MusicCog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MusicBot(commands.Bot):
    """Custom bot class for the music bot."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        
        super().__init__(
            command_prefix=config.BOT_PREFIX,
            intents=intents,
            case_insensitive=True
        )
        
        self.synced = False
    
    async def setup_hook(self):
        """Setup hook called when the bot is ready."""
        # Add music cog
        await self.add_cog(MusicCog(self))
        
        # Sync commands
        if not self.synced:
            await self.tree.sync()
            self.synced = True
            logger.info("Commands synced successfully")
        
        logger.info(f"{config.BOT_NAME} is ready!")
    
    async def close(self):
        """Clean up when bot shuts down."""
        await super().close()
        logger.info("Bot closed successfully")


async def main():
    """Main entry point."""
    # Check if token is set
    if config.DISCORD_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("Please set your Discord bot token in config.py!")
        logger.error("Get your token from: https://discord.com/developers/applications")
        return
    
    # Create and run bot
    bot = MusicBot()
    
    try:
        await bot.start(config.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        await bot.close()
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
