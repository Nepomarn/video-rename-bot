# Video AutoRename Telegram Bot (Render Edition)

A Telegram bot that automatically renames video files based on series name, season, and episode numbers. Designed for deployment on Render's free tier.

## Features

- 🎬 Automatic episode detection from filenames
- 📝 Custom naming templates
- 🔄 Sequential episode numbering
- 📁 Support for multiple video formats (MP4, MKV, AVI, MOV, WMV, FLV, WEBM)
- ✅ Actually renames and returns files (unlike limited hosting platforms)

## Deployment on Render

### Step 1: Push to GitHub

1. Create a new repository on GitHub
2. Upload all files from this folder:
   - `bot.py`
   - `requirements.txt`
   - `runtime.txt`
   - `.gitignore`
   - `README.md`

### Step 2: Create Render Web Service

1. Go to [render.com](https://render.com) and sign up/login
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `video-rename-bot` (or your choice)
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: Free

### Step 3: Set Environment Variable

1. In Render dashboard, go to **"Environment"** section
2. Add variable:
   - **Key**: `BOT_TOKEN`
   - **Value**: Your bot token from [@BotFather](https://t.me/botfather)

### Step 4: Deploy

Click **"Create Web Service"** and wait 5-15 minutes for deployment.

## Bot Commands

- `/start` - Start the bot
- `/help` - Show help message
- `/setseries <name>` - Set series name (e.g., `/setseries Vikings`)
- `/setseason <number>` - Set season number (e.g., `/setseason 1`)
- `/settemplate <template>` - Custom naming template
- `/settings` - View current settings
- `/clear` - Clear your settings

## Usage Example

1. Set series: `/setseries Vikings`
2. Set season: `/setseason 1`
3. Send video file
4. Bot downloads, renames, and sends back: `Vikings S01E01.mkv`

## Template Variables

Default template: `{series} S{season:02d}E{episode:02d}{ext}`

Available variables:
- `{series}` - Series name
- `{season}` - Season number
- `{episode}` - Episode number
- `{ext}` - File extension

Example custom template:
```
/settemplate {series} - {season}x{episode:02d}{ext}
```
Result: `Vikings - 1x01.mkv`

## Limitations

- ⚠️ Settings reset on bot restart (no database)
- ⚠️ 500MB file size limit
- ⚠️ 15-minute sleep after inactivity (free tier)
- ⚠️ Bot takes 50+ seconds to wake up from sleep

## Notes

- Temporary files are cleaned up automatically
- Multiple video formats supported
- Episode numbers auto-increment after each file
