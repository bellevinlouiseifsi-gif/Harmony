"""
Music Cog - Handles all music-related commands
"""

import asyncio
import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands
from discord import utils

import config


# yt-dlp options for extracting audio
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': False,
    'quiet': False,  # Changed to False for debugging
    'no_warnings': False,
    'extract_flat': False,
    'verbose': True,  # Added verbose for debugging
    'js_runtimes': {'deno': {'executable': 'deno'}},
    'socket_timeout': 30,
    'extractor_retries': 3,
    'fragment_retries': 3,
    'extractor_args': {
        'youtube': {
            'player_client': ['web', 'web_creator', 'default'],
        },
        # Apple Music extractor options
        'applemusic': {
            'skip': 'webpages',
        },
    }
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}


class Song:
    """Represents a song in the queue."""
    
    def __init__(self, url, title, duration, thumbnail=None, requester=None):
        self.url = url
        self.title = title
        self.duration = duration
        self.thumbnail = thumbnail
        self.requester = requester
    
    def __str__(self):
        return self.title


class SongQueue:
    """Manages the song queue for a guild."""
    
    def __init__(self):
        self.queue = []
        self.current = None
    
    def add(self, song):
        """Add a song to the queue."""
        self.queue.append(song)
    
    def add_multiple(self, songs):
        """Add multiple songs to the queue."""
        self.queue.extend(songs)
    
    def next(self):
        """Get the next song and remove it from queue."""
        if self.queue:
            self.current = self.queue.pop(0)
            return self.current
        return None
    
    def shuffle(self):
        """Shuffle the remaining queue (not current song)."""
        if len(self.queue) > 1:
            # Keep current song at position 0, shuffle the rest
            current = self.queue[0]
            rest = self.queue[1:]
            import random
            random.shuffle(rest)
            self.queue = [current] + rest
    
    def clear(self):
        """Clear all songs from queue."""
        self.queue.clear()
        self.current = None
    
    def __len__(self):
        return len(self.queue)
    
    def get_list(self):
        """Get all songs as a list."""
        return self.queue.copy()


