import os
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, CallbackQueryHandler
)

# --- Configuration ---
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required.")

ADMIN_ID = 6312622799  # Your admin ID

# --- In-Memory Storage (resets on restart) ---
users_db = {}

# --- Utility functions ---
def clean_series_name(name: str) -> str:
    name = re.sub(r'[\._]+', ' ', name)
    name = re.sub(r'\s{2,}', ' ', name).strip()
    return name

def detect_episode_info(filename: str):
    patterns = [
        r'[Ss](\d+)[Ee](\d+)',
        r'(\d+)[xX](\d+)',
        r'[Ss]eason\D*(\d+).*?[Ee]pisode\D*(\d+)',
        r'[Ee][Pp]?[.\s_-]*(\d{1,3})',
        r'\b(\d{1,2})(\d{2})\b'
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

def normalize_original_name(name: str) -> str:
    name = re.sub(r'\b(720p|1080p|2160p|4k|WEBRip|WEB|BluRay|x264|x265|h264|HEVC|AAC|DTS|HDRip|BRRip|PROPER|REPACK)\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[-._]{1,}', ' ', name)
    name = re.sub(r'\s{2,}', ' ', name).strip()
    return name

# --- Command handlers ---
def start(update: Update, context: CallbackContext):
    text = ("🎬 *Welcome to Video AutoRename Bot (Render Edition)*\n\n"
            "⚠️ Note: Settings are NOT saved after bot restart.\n"
            "Use /setseries and /setseason, then send videos for renaming.\n\n"
            "Commands: /help /setseries /setseason /settemplate /settings /clear")
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

def help_command(update: Update, context: CallbackContext):
    text = ("*Commands*\n"
            "/start - Start bot\n"
            "/help - This message\n"
            "/setseries <name> - Set series name\n"
            "/setseason <number> - Set season number\n"
            "/settemplate <template> - Set naming template\n"
            "/settings - View current settings\n"
            "/clear - Clear your settings")
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

def ensure_user(uid):
    if uid not in users_db:
        users_db[uid] = {"series": None, "season": None, "template": None, "episode_counter": 1}
    return users_db[uid]

def setseries(update: Update, context: CallbackContext):
    user = update.effective_user
    if not context.args:
        update.message.reply_text("Usage: /setseries <series name>")
        return
    name = " ".join(context.args)
    name = clean_series_name(name)
    u = ensure_user(user.id)
    u["series"] = name
    u["episode_counter"] = 1
    update.message.reply_text(f"✅ Series set to: *{name}*", parse_mode=ParseMode.MARKDOWN)

def setseason(update: Update, context: CallbackContext):
    user = update.effective_user
    if not context.args:
        update.message.reply_text("Usage: /setseason <number>")
        return
    try:
        season = int(context.args[0])
    except:
        update.message.reply_text("❌ Please enter a valid season number.")
        return
    u = ensure_user(user.id)
    u["season"] = season
    u["episode_counter"] = 1
    update.message.reply_text(f"✅ Season set to: *{season}*", parse_mode=ParseMode.MARKDOWN)

def settemplate(update: Update, context: CallbackContext):
    user = update.effective_user
    if not context.args:
        update.message.reply_text("Usage: /settemplate <template>")
        return
    templ = " ".join(context.args)
    u = ensure_user(update.effective_user.id)
    u["template"] = templ
    update.message.reply_text(f"✅ Template updated:\n`{templ}`", parse_mode=ParseMode.MARKDOWN)

def settings(update: Update, context: CallbackContext):
    u = ensure_user(update.effective_user.id)
    text = (f"⚙️ *Your Settings (Temporary)*\n\n"
            f"📺 Series: `{u.get('series') or 'Not set'}`\n"
            f"🎬 Season: `{u.get('season') or 'Not set'}`\n"
            f"📝 Template: `{u.get('template') or '{series} S{season:02d}E{episode:02d}{ext}'}`")
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

def clear(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if uid in users_db:
        del users_db[uid]
    update.message.reply_text("✅ Your settings have been cleared.")

def handle_video(update: Update, context: CallbackContext):
    user = update.effective_user
    video = update.message.video
    if not video:
        update.message.reply_text("❌ Please send a video file.")
        return

    # 500MB limit for safety
    if video.file_size > 500 * 1024 * 1024:
        update.message.reply_text("❌ File too large (>500MB). Please send smaller files.")
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
        update.message.reply_text("⚠️ Season not set. Use /setseason <number>.")
        return

    series = u.get("series") or clean_series_name(name_part)
    template = u.get("template")
    new_filename = generate_filename(series, season, episode, ext, template)

    # Send processing message
    status_msg = update.message.reply_text("⏳ Processing video... This may take a moment.")

    try:
        # Download file
        file = context.bot.get_file(video.file_id)
        temp_path = f"temp_{video.file_id}{ext}"
        file.download(temp_path)

        # Rename by moving to new filename
        renamed_path = new_filename
        os.rename(temp_path, renamed_path)

        # Send renamed file back
        with open(renamed_path, 'rb') as f:
            caption = (f"✅ *Renamed Successfully*\n\n"
                      f"📁 Original: `{original_name}`\n"
                      f"📝 New Name: `{new_filename}`\n"
                      f"Next episode: E{episode + 1:02d}")
            update.message.reply_video(video=f, caption=caption, parse_mode=ParseMode.MARKDOWN, 
                                      timeout=300, supports_streaming=True)

        # Clean up
        os.remove(renamed_path)
        status_msg.delete()

        # Increment counter
        u["episode_counter"] = episode + 1

    except Exception as e:
        status_msg.edit_text(f"❌ Error processing file: {str(e)}")
        # Clean up on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(renamed_path):
            os.remove(renamed_path)

def handle_document(update: Update, context: CallbackContext):
    doc = update.message.document
    if not doc.file_name:
        update.message.reply_text("❌ File name missing.")
        return
    ext = os.path.splitext(doc.file_name)[1].lower()
    if ext not in {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'}:
        update.message.reply_text("❌ Only video files are supported.")
        return

    if doc.file_size > 500 * 1024 * 1024:
        update.message.reply_text("❌ File too large (>500MB).")
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
        update.message.reply_text("⚠️ Season not set. Use /setseason <number>.")
        return

    series = u.get("series") or clean_series_name(name_part)
    template = u.get("template")
    new_filename = generate_filename(series, season, episode, ext, template)

    # Send processing message
    status_msg = update.message.reply_text("⏳ Processing video... This may take a moment.")

    try:
        # Download file
        file = context.bot.get_file(doc.file_id)
        temp_path = f"temp_{doc.file_id}{ext}"
        file.download(temp_path)

        # Rename
        renamed_path = new_filename
        os.rename(temp_path, renamed_path)

        # Send renamed file back
        with open(renamed_path, 'rb') as f:
            caption = (f"✅ *Renamed Successfully*\n\n"
                      f"📁 Original: `{original_name}`\n"
                      f"📝 New Name: `{new_filename}`\n"
                      f"Next episode: E{episode + 1:02d}")
            update.message.reply_document(document=f, caption=caption, parse_mode=ParseMode.MARKDOWN, 
                                         timeout=300, filename=new_filename)

        # Clean up
        os.remove(renamed_path)
        status_msg.delete()

        # Increment counter
        u["episode_counter"] = episode + 1

    except Exception as e:
        status_msg.edit_text(f"❌ Error processing file: {str(e)}")
        # Clean up on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(renamed_path):
            os.remove(renamed_path)

def error_handler(update: Update, context: CallbackContext):
    pass  # Silent error handling

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("setseries", setseries, pass_args=True))
    dp.add_handler(CommandHandler("setseason", setseason, pass_args=True))
    dp.add_handler(CommandHandler("settemplate", settemplate, pass_args=True))
    dp.add_handler(CommandHandler("settings", settings))
    dp.add_handler(CommandHandler("clear", clear))

    dp.add_handler(MessageHandler(Filters.video, handle_video))
    dp.add_handler(MessageHandler(Filters.document, handle_document))

    dp.add_error_handler(error_handler)

    print("✅ Bot started successfully on Render!")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
