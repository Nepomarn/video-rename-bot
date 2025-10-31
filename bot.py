import os
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Configuration ---
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required.")

ADMIN_ID = 6312622799  # Your admin ID

# --- In-Memory Storage (resets on restart) ---
users_db = {}

# --- Utility functions ---
def clean_series_name(name: str) -> str:
    name = re.sub(r'[\\_]+', ' ', name)
    name = re.sub(r'\\s{2,}', ' ', name).strip()
    return name

def detect_episode_info(filename: str):
    patterns = [
        r'[Ss](\\d+)[Ee](\\d+)',
        r'(\\d+)[xX](\\d+)',
        r'[Ss]eason\\D*(\\d+).*?[Ee]pisode\\D*(\\d+)',
        r'[Ee][Pp]?[.\\s_-]*(\\d{1,3})',
        r'\\b(\\d{1,2})(\\d{2})\\b'
    ]
    for pat in patterns:
        m = re.search(pat, filename, re.IGNORECASE)
        if m:
            if len(m.groups()) >= 2:
                try:
                    s = int(m.group(1))
                    e = int(m.group(2))
                    return s, e
                except:
                    continue
            elif len(m.groups()) == 1:
                try:
                    return None, int(m.group(1))
                except:
                    continue
    return None, None

def generate_filename(series, season, episode, ext, template=None):
    if template is None:
        template = "{series} S{season:02d}E{episode:02d}{ext}"
    return template.format(series=series, season=season or 0, episode=episode or 0, ext=ext)

def ensure_user(uid):
    if uid not in users_db:
        users_db[uid] = {"series": None, "season": None, "template": None, "episode_counter": 1}
    return users_db[uid]

# --- Command handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ("馃幀 *Welcome to Video AutoRename Bot \\(Render Edition\\)*\\n\\n"
            "鈿狅笍 Note: Settings are NOT saved after bot restart\\.\\n"
            "Use /setseries and /setseason, then send videos for renaming\\.\\n\\n"
            "Commands: /help /setseries /setseason /settemplate /settings /clear")
    await update.message.reply_text(text, parse_mode='MarkdownV2')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ("*Commands*\\n"
            "/start \\- Start bot\\n"
            "/help \\- This message\\n"
            "/setseries <name> \\- Set series name\\n"
            "/setseason <number> \\- Set season number\\n"
            "/settemplate <template> \\- Set naming template\\n"
            "/settings \\- View current settings\\n"
            "/clear \\- Clear your settings")
    await update.message.reply_text(text, parse_mode='MarkdownV2')

async def setseries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("Usage: /setseries <series name>")
        return
    name = " ".join(context.args)
    name = clean_series_name(name)
    u = ensure_user(user.id)
    u["series"] = name
    u["episode_counter"] = 1
    await update.message.reply_text(f"鉁� Series set to: *{name}*", parse_mode='MarkdownV2')

async def setseason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("Usage: /setseason <number>")
        return
    try:
        season = int(context.args[0])
    except:
        await update.message.reply_text("鉂� Please enter a valid season number.")
        return
    u = ensure_user(user.id)
    u["season"] = season
    u["episode_counter"] = 1
    await update.message.reply_text(f"鉁� Season set to: *{season}*", parse_mode='MarkdownV2')

