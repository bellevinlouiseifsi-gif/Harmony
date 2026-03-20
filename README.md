# Discord Music Bot

A simple Discord music bot that plays YouTube videos and playlists using slash commands.

## Features

- 🎵 Play YouTube videos and playlists
- ⏸️ Pause/Resume playback
- ⏭️ Skip songs
- 🔀 Shuffle queue
- 📜 View queue
- ⏹️ Stop and clear queue

## Prerequisites

1. **Python 3.10 or higher**
2. **FFmpeg** - Required for audio processing
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Add FFmpeg to your system PATH

## Setup

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to "Bot" section on the left
4. Click "Reset Token" to get your bot token
5. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
   - Voice States Intent
6. Go to "OAuth2" > "URL Generator"
   - Select `bot` scope
   - Select `Connect to voice` and `Use slash commands` permissions
   - Copy the generated URL and invite the bot to your server

### 2. Configure the Bot

1. Open `config.py` in a text editor
2. Replace `YOUR_BOT_TOKEN_HERE` with your actual bot token:

```python
DISCORD_BOT_TOKEN = "your_actual_token_here"
```

### 3. Install Dependencies

Open a terminal in the project directory and run:

```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg

**Windows:**
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract the zip file
3. Add the `bin` folder to your system PATH
4. Restart your terminal

**Verify FFmpeg installation:**
```bash
ffmpeg -version
```

## Running the Bot

```bash
python main.py
```

You should see:
```
2024-xxx-xx ... - INFO - Musica Bot is ready!
```

## Commands

| Command | Description |
|---------|-------------|
| `/play <url>` | Play a YouTube video or playlist |
| `/pause` | Pause the current song |
| `/resume` | Resume the paused song |
| `/skip` | Skip to the next song |
| `/stop` | Stop playback and clear the queue |
| `/queue` | View the current queue |
| `/nowplaying` | See what's currently playing |
| `/shuffle` | Shuffle the queue |

## Usage Example

1. Join a voice channel in your Discord server
2. Use `/play https://www.youtube.com/watch?v=...` to start playing
3. Use other commands to control playback

## Troubleshooting

### Bot not responding to commands?
- Make sure the bot has permission to use slash commands
- Try restarting the bot

### Voice connection issues?
- Make sure FFmpeg is installed and in your PATH
- Check that the bot has "Connect to Voice" permissions

### YouTube links not working?
- Make sure you're using full YouTube URLs (youtube.com, not youtu.be)
- Some videos may be age-restricted or unavailable

## License

MIT License