class MusicCog(commands.Cog):
    """Music commands cog."""
    
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}  # guild_id -> SongQueue
        self.players = {}  # guild_id -> voice_client
    
    def get_queue(self, guild_id):
        """Get or create queue for guild."""
        if guild_id not in self.queues:
            self.queues[guild_id] = SongQueue()
        return self.queues[guild_id]
    
    async def connect_to_voice(self, interaction, channel):
        """Connect to a voice channel."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"Attempting to connect to voice channel: {channel.name}")
            # Use timeout for voice connection
            vc = await asyncio.wait_for(
                channel.connect(),
                timeout=30.0
            )
            self.players[interaction.guild.id] = vc
            logger.info(f"Successfully connected to voice channel: {channel.name}")
            return vc
        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to voice channel: {channel.name}")
            raise Exception("Voice connection timed out. This may be due to firewall or network restrictions.")
        except Exception as e:
            logger.error(f"Error connecting to voice: {e}")
            raise
    
    async def play_next(self, interaction):
        """Play the next song in queue."""
        guild_id = interaction.guild.id
        queue = self.get_queue(guild_id)
        
        next_song = queue.next()
        if not next_song:
            # No more songs, disconnect
            if guild_id in self.players:
                await self.players[guild_id].disconnect()
                del self.players[guild_id]
            return
        
        await self.play_song(interaction, next_song)
    
    async def play_song(self, interaction, song):
        """Play a song."""
        guild_id = interaction.guild.id
        
        # Create audio source
        source = discord.FFmpegPCMAudio(song.url, **FFMPEG_OPTIONS)
        
        def after_playing(error):
            if error:
                print(f"Error in playback: {error}")
            # Schedule next song
            asyncio.run_coroutine_threadsafe(
                self.play_next(interaction),
                self.bot.loop
            )
        
        # Play the song
        vc = self.players.get(guild_id)
        if vc:
            vc.play(source, after=after_playing)
            
            # Update now playing message if needed
            embed = discord.Embed(
                title="🎵 Now Playing",
                description=f"**{song.title}**",
                color=discord.Color.green()
            )
            if song.thumbnail:
                embed.set_thumbnail(url=song.thumbnail)
            
            await interaction.followup.send(embed=embed, ephemeral=False)
    
    @app_commands.command(name="play", description="Play a YouTube video, playlist, or Apple Music track/album")
    @app_commands.describe(url="YouTube or Apple Music URL (video, playlist, track, or album)")
    async def play(self, interaction: discord.Interaction, url: str):
        """Play a YouTube video or playlist."""
        await interaction.response.defer()
        
        # Get user's voice channel
        voice_channel = interaction.user.voice.channel
        if not voice_channel:
            await interaction.followup.send(
                "❌ You must be in a voice channel to use this command!",
                ephemeral=True
            )
            return
        
        # Connect to voice if not already connected
        guild_id = interaction.guild.id
        vc = self.players.get(guild_id)
        
        if not vc or not vc.is_connected():
            try:
                vc = await self.connect_to_voice(interaction, voice_channel)
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Could not connect to voice channel: {str(e)}\n\n"
                    "This is often caused by:\n"
                    "- Firewall or antivirus blocking UDP connections\n"
                    "- Corporate/network restrictions\n"
                    "- Try disabling Windows Defender temporarily",
                    ephemeral=True
                )
                return
        
        # Extract song info using yt-dlp
        try:
            # Run extraction in a thread to avoid blocking
            info = await asyncio.to_thread(self._extract_song_info, url)
            
            if 'entries' in info:
                # It's a playlist
                songs = []
                for entry in info['entries']:
                    if entry:
                        song = Song(
                            url=entry['url'],
                            title=entry['title'],
                            duration=entry.get('duration', 0),
                            thumbnail=entry.get('thumbnail'),
                            requester=interaction.user
                        )
                        songs.append(song)
                
                queue = self.get_queue(guild_id)
                queue.add_multiple(songs)
                
                await interaction.followup.send(
                    f"✅ Added {len(songs)} songs from playlist to queue!"
                )
                
                # Start playing if not already playing
                if not vc.is_playing():
                    await self.play_next(interaction)
            else:
                # Single video
                song = Song(
                    url=info['url'],
                    title=info['title'],
                    duration=info.get('duration', 0),
                    thumbnail=info.get('thumbnail'),
                    requester=interaction.user
                )
                
                queue = self.get_queue(guild_id)
                queue.add(song)
                
                await interaction.followup.send(
                    f"✅ Added to queue: **{song.title}**"
                )
                
                # Start playing if not already playing
                if not vc.is_playing():
                    await self.play_next(interaction)
                        
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
            print(f"Error in play command: {e}")
    
    def _extract_song_info(self, url):
        """Extract song info using yt-dlp (runs in thread)."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[DEBUG] Starting extraction for URL: {url}")
        
        # Add verbose logging to diagnose extractor selection
        import yt_dlp
        
        # Get list of available extractors properly
        try:
            from yt_dlp.extractor import list_extractors
            extractor_list = list_extractors()
            available_ie_names = [ie.ie_key() for ie in extractor_list]
            apple_extractors = [e for e in available_ie_names if 'apple' in e.lower()]
            logger.info(f"[DEBUG] Available Apple extractors: {apple_extractors}")
        except Exception as e:
            logger.error(f"[DEBUG] Error getting extractors: {e}")
            available_ie_names = []
            apple_extractors = []
        
        # Pre-process URL to ensure Apple Music extractor is used
        import re
        original_url = url
        
        # Check if this is an Apple Music playlist URL with pl. prefix
        apple_music_playlist_match = re.match(r'(https?://music\.apple\.com/([a-z]{2})/playlist/[^/]+)/(pl\.[a-zA-Z0-9]+)', url)
        if apple_music_playlist_match:
            country = apple_music_playlist_match.group(2)
            playlist_id = apple_music_playlist_match.group(3)
            # Try different URL formats that yt-dlp might accept
            url_formats = [
                f"https://music.apple.com/{country}/playlist/-/{playlist_id}",
                f"https://music.apple.com/{country}/playlist/{playlist_id}",
            ]
            logger.info(f"[DEBUG] Transformed Apple Music playlist URL: {original_url} -> {url_formats}")
        else:
            url_formats = [url]
        
        # Try each URL format
        last_error = None
        for test_url in url_formats:
            logger.info(f"[DEBUG] Trying URL: {test_url}")
            
            # Try using the Apple Music extractor if available
            for extractor_name in apple_extractors:
                logger.info(f"[DEBUG] Trying with extractor: {extractor_name}")
                ydl_options = YDL_OPTIONS.copy()
                ydl_options['ie_key'] = extractor_name
                
                try:
                    with yt_dlp.YoutubeDL(ydl_options) as ydl:
                        info = ydl.extract_info(test_url, download=False)
                        logger.info(f"[DEBUG] Extraction successful with {extractor_name}")
                        return info
                except Exception as e:
                    logger.error(f"[DEBUG] {extractor_name} failed: {type(e).__name__}: {str(e)[:100]}")
                    last_error = e
                    continue
            
            # Try without ie_key
            try:
                with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                    info = ydl.extract_info(test_url, download=False)
                    logger.info(f"[DEBUG] Extraction successful without ie_key")
                    return info
            except Exception as e:
                logger.error(f"[DEBUG] Without ie_key failed: {type(e).__name__}: {str(e)[:100]}")
                last_error = e
        
        # All attempts failed
        logger.error(f"[DEBUG] All extraction attempts failed. Last error: {last_error}")
        raise last_error or Exception("Failed to extract info from URL")
    
    @app_commands.command(name="pause", description="Pause the current song")
    async def pause(self, interaction: discord.Interaction):
        """Pause the current song."""
        guild_id = interaction.guild.id
        vc = self.players.get(guild_id)
        
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Paused!", ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ Nothing is playing!",
                ephemeral=True
            )
    
    @app_commands.command(name="resume", description="Resume the current song")
    async def resume(self, interaction: discord.Interaction):
        """Resume the current song."""
        guild_id = interaction.guild.id
        vc = self.players.get(guild_id)
        
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Resumed!", ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ Nothing is paused!",
                ephemeral=True
            )
    
    @app_commands.command(name="skip", description="Skip to the next song")
    async def skip(self, interaction: discord.Interaction):
        """Skip to the next song."""
        guild_id = interaction.guild.id
        vc = self.players.get(guild_id)
        
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭️ Skipped!", ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ Nothing is playing!",
                ephemeral=True
            )
    
    @app_commands.command(name="stop", description="Stop playback and clear queue")
    async def stop(self, interaction: discord.Interaction):
        """Stop playback and clear queue."""
        guild_id = interaction.guild.id
        
        # Stop playback
        vc = self.players.get(guild_id)
        if vc:
            vc.stop()
            await vc.disconnect()
            del self.players[guild_id]
        
        # Clear queue
        queue = self.get_queue(guild_id)
        queue.clear()
        
        await interaction.response.send_message("⏹️ Stopped and queue cleared!", ephemeral=True)
    
    @app_commands.command(name="queue", description="Show the current queue")
    async def queue(self, interaction: discord.Interaction):
        """Show the current queue."""
        guild_id = interaction.guild.id
        queue = self.get_queue(guild_id)
        
        if len(queue) == 0 and not queue.current:
            await interaction.response.send_message(
                "📭 Queue is empty!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎵 Music Queue",
            color=discord.Color.blue()
        )
        
        # Current song
        if queue.current:
            embed.add_field(
                name="Now Playing",
                value=f"🎶 {queue.current.title}",
                inline=False
            )
        
        # Queue
        if len(queue) > 0:
            queue_text = ""
            for i, song in enumerate(queue.get_list()[:10], 1):
                queue_text += f"{i}. {song.title}\n"
            
            if len(queue) > 10:
                queue_text += f"\n... and {len(queue) - 10} more"
            
            embed.add_field(
                name=f"Up Next ({len(queue)} songs)",
                value=queue_text,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="nowplaying", description="Show the current song")
    async def nowplaying(self, interaction: discord.Interaction):
        """Show the current song."""
        guild_id = interaction.guild.id
        queue = self.get_queue(guild_id)
        
        if not queue.current:
            await interaction.response.send_message(
                "❌ Nothing is playing!",
                ephemeral=True
            )
            return
        
        song = queue.current
        
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{song.title}**",
            color=discord.Color.green()
        )
        
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        
        embed.add_field(name="Requested by", value=song.requester.mention if song.requester else "Unknown")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="shuffle", description="Shuffle the queue")
    async def shuffle(self, interaction: discord.Interaction):
        """Shuffle the queue."""
        guild_id = interaction.guild.id
        queue = self.get_queue(guild_id)
        
        if len(queue) <= 1:
            await interaction.response.send_message(
                "❌ Not enough songs in queue to shuffle!",
                ephemeral=True
            )
            return
        
        queue.shuffle()
        
        await interaction.response.send_message(
            "🔀 Queue shuffled!",
            ephemeral=True
        )


async def setup(bot):
    """Setup function for the cog."""
    await bot.add_cog(MusicCog(bot))