async def settemplate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("Usage: /settemplate <template>")
        return
    templ = " ".join(context.args)
    u = ensure_user(user.id)
    u["template"] = templ
    await update.message.reply_text(f"鉁� Template updated:\\n`{templ}`", parse_mode='MarkdownV2')

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = ensure_user(update.effective_user.id)
    series = u.get('series') or 'Not set'
    season = u.get('season') or 'Not set'
    template = u.get('template') or '{series} S{season:02d}E{episode:02d}{ext}'
    text = (f"鈿欙笍 *Your Settings \\(Temporary\\)*\\n\\n"
            f"馃摵 Series: `{series}`\\n"
            f"馃幀 Season: `{season}`\\n"
            f"馃摑 Template: `{template}`")
    await update.message.reply_text(text, parse_mode='MarkdownV2')

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in users_db:
        del users_db[uid]
    await update.message.reply_text("鉁� Your settings have been cleared.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    video = update.message.video
    if not video:
        await update.message.reply_text("鉂� Please send a video file.")
        return

    # 500MB limit for safety
    if video.file_size > 500 * 1024 * 1024:
        await update.message.reply_text("鉂� File too large (>500MB). Please send smaller files.")
        return

    u = ensure_user(user.id)
    original_name = video.file_name or f"video_{video.file_id}.mp4"
    name_part, ext = os.path.splitext(original_name)
    if not ext:
        ext = ".mp4"

    s_detected, e_detected = detect_episode_info(original_name)
    episode = e_detected or u.get("episode_counter", 1)
    season = u.get("season")
    if season is None and s_detected:
        season = s_detected
    if season is None:
        await update.message.reply_text("鈿狅笍 Season not set. Use /setseason <number>.")
        return

    series = u.get("series") or clean_series_name(name_part)
    template = u.get("template")
    new_filename = generate_filename(series, season, episode, ext, template)

    # Send processing message
    status_msg = await update.message.reply_text("鈴� Processing video... This may take a moment.")

    try:
        # Download file
        file = await context.bot.get_file(video.file_id)
        temp_path = f"temp_{video.file_id}{ext}"
        await file.download_to_drive(temp_path)

        # Rename by moving to new filename
        renamed_path = new_filename
        os.rename(temp_path, renamed_path)

        # Send renamed file back
        with open(renamed_path, 'rb') as f:
            caption = (f"鉁� *Renamed Successfully*\\n\\n"
                      f"馃搧 Original: `{original_name}`\\n"
                      f"馃摑 New Name: `{new_filename}`\\n"
                      f"Next episode: E{episode + 1:02d}")
            await update.message.reply_video(video=f, caption=caption, parse_mode='MarkdownV2',
                                           write_timeout=300, read_timeout=300)

        # Clean up
        os.remove(renamed_path)
        await status_msg.delete()

        # Increment counter
        u["episode_counter"] = episode + 1

    except Exception as e:
        await status_msg.edit_text(f"鉂� Error processing file: {str(e)}")
        # Clean up on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(renamed_path):
            os.remove(renamed_path)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name:
        await update.message.reply_text("鉂� File name missing.")
        return
    ext = os.path.splitext(doc.file_name)[1].lower()
    if ext not in {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}:
        await update.message.reply_text("鉂� Only video files are supported.")
        return

    if doc.file_size > 500 * 1024 * 1024:
        await update.message.reply_text("鉂� File too large (>500MB).")
        return

    u = ensure_user(update.effective_user.id)
    original_name = doc.file_name
    name_part, ext = os.path.splitext(original_name)
    if not ext:
        ext = ".mp4"

    s_detected, e_detected = detect_episode_info(original_name)
    episode = e_detected or u.get("episode_counter", 1)
    season = u.get("season")
    if season is None and s_detected:
        season = s_detected
    if season is None:
        await update.message.reply_text("鈿狅笍 Season not set. Use /setseason <number>.")
        return

    series = u.get("series") or clean_series_name(name_part)
    template = u.get("template")
    new_filename = generate_filename(series, season, episode, ext, template)

    # Send processing message
    status_msg = await update.message.reply_text("鈴� Processing video... This may take a moment.")

    try:
        # Download file
        file = await context.bot.get_file(doc.file_id)
        temp_path = f"temp_{doc.file_id}{ext}"
        await file.download_to_drive(temp_path)

        # Rename
        renamed_path = new_filename
        os.rename(temp_path, renamed_path)

        # Send renamed file back
        with open(renamed_path, 'rb') as f:
            caption = (f"鉁� *Renamed Successfully*\\n\\n"
                      f"馃搧 Original: `{original_name}`\\n"
                      f"馃摑 New Name: `{new_filename}`\\n"
                      f"Next episode: E{episode + 1:02d}")
            await update.message.reply_document(document=f, caption=caption, parse_mode='MarkdownV2',
                                              write_timeout=300, read_timeout=300, filename=new_filename)

        # Clean up
        os.remove(renamed_path)
        await status_msg.delete()

        # Increment counter
        u["episode_counter"] = episode + 1

    except Exception as e:
        await status_msg.edit_text(f"鉂� Error processing file: {str(e)}")
        # Clean up on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(renamed_path):
            os.remove(renamed_path)

def main():
    # Create application
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("setseries", setseries))
    application.add_handler(CommandHandler("setseason", setseason))
    application.add_handler(CommandHandler("settemplate", settemplate))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("clear", clear))

    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("鉁� Bot started successfully on Render!")

    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
