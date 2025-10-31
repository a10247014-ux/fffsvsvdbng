import asyncio
import os
import logging
import re
import aiohttp
import time
import unicodedata
import shutil
import random
from urllib.parse import quote
from pyrogram import Client, filters, enums
from pyrogram.handlers import MessageHandler
from pyrogram.enums import ChatType, ChatAction, UserStatus
from pyrogram.errors import (
    FloodWait, SessionPasswordNeeded, PhoneCodeInvalid,
    PasswordHashInvalid, PhoneNumberInvalid, PhoneCodeExpired, UserDeactivated, AuthKeyUnregistered,
    ReactionInvalid, MessageIdInvalid, MessageNotModified, PeerIdInvalid, UserNotParticipant, PhotoCropSizeSmall
)
try:
    from pyrogram.raw import functions
except ImportError:
    logging.warning("Could not import 'pyrogram.raw.functions'. Anti-login feature might not work.")
    functions = None

from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request, render_template_string, redirect, session, url_for
from threading import Thread
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pytube import YouTube
import certifi

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')

# =======================================================
# ⚠️ Main Settings (Enter your API_ID and API_HASH here)
# =======================================================
API_ID = 28190856
API_HASH = "6b9b5309c2a211b526c6ddad6eabb521"

# --- Database Setup (MongoDB) ---
MONGO_URI = "mongodb+srv://CFNBEFBGWFB:hdhbedfefbegh@cluster0.obohcl3.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
mongo_client = None
sessions_collection = None
if MONGO_URI and "<db_password>" not in MONGO_URI: # Check for placeholder password
    try:
        mongo_client = MongoClient(MONGO_URI, server_api=ServerApi('1'), tlsCAFile=certifi.where())
        mongo_client.admin.command('ping')
        db = mongo_client['telegram_self_bot']
        sessions_collection = db['sessions']
        logging.info("Successfully connected to MongoDB!")
    except Exception as e:
        logging.error(f"Could not connect to MongoDB: {e}")
        mongo_client = None
        sessions_collection = None
else:
    logging.warning("MONGO_URI is not configured correctly or contains placeholder. Session persistence will be disabled.")

# --- Application Variables ---
TEHRAN_TIMEZONE = ZoneInfo("Asia/Tehran")
app_flask = Flask(__name__)
app_flask.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

# --- Clock Font Dictionaries ---
# Corrected font mappings for Fraktur and Gothic to use numeric characters or known stylized number sets.
# Removed entries that map to non-numeric letters to avoid confusion.
FONT_STYLES = {
    "cursive":      {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'V𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "stylized":     {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵',':':':'},
    "doublestruck": {'0':'𝟘','1':'𝟙','2':'𝟚','3':'𝟛','4':'𝟜','5':'𝟝','6':'𝟞','7':'𝟟','8':'𝟠','9':'𝟡',':':':'},
    "monospace":    {'0':'𝟶','1':'𝟷','2':'𝟸','3':'𝟹','4':'𝟺','5':'𝟻','6':'𝟼','7':'𝟽','8':'𝟾','9':'𝟿',':':':'},
    "normal":       {'0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9',':':':'},
    "circled":      {'0':'⓪','1':'①','2':'②','3':'③','4':'④','5':'⑤','6':'⑥','7':'⑦','8':'⑧','9':'⑨',':':'∶'},
    "fullwidth":    {'0':'０','1':'１','2':'２','3':'３','4':'４','5':'５','6':'۶','7':'７','8':'８','9':'９',':':'：'},
    "sans_normal":  {'0':'𝟢','1':'𝟣','2':'𝟤','3':'𝟥','4':'𝟦','5':'𝟧','6':'𝟨','7':'𝟩','8':'𝟪','9':'𝟫',':':'∶'},
    "negative_circled": {'0':'⓿','1':'❶','2':'❷','3':'❸','4':'❹','5':'❺','6':'❻','7':'❼','8':'❽','9':'❾',':':'∶'},
    "parenthesized": {'0':'🄀','1':'⑴','2':'⑵','3':'⑶','4':'⑷','5':'⑸','6':'⑹','7':'⑺','8':'⑻','9':'⑼',':':'∶'},
    "dot":          {'0':'🄀','1':'⒈','2':'⒉','3':'⒊','4':'⒋','5':'⒌','6':'⒍','7':'⒎','8':'⒏','9':'⒐',':':'∶'},
    "thai":         {'0':'๐','1':'๑','2':'๒','3':'๓','4':'๔','5':'๕','6':'๖','7':'๗','8':'๘','9':'๙',':':' : '},
    "devanagari":   {'0':'०','1':'१','2':'२','3':'३','4':'४','5':'५','6':'६','7':'७','8':'८','9':'९',':':' : '},
    "arabic_indic": {'0':'٠','1':'١','2':'٢','3':'٣','4':'٤','5':'٥','6':'٦','7':'٧','8':'٨','9':'٩',':':' : '},
    "keycap":       {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣',':':':'},
    "superscript":  {'0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹',':':':'},
    "subscript":    {'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉',':':':'},
    "tibetan":      {'0':'༠','1':'༡','2':'༢','3':'༣','4':'༤','5':'༥','6':'༦','7':'༧','8':'༨','9':'༩',':':' : '},
    "bengali":      {'0':'০','1':'১','2':'২','3':'৩','4':'৪','5':'۵','6':'৬','7':'৭','8':'۸','9':'৯',':':' : '},
    "gujarati":     {'0':'૦','1':'૧','2':'૨','3':'૩','4':'૪','5':'૫','6':'૬','7':'૭','8':'૮','9':'૯',':':' : '},
    "mongolian":    {'0':'᠐','1':'᠑','2':'᠒','3':'᠓','4':'᠔','5':'᠕','6':'᠖','7':'᠗','8':'᠘','9':'᠙',':':' : '},
    "lao":          {'0':'໐','1':'໑','2':'໒','3':'໓','4':'໔','5':'໕','6':'໖','7':'໗','8':'໘','9':'໙',':':' : '},
    "bold_fraktur": {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'}, # Using Math Bold for "bold_fraktur" for better numeric representation.
    "script":       {'0':'𝟢','1':'𝟣','2':'𝟤','3':'𝟥','4':'𝟦','5':'𝟧','6':'𝟨','7':'𝟩','8':'𝟪','9':'𝟫',':':':'},
    "bold_script":  {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "squared":      {'0':'🄀','1':'🄁','2':'🄂','3':'🄃','4':'🄄','5':'🄅','6':'🄆','7':'🄇','8':'🄈','9':'🄉',':':'∶'},
    "negative_squared": {'0':'🅀','1':'🅁','2':'🅂','3':'🅃','4':'🅄','5':'🅅','6':'🅆','7':'🅇','8':'🅈','9':'🅉',':':'∶'},
    "roman":        {'0':'⓪','1':'Ⅰ','2':'Ⅱ','3':'Ⅲ','4':'Ⅳ','5':'Ⅴ','6':'Ⅵ','7':'Ⅶ','8':'Ⅷ','9':'Ⅸ',':':':'},
    "small_caps":   {'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉',':':':'},
    "oldstyle":     {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "inverted":     {'0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'9','7':'7','8':'8','9':'6',':':':'},
    "mirror":       {'0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'9','7':'7','8':'8','9':'6',':':':'},
    "strike":       {'0':'0̶','1':'1̶','2':'2̶','3':'3̶','4':'4̶','5':'5̶','6':'6̶','7':'7̶','8':'8̶','9':'9̶',':':':'},
    "bubble":       {'0':'⓪','1':'①','2':'②','3':'③','4':'④','5':'⑤','6':'⑥','7':'⑦','8':'⑧','9':'⑨',':':'∶'},
    "fancy1":       {'0':'０','1':'１','2':'２','3':'３','4':'４','5':'５','6':'６','7':'７','8':'８','9':'９',':':'：'},
    "fancy2":       {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵',':':':'},
    "fancy3":       {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "fancy4":       {'0':'⓿','1':'❶','2':'❷','3':'❸','4':'❹','5':'❺','6':'❻','7':'❼','8':'❽','9':'❾',':':'∶'},
    # Additional cool fonts
    "ethiopic":     {'0':'፩','1':'፪','2':'፫','3':'፬','4':'፭','5':'፮','6':'፯','7':'፰','8':'፱','9':'፲',':':' : '},  # Approximate Ethiopic numbers, 10 is actually X.
    "runic":        {'0':'ᛟ','1':'ᛁ','2':'ᛒ','3':'ᛏ','4':'ᚠ','5':'ᚢ','6':'ᛋ','7':'ᚷ','8':'ᚺ','9':'ᛉ',':':' : '},  # Approximate runic, these are not direct numeric representations
    "math_bold":    {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "math_italic":  {'0':'𝟢','1':'𝟣','2':'𝟤','3':'𝟥','4':'𝟦','5':'𝟧','6':'𝟨','7':'𝟩','8':'𝟪','9':'𝟫',':':':'},
    "math_sans":    {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵',':':':'},
    "math_monospace": {'0':'𝟶','1':'𝟷','2':'𝟸','3':'𝟹','4':'𝟺','5':'𝟻','6':'𝟼','7':'𝟽','8':'𝟾','9':'𝟿',':':':'},
    "math_double":  {'0':'𝟘','1':'𝟙','2':'𝟚','3':'𝟛','4':'𝟜','5':'𝟝','6':'𝟞','7':'𝟟','8':'𝟠','9':'𝟡',':':':'},
    "japanese":     {'0':'零','1':'壱','2':'弐','3':'参','4':'四','5':'伍','6':'陸','7':'漆','8':'捌','9':'玖',':':' : '},  # Kanji numbers
    "emoji":        {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣',':':':'},
    "shadow":       {'0':'🅾','1':'🅰','2':'🅱','3':'🅲','4':'🅳','5':'🅴','6':'🅵','7':'G','8':'🅷','9':'🅸',':':' : '},  # Approximate, some chars are letters
}
FONT_KEYS_ORDER = list(FONT_STYLES.keys())
FONT_DISPLAY_NAMES = {
    "cursive": "کشیده", "stylized": "فانتزی", "doublestruck": "توخالی",
    "monospace": "کامپیوتری", "normal": "ساده", "circled": "دایره‌ای", "fullwidth": "پهن",
    "sans_normal": "ساده ۲", "negative_circled": "دایره‌ای معکوس",
    "parenthesized": "پرانتزی", "dot": "نقطه‌دار", "thai": "تایلندی", "devanagari": "هندی", "arabic_indic": "عربی",
    "keycap": "کیکپ", "superscript": "بالانویس", "subscript": "زیرنویس", "tibetan": "تبتی", "bengali": "بنگالی",
    "gujarati": "گجراتی", "mongolian": "مغولی", "lao": "لائوسی",
    "bold_fraktur": "فراکتور (بولد ریاضی)", "script": "اسکریپت", "bold_script": "اسکریپت بولد", "squared": "مربعی", "negative_squared": "مربعی معکوس", "roman": "رومی", "small_caps": "کوچک کپس", "oldstyle": "قدیمی", "inverted": "وارونه", "mirror": "آینه‌ای", "strike": "خط خورده", "bubble": "حبابی", "fancy1": "فانتزی ۱", "fancy2": "فانتزی ۲", "fancy3": "فانتزی ۳", "fancy4": "فانتزی ۴",
    "ethiopic": "اتیوپیک", "runic": "رونیک", "math_bold": "ریاضی بولد", "math_italic": "ریاضی ایتالیک", "math_sans": "ریاضی سنس", "math_monospace": "ریاضی مونوسپیس", "math_double": "ریاضی دوبل", "japanese": "ژاپنی", "emoji": "ایموجی", "shadow": "سایه‌دار",
}
# Pre-calculate all unique characters used in clock fonts for robust regex matching
ALL_CLOCK_CHARS = "".join(set(char for font in FONT_STYLES.values() for char in font.values()))
CLOCK_CHARS_REGEX_CLASS = f"[{re.escape(ALL_CLOCK_CHARS)}]" # Used to find/replace existing clocks

# --- Feature Variables ---
ENEMY_REPLIES = {}  # {user_id: list of replies}
FRIEND_REPLIES = {} # {user_id: list of replies}
ENEMY_LIST = {} # {user_id: set of enemy user_ids}
FRIEND_LIST = {}    # {user_id: set of friend user_ids}
ENEMY_ACTIVE = {}   # {user_id: bool}
FRIEND_ACTIVE = {}  # {user_id: bool}
SECRETARY_MODE_STATUS = {}
CUSTOM_SECRETARY_MESSAGES = {}
USERS_REPLIED_IN_SECRETARY = {} # {user_id: {target_user_id: "YYYY-MM-DD"}} for daily reset
MUTED_USERS = {}    # {user_id: set of (sender_id, chat_id)}
USER_FONT_CHOICES = {}
CLOCK_STATUS = {}
TIME_BIO_STATUS = {}      # NEW: For TimeBio (time in bio)
DATE_STATUS = {}          # NEW: For enabling date globally (affects name & bio if active)
BOLD_MODE_STATUS = {}
ITALIC_MODE_STATUS = {}   # NEW: For Italic format
UNDERLINE_MODE_STATUS = {}# NEW: For Underline format
LINK_MODE_STATUS = {}     # NEW: For Link format
AUTO_SEEN_STATUS = {}
AUTO_REACTION_TARGETS = {}  # {user_id: {target_user_id: emoji}}
AUTO_TRANSLATE_TARGET = {}  # {user_id: lang_code}
ANTI_LOGIN_STATUS = {}
COPY_MODE_STATUS = {}
ORIGINAL_PROFILE_DATA = {}
PV_LOCK_STATUS = {}
# Statuses (seen, typing, etc.)
TYPING_MODE_STATUS = {}
PLAYING_MODE_STATUS = {}
RECORD_VOICE_STATUS = {}
UPLOAD_PHOTO_STATUS = {}
WATCH_GIF_STATUS = {}
# NEW Statuses
RECORD_VIDEO_STATUS = {}
CHOOSE_STICKER_STATUS = {}
UPLOAD_VIDEO_STATUS = {}
UPLOAD_DOCUMENT_STATUS = {}
UPLOAD_AUDIO_STATUS = {}
SPEAKING_STATUS = {}


# --- Task Management ---
EVENT_LOOP = asyncio.new_event_loop()
ACTIVE_CLIENTS = {} # Temporary clients for login flow
ACTIVE_BOTS = {}    # Main clients with active self-bot features

DEFAULT_SECRETARY_MESSAGE = "سلام! منشی هستم. پیامتون رو دیدم، بعدا جواب می‌دم."

# Updated REGEX to include all new commands
# Added (?: \d+)? for optional number in 'حذف' and 'حذف متن دشمن/دوست'
# Added (?: \d+)? for optional interval in 'تکرار'
# Changed '.*' to '(.*)' in some regex for capturing group
COMMAND_REGEX = r"^(تایپ روشن|تایپ خاموش|بازی روشن|بازی خاموش|ضبط ویس روشن|ضبط ویس خاموش|عکس روشن|عکس خاموش|گیف روشن|گیف خاموش|ترجمه [a-z]{2}(?:-[a-z]{2})?|ترجمه خاموش|چینی روشن|چینی خاموش|روسی روشن|روسی خاموش|انگلیسی روشن|انگلیسی خاموش|بولد روشن|بولد خاموش|سین روشن|سین خاموش|ساعت روشن|ساعت خاموش|بیو ساعت روشن|بیو ساعت خاموش|تاریخ روشن|تاریخ خاموش|فونت|فونت \d+|منشی روشن|منشی خاموش|منشی متن(?: |$)(.*)|انتی لوگین روشن|انتی لوگین خاموش|پیوی قفل|پیوی باز|ذخیره|تکرار \d+(?: \d+)?|حذف همه|حذف(?: \d+)?|دشمن روشن|دشمن خاموش|تنظیم دشمن|حذف دشمن|پاکسازی لیست دشمن|لیست دشمن|لیست متن دشمن|تنظیم متن دشمن (.*)|حذف متن دشمن(?: \d+)?|دوست روشن|دوست خاموش|تنظیم دوست|حذف دوست|پاکسازی لیست دوست|لیست دوست|لیست متن دوست|تنظیم متن دوست (.*)|حذف متن دوست(?: \d+)?|بلاک روشن|بلاک خاموش|سکوت روشن|سکوت خاموش|ریاکشن (.*)|ریاکشن خاموش|کپی روشن|کپی خاموش|تاس|تاس \d+|بولینگ|راهنما|ترجمه|ایتالیک روشن|ایتالیک خاموش|زیرخط روشن|زیرخط خاموش|لینک روشن|لینک خاموش|ضبط ویدیو روشن|ضبط ویدیو خاموش|استیکر روشن|استیکر خاموش|آپلود ویدیو روشن|آپلود ویدیو خاموش|آپلود فایل روشن|آپلود فایل خاموش|آپلود صدا روشن|آپلود صدا خاموش|صحبت روشن|صحبت خاموش|تنظیم اسم|تنظیم بیو|تنظیم پروفایل|مربع|قلب|قلب بزرگ|بکیرم|به کیرم|مکعب|لودینگ|Loading|ربات|bot|!YouTube (.*)|!check (.*)|ویس (.*)|پارت (.*))$"


# --- Main Bot Functions ---
def stylize_time(time_str: str, style: str) -> str:
    """Applies a chosen font style to time string (HH:MM)."""
    font_map = FONT_STYLES.get(style, FONT_STYLES["stylized"])
    return ''.join(font_map.get(char, char) for char in time_str)

def stylize_date(date_str: str, style: str = "normal") -> str:
    """Applies a chosen font style to date string (DD/MM/YYYY)."""
    # Use a simpler/smaller font for date by default or specified (e.g., 'normal')
    font_map = FONT_STYLES.get(style, FONT_STYLES["normal"]) # Default to normal for dates
    return ''.join(font_map.get(char, char) for char in date_str)


async def update_profile_clock(client: Client, user_id: int):
    log_message = f"Starting clock loop for user_id {user_id}..."
    logging.info(log_message)

    while user_id in ACTIVE_BOTS:
        try:
            # Check if clock is enabled AND copy mode is off
            if CLOCK_STATUS.get(user_id, False) and not COPY_MODE_STATUS.get(user_id, False):
                current_font_style = USER_FONT_CHOICES.get(user_id, 'stylized')
                me = await client.get_me()
                current_name = me.first_name or ""
                
                # Use robust regex to find base name, removing any existing clock/date parts
                # This regex looks for a sequence of clock/date characters at the end of the string
                base_name = re.sub(r'\s+[' + re.escape(ALL_CLOCK_CHARS) + r'/:,\s\d]+$', '', current_name).strip()
                if not base_name: base_name = me.username or f"User_{user_id}"
                
                tehran_time = datetime.now(TEHRAN_TIMEZONE)
                
                # Construct time part
                current_time_str = tehran_time.strftime("%H:%M")
                stylized_time = stylize_time(current_time_str, current_font_style)
                
                # Construct date part if DATE_STATUS is active
                date_part = ""
                if DATE_STATUS.get(user_id, False):
                    current_date_str = tehran_time.strftime("%d/%m/%Y") # Gregorian Date
                    stylized_date_str = stylize_date(current_date_str, "normal") # Fixed 'normal' font for date for smaller, cooler look
                    date_part = f" {stylized_date_str}"
                
                new_name = f"{base_name} {stylized_time}{date_part}"
                
                # Check if name needs updating
                if new_name != current_name:
                    await client.update_profile(first_name=new_name[:64]) # Apply 64 char limit

            # Calculate sleep duration
            now = datetime.now(TEHRAN_TIMEZONE)
            sleep_duration = 60 - now.second + 0.1 # Sleep until the start of the next minute
            await asyncio.sleep(sleep_duration)

        except (UserDeactivated, AuthKeyUnregistered):
            logging.error(f"Clock Task: Session for user_id {user_id} is invalid. Stopping task.")
            # Remove from ACTIVE_BOTS so Flask doesn't try to restart it
            if user_id in ACTIVE_BOTS:
                _, tasks = ACTIVE_BOTS.pop(user_id)
                for task in tasks:
                    if task and not task.done(): task.cancel()
            break
        except FloodWait as e:
            logging.warning(f"Clock Task: Flood wait of {e.value}s for user_id {user_id}.")
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            logging.error(f"An error occurred in clock task for user_id {user_id}: {e}", exc_info=True)
            await asyncio.sleep(60)

    logging.info(f"Clock task for user_id {user_id} has stopped.")

# NEW: Task for TimeBio, including date
async def update_profile_bio(client: Client, user_id: int):
    logging.info(f"Starting TimeBio loop for user_id {user_id}...")

    while user_id in ACTIVE_BOTS:
        try:
            # Check if TimeBio is enabled AND copy mode is off
            if TIME_BIO_STATUS.get(user_id, False) and not COPY_MODE_STATUS.get(user_id, False):
                current_font_style = USER_FONT_CHOICES.get(user_id, 'stylized')
                
                tehran_time = datetime.now(TEHRAN_TIMEZONE)
                
                # Construct time part
                current_time_str = tehran_time.strftime("%H:%M")
                stylized_time = stylize_time(current_time_str, current_font_style)
                
                # Construct date part if DATE_STATUS is active
                date_part = ""
                if DATE_STATUS.get(user_id, False):
                    current_date_str = tehran_time.strftime("%d/%m/%Y") # Gregorian Date
                    stylized_date_str = stylize_date(current_date_str, "normal") # Fixed 'normal' font for date
                    date_part = f" {stylized_date_str}"
                
                new_bio = f"Time Now : {stylized_time}{date_part}"
                
                # We can't easily check the current bio, so we just update it.
                # Telegram's servers will handle if it's the same.
                # Apply 70 char limit for bio
                await client.update_profile(bio=new_bio[:70])

            # Calculate sleep duration (same as clock)
            now = datetime.now(TEHRAN_TIMEZONE)
            sleep_duration = 60 - now.second + 0.1
            await asyncio.sleep(sleep_duration)

        except (UserDeactivated, AuthKeyUnregistered):
            logging.error(f"TimeBio Task: Session for user_id {user_id} is invalid. Stopping task.")
            # Removal from ACTIVE_BOTS handled by main start_bot_instance cleanup
            break
        except FloodWait as e:
            logging.warning(f"TimeBio Task: Flood wait of {e.value}s for user_id {user_id}.")
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            logging.error(f"An error occurred in TimeBio task for user_id {user_id}: {e}", exc_info=True)
            await asyncio.sleep(60)

    logging.info(f"TimeBio task for user_id {user_id} has stopped.")

async def anti_login_task(client: Client, user_id: int):
    logging.info(f"Starting anti-login task for user_id {user_id}...")
    while user_id in ACTIVE_BOTS:
        try:
            if ANTI_LOGIN_STATUS.get(user_id, False) and functions:
                auths = await client.invoke(functions.account.GetAuthorizations())
                # Current session's hash isn't directly exposed by Pyrogram.
                # We rely on the 'current' flag to identify the bot's own session.
                
                current_auth_hash = None
                for auth in auths.authorizations:
                    if auth.current:
                        current_auth_hash = auth.hash
                        break
                
                if current_auth_hash: # If we can identify the current session
                    sessions_terminated = 0
                    for auth in auths.authorizations:
                        # Only terminate if NOT the current session and NOT if the bot itself is failing to mark its session current
                        if not auth.current and auth.hash != current_auth_hash: # Also explicitly check hash
                            try:
                                await client.invoke(functions.account.ResetAuthorization(hash=auth.hash))
                                sessions_terminated += 1
                                logging.info(f"Anti-Login: Terminated session for user {user_id} (Hash: {auth.hash})")
                                device_info = f"{auth.app_name} ({auth.app_version}) on {auth.device_model} ({auth.platform}, {auth.system_version})"
                                location_info = f"IP {auth.ip} in {auth.country}" if auth.ip else "Unknown Location"
                                message_text = (
                                    f"🚨 **هشدار امنیتی: نشست غیرمجاز خاتمه داده شد** 🚨\n\n"
                                    f"یک نشست فعال در حساب شما که با نشست فعلی این ربات مطابقت نداشت، به صورت خودکار خاتمه داده شد.\n\n"
                                    f"**جزئیات نشست خاتمه یافته:**\n"
                                    f"- **دستگاه:** {device_info}\n"
                                    f"- **مکان:** {location_info}\n"
                                    f"- **آخرین فعالیت:** {auth.date_active.strftime('%Y-%m-%d %H:%M:%S') if auth.date_active else 'N/A'}"
                                )
                                await client.send_message("me", message_text)
                            except FloodWait as e_term:
                                logging.warning(f"Anti-Login: Flood wait terminating session {auth.hash} for user {user_id}: {e_term.value}s")
                                await asyncio.sleep(e_term.value + 1)
                            except Exception as e_term_other:
                                logging.error(f"Anti-Login: Failed to terminate session {auth.hash} for user {user_id}: {e_term_other}")
                else:
                    logging.warning(f"Anti-Login: Could not identify current session for user {user_id}. No sessions terminated.")

            await asyncio.sleep(60 * 5) # Check every 5 minutes

        except (UserDeactivated, AuthKeyUnregistered):
            logging.error(f"Anti-Login Task: Session for user_id {user_id} is invalid. Stopping task.")
            break
        except AttributeError:
             logging.error(f"Anti-Login Task: 'pyrogram.raw.functions' module not available for user_id {user_id}. Feature disabled.")
             ANTI_LOGIN_STATUS[user_id] = False # Disable it permanently for this session
             await asyncio.sleep(3600) # Sleep for an hour if raw functions not available
        except Exception as e:
            logging.error(f"An error occurred in anti-login task for user_id {user_id}: {e}", exc_info=True)
            await asyncio.sleep(120)

    logging.info(f"Anti-login task for user_id {user_id} has stopped.")

# UPDATED: status_action_task to include all new statuses
async def status_action_task(client: Client, user_id: int):
    logging.info(f"Starting status action task for user_id {user_id}...")
    chat_ids_cache = []
    last_dialog_fetch_time = 0
    FETCH_INTERVAL = 300 # 5 minutes

    while user_id in ACTIVE_BOTS:
        try:
            # Load all status flags
            typing_mode = TYPING_MODE_STATUS.get(user_id, False)
            playing_mode = PLAYING_MODE_STATUS.get(user_id, False)
            record_voice = RECORD_VOICE_STATUS.get(user_id, False)
            upload_photo = UPLOAD_PHOTO_STATUS.get(user_id, False)
            watch_gif = WATCH_GIF_STATUS.get(user_id, False)
            # New statuses
            record_video = RECORD_VIDEO_STATUS.get(user_id, False)
            choose_sticker = CHOOSE_STICKER_STATUS.get(user_id, False)
            upload_video = UPLOAD_VIDEO_STATUS.get(user_id, False)
            upload_doc = UPLOAD_DOCUMENT_STATUS.get(user_id, False)
            upload_audio = UPLOAD_AUDIO_STATUS.get(user_id, False)
            speaking_mode = SPEAKING_STATUS.get(user_id, False)

            active_statuses = {
                ChatAction.TYPING: typing_mode,
                ChatAction.PLAYING: playing_mode,
                ChatAction.RECORD_AUDIO: record_voice,
                ChatAction.UPLOAD_PHOTO: upload_photo,
                ChatAction.CHOOSE_STICKER: watch_gif or choose_sticker, # Combine watch_gif and choose_sticker for simplicity
                ChatAction.RECORD_VIDEO: record_video,
                ChatAction.UPLOAD_VIDEO: upload_video,
                ChatAction.UPLOAD_DOCUMENT: upload_doc,
                ChatAction.UPLOAD_AUDIO: upload_audio,
                ChatAction.SPEAKING: speaking_mode,
            }

            # Find the first active action
            action_to_send = None
            for action, is_active in active_statuses.items():
                if is_active:
                    action_to_send = action
                    break # Send only one action at a time

            if not action_to_send:
                await asyncio.sleep(5) # No action active, check again soon
                continue

            # Refresh chat list if needed
            now = asyncio.get_event_loop().time()
            if not chat_ids_cache or (now - last_dialog_fetch_time > FETCH_INTERVAL):
                logging.info(f"Status Action: Refreshing dialog list for user_id {user_id}...")
                new_chat_ids = []
                try:
                    async for dialog in client.get_dialogs(limit=75): # Get top 75 dialogs
                        if dialog.chat and dialog.chat.type in [ChatType.PRIVATE, ChatType.GROUP, ChatType.SUPERGROUP]:
                            new_chat_ids.append(dialog.chat.id)
                    chat_ids_cache = new_chat_ids
                    last_dialog_fetch_time = now
                    logging.info(f"Status Action: Found {len(chat_ids_cache)} chats for user {user_id}.")
                except Exception as e_dialog:
                     logging.error(f"Status Action: Error fetching dialogs for user {user_id}: {e_dialog}")
                     chat_ids_cache = [] # Clear cache on error
                     last_dialog_fetch_time = 0 # Force retry soon
                     await asyncio.sleep(60) # Wait before retrying dialog fetch
                     continue

            if not chat_ids_cache:
                logging.warning(f"Status Action: No suitable chats found in cache for user_id {user_id}.")
                await asyncio.sleep(30)
                continue

            # Send action to all cached chats
            for chat_id in chat_ids_cache:
                try:
                    await client.send_chat_action(chat_id, action_to_send)
                except FloodWait as e_action:
                    logging.warning(f"Status Action: Flood wait sending action to chat {chat_id} for user {user_id}. Sleeping {e_action.value}s.")
                    await asyncio.sleep(e_action.value + 1)
                except PeerIdInvalid:
                     logging.warning(f"Status Action: PeerIdInvalid for chat {chat_id}. Removing from cache.")
                     try: chat_ids_cache.remove(chat_id) # Remove invalid chat
                     except ValueError: pass # Ignore if already removed
                except UserNotParticipant:
                     logging.warning(f"Status Action: Not participant in chat {chat_id}. Removing from cache.")
                     try: chat_ids_cache.remove(chat_id)
                     except ValueError: pass
                except Exception:
                    # Ignore other minor errors (like chat deleted, user kicked, etc.)
                    pass

            # Standard sleep interval for sending actions
            await asyncio.sleep(4.5) 

        except (UserDeactivated, AuthKeyUnregistered):
            logging.error(f"Status Action Task: Session for user_id {user_id} is invalid. Stopping task.")
            break
        except Exception as e:
            logging.error(f"An error occurred in status action task for user_id {user_id}: {e}", exc_info=True)
            await asyncio.sleep(60)

    logging.info(f"Status action task for user_id {user_id} has stopped.")

async def translate_text(text: str, target_lang: str = "fa") -> str:
    if not text: return text
    encoded_text = quote(text)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={encoded_text}"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    try:
                        data = await response.json(content_type=None) # Allow non-json content type
                        if isinstance(data, list) and data and isinstance(data[0], list):
                            translated_text = "".join(segment[0] for segment in data[0] if isinstance(segment, list) and segment and isinstance(segment[0], str))
                            return translated_text.strip() if translated_text else text
                        else:
                            logging.warning(f"Unexpected translation response structure: {str(data)[:200]}")
                            return text
                    except (IndexError, TypeError, ValueError, AttributeError, aiohttp.ContentTypeError) as json_err:
                         logging.warning(f"Could not parse translation response: {json_err}. Response: {await response.text()[:200]}")
                         return text
                else:
                    logging.error(f"Translation API request failed: Status {response.status}, Response: {await response.text()[:200]}")
                    return text
    except asyncio.TimeoutError:
         logging.error("Translation request timed out.")
         return text
    except Exception as e:
        logging.error(f"Translation request failed: {e}", exc_info=True)
    return text

# UPDATED: outgoing_message_modifier to include new text formats with HTML
async def outgoing_message_modifier(client, message):
    user_id = client.me.id
    if not message.text or message.text.startswith("/") or message.entities:
        return

    # چک کردن اگر دستور هست، تغییر نده
    if re.match(COMMAND_REGEX, message.text.strip(), re.IGNORECASE):
        return

    original_text = message.text
    modified_text = original_text
    needs_edit = False
    parse_mode = None

    # Apply auto-translation first
    target_lang = AUTO_TRANSLATE_TARGET.get(user_id)
    if target_lang:
        translated = await translate_text(modified_text, target_lang)
        if translated != modified_text:
             modified_text = translated
             needs_edit = True
    
    # Check formatting modes
    is_bold = BOLD_MODE_STATUS.get(user_id, False)
    is_italic = ITALIC_MODE_STATUS.get(user_id, False)
    is_underline = UNDERLINE_MODE_STATUS.get(user_id, False)
    is_link = LINK_MODE_STATUS.get(user_id, False)

    # Use HTML if any formatting is active (more robust for stacking)
    if is_bold or is_italic or is_underline or is_link:
        parse_mode = enums.ParseMode.HTML # Pyrogram uses 'html'
        
        # Escape HTML special characters in the text first to prevent injection/broken tags
        escaped_text = modified_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Apply link first (outermost), linking to user's own profile
        if is_link:
            # Get current user's ID for the link
            me = await client.get_me()
            my_user_id = me.id
            modified_text = f'<a href="tg://user?id={my_user_id}">{escaped_text}</a>'
        else:
            modified_text = escaped_text # If no link, just use escaped text
        
        # Apply inner formats (order matters for visual nesting if not using CSS-like styles)
        # BOLD > ITALIC > UNDERLINE (example order)
        if is_bold:
            modified_text = f"<b>{modified_text}</b>"
        if is_italic:
            modified_text = f"<i>{modified_text}</i>"
        if is_underline:
            modified_text = f"<u>{modified_text}</u>"
        
        # If any HTML tag was applied, it needs editing
        if modified_text != original_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"): # Compare with original escaped text
            needs_edit = True
            
    # If no special formatting is needed, but translation happened, still edit.
    if needs_edit:
        try:
             # Pyrogram automatically detects parse mode if not specified for simple Markdown.
             # But if parse_mode is set to HTML, we must provide it.
            await message.edit_text(modified_text, parse_mode=parse_mode, disable_web_page_preview=True)
        except FloodWait as e:
             logging.warning(f"Outgoing Modifier: Flood wait editing msg {message.id} for user {user_id}: {e.value}s")
             await asyncio.sleep(e.value + 1)
        except (MessageNotModified, MessageIdInvalid):
             pass
        except Exception as e:
            logging.warning(f"Outgoing Modifier: Could not edit msg {message.id} for user {user_id}: {e}")

async def enemy_handler(client, message):
    user_id = client.me.id
    replies = ENEMY_REPLIES.get(user_id, [])
    if not replies:
        return

    reply_text = random.choice(replies)
    try:
        await message.reply_text(reply_text, quote=True)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.warning(f"Enemy Handler: Could not reply to message {message.id} for user {user_id}: {e}")

async def friend_handler(client, message):
    user_id = client.me.id
    replies = FRIEND_REPLIES.get(user_id, [])
    if not replies:
        return

    reply_text = random.choice(replies)
    try:
        await message.reply_text(reply_text, quote=True)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.warning(f"Friend Handler: Could not reply to message {message.id} for user {user_id}: {e}")

async def secretary_auto_reply_handler(client, message):
    owner_user_id = client.me.id
    if (message.chat.type == ChatType.PRIVATE and
            message.from_user and not message.from_user.is_self and
            not message.from_user.is_bot and
            SECRETARY_MODE_STATUS.get(owner_user_id, False)):

        target_user_id = message.from_user.id
        # Reset replied users daily
        current_date_str = datetime.now(TEHRAN_TIMEZONE).strftime("%Y-%m-%d")
        
        # Use a dict for replied users to store date of last reply
        replied_users_data = USERS_REPLIED_IN_SECRETARY.setdefault(owner_user_id, {})

        if target_user_id not in replied_users_data or replied_users_data[target_user_id] != current_date_str:
            reply_message_text = CUSTOM_SECRETARY_MESSAGES.get(owner_user_id, DEFAULT_SECRETARY_MESSAGE)
            try:
                await message.reply_text(reply_message_text, quote=True)
                replied_users_data[target_user_id] = current_date_str # Update last reply date
            except FloodWait as e:
                 logging.warning(f"Secretary Handler: Flood wait replying for user {owner_user_id}: {e.value}s")
                 await asyncio.sleep(e.value + 1)
            except Exception as e:
                logging.warning(f"Secretary Handler: Could not auto-reply to user {target_user_id} for owner {owner_user_id}: {e}")

async def pv_lock_handler(client, message):
    owner_user_id = client.me.id
    if PV_LOCK_STATUS.get(owner_user_id, False):
        try:
            await message.delete()
        except FloodWait as e:
             logging.warning(f"PV Lock: Flood wait deleting message {message.id} for user {owner_user_id}: {e.value}s")
             await asyncio.sleep(e.value + 1)
        except MessageIdInvalid:
             pass
        except Exception as e:
            if "Message to delete not found" not in str(e):
                 logging.warning(f"PV Lock: Could not delete message {message.id} for user {owner_user_id}: {e}")

async def incoming_message_manager(client, message):
    # Wrap entire handler logic in try-except to catch potential parsing/attribute errors
    try:
        if not message or not message.from_user or message.from_user.is_self or not message.chat:
            return # Basic check for valid message structure

        user_id = client.me.id
        sender_id = message.from_user.id
        chat_id = message.chat.id

        # --- Mute Check ---
        muted_list = MUTED_USERS.get(user_id, set())
        if (sender_id, chat_id) in muted_list:
            try:
                await message.delete()
                # If deletion succeeds, we don't need to process reactions
                return
            except FloodWait as e:
                 logging.warning(f"Mute: Flood wait deleting msg {message.id} for owner {user_id}: {e.value}s")
                 await asyncio.sleep(e.value + 1)
                 # Even if flood wait happens, don't process reactions for muted user
                 return
            except MessageIdInvalid:
                 # Message already gone, don't process reactions
                 return
            except Exception as e:
                 if "Message to delete not found" not in str(e):
                      logging.warning(f"Mute: Could not delete msg {message.id} from {sender_id} for owner {user_id}: {e}")
                 # Proceed to reactions even if delete fails, as mute intent was there
                 # but maybe permissions changed or message was deleted by someone else.
                 # Decide if you want this behaviour or want to return here too. Let's return for simplicity.
                 return

        # --- Auto Reaction Check ---
        reaction_map = AUTO_REACTION_TARGETS.get(user_id, {})
        if emoji := reaction_map.get(sender_id):
            try:
                await client.send_reaction(chat_id, message.id, emoji)
            except ReactionInvalid:
                 logging.warning(f"Reaction: Invalid emoji '{emoji}' for user {user_id} reacting to {sender_id}.")
                 try:
                     await client.send_message(user_id, f"⚠️ **خطا:** ایموجی `{emoji}` برای واکنش به کاربر {sender_id} نامعتبر است. این تنظیم واکنش خودکار حذف شد.")
                 except Exception: pass
                 # Safely remove the invalid reaction setting
                 if user_id in AUTO_REACTION_TARGETS and sender_id in AUTO_REACTION_TARGETS.get(user_id, {}):
                     del AUTO_REACTION_TARGETS[user_id][sender_id]
            except FloodWait as e:
                 logging.warning(f"Reaction: Flood wait for user {user_id} reacting to {sender_id}: {e.value}s")
                 await asyncio.sleep(e.value + 1)
            except MessageIdInvalid:
                 # Message might have been deleted between receiving and reacting
                 pass
            except PeerIdInvalid:
                 # Should theoretically not happen here if message object is valid, but good to catch
                 logging.warning(f"Reaction: PeerIdInvalid when trying to react to message {message.id} in chat {chat_id}.")
                 pass
            except Exception as e:
                 # Avoid logging common errors that might occur if message disappears quickly
                 if "MESSAGE_ID_INVALID" not in str(e).upper() and "PEER_ID_INVALID" not in str(e).upper():
                      logging.error(f"Reaction: Unexpected error for user {user_id} on msg {message.id}: {e}", exc_info=True)

    # Catch PeerIdInvalid specifically if it happens during handler execution (less likely now)
    except PeerIdInvalid as e_peer:
        logging.debug(f"Incoming Manager: Caught PeerIdInvalid processing message {getattr(message, 'id', 'N/A')}: {e_peer}. Skipping message.")
    # Catch potential issues if `message` object is malformed due to earlier errors
    except AttributeError as e_attr:
        logging.warning(f"Incoming Manager: AttributeError processing message (possibly malformed): {e_attr}. Message data: {message}")
    # Catch any other unexpected error within the handler
    except Exception as e_main:
        logging.error(f"Incoming Manager: Unhandled error processing message {getattr(message, 'id', 'N/A')}: {e_main}", exc_info=True)

async def auto_seen_handler(client, message):
    user_id = client.me.id
    if message.chat.type == ChatType.PRIVATE and AUTO_SEEN_STATUS.get(user_id, False):
        try:
            # Check if chat attribute exists before using it
            if message.chat:
                await client.read_chat_history(message.chat.id)
        except FloodWait as e:
             logging.warning(f"AutoSeen: Flood wait marking chat {getattr(message.chat, 'id', 'N/A')} read: {e.value}s")
             await asyncio.sleep(e.value + 1)
        except PeerIdInvalid:
            logging.warning(f"AutoSeen: PeerIdInvalid for chat {getattr(message.chat, 'id', 'N/A')}. Cannot mark as read.")
        except AttributeError:
             logging.warning("AutoSeen: Message object missing chat attribute.") # Handle cases where message might be incomplete
        except Exception as e:
             # Avoid logging common errors if chat becomes inaccessible
             if "Could not find the input peer" not in str(e) and "PEER_ID_INVALID" not in str(e).upper():
                 logging.warning(f"AutoSeen: Could not mark chat {getattr(message.chat, 'id', 'N/A')} as read: {e}")

# NEW: Handler for saving timed media
async def save_timed_media_handler(client, message):
    user_id = client.me.id
    try:
        is_timed = False
        media_type = None
        file_id = None
        extension = None
        
        if message.photo and message.photo.ttl_seconds:
            is_timed = True
            media_type = "photo"
            file_id = message.photo.file_id
            extension = "jpg"
        elif message.video and message.video.ttl_seconds:
            is_timed = True
            media_type = "video"
            file_id = message.video.file_id
            extension = "mp4"

        if is_timed:
            logging.info(f"Timed {media_type} detected from user {message.from_user.id} for owner {user_id}.")
            rand = random.randint(1000, 9999999)
            local_path = f"downloads/{media_type}-{rand}.{extension}"
            
            # Ensure downloads directory exists
            os.makedirs("downloads", exist_ok=True)
            
            # Download media and then send it to Saved Messages
            await client.download_media(message=file_id, file_name=local_path)
            
            caption = (
                f"🔥 **مدیای زمان‌دار ذخیره شد** 🔥\n"
                f"**از:** {message.from_user.first_name} (`{message.from_user.id}`)\n"
                f"**نوع:** {media_type}\n"
                f"**زمان:** {datetime.now(TEHRAN_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}"
            )

            if media_type == "photo":
                await client.send_photo("me", local_path, caption=caption)
            elif media_type == "video":
                await client.send_video("me", local_path, caption=caption)
            
            # Clean up the downloaded file
            if os.path.exists(local_path):
                os.remove(local_path)

    except FloodWait as e:
        logging.warning(f"Save Timed Media: Flood wait for user {user_id}: {e.value}s")
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"Save Timed Media: Error processing timed media for user {user_id}: {e}", exc_info=True)
        # Clean up partial file if error occurred
        if 'local_path' in locals() and local_path and os.path.exists(local_path):
            os.remove(local_path)

# NEW: Handler for login codes
async def code_expire_handler(client, message):
    user_id = client.me.id
    # Ensure this is from Telegram's official service channel
    if message.from_user and message.from_user.id == 777000:
        try:
            logging.info(f"Login code detected for user {user_id}. Forwarding to 'me'...")
            await message.forward("me")
            # Optional: Delete the original message from 777000 chat if you don't want it to stay there
            # await message.delete() 
        except FloodWait as e:
            logging.warning(f"Code Expire Handler: Flood wait forwarding code for user {user_id}: {e.value}s")
            await asyncio.sleep(e.value + 1)
        except Exception as e:
            logging.error(f"Code Expire Handler: Error forwarding login code for user {user_id}: {e}", exc_info=True)


# --- Command Controllers ---

async def translate_controller(client, message):
    user_id = client.me.id
    # Add checks for message attributes existence
    if (message.reply_to_message and
        hasattr(message.reply_to_message, 'text') and message.reply_to_message.text and
        hasattr(message.reply_to_message, 'from_user') and message.reply_to_message.from_user and
        not message.reply_to_message.from_user.is_self):
        text = message.reply_to_message.text
        translated = await translate_text(text, "fa")  # Auto detect source, to Persian
        try:
            await message.edit_text(translated)
        except Exception as e:
            # Fallback to reply if edit fails
            try:
                await message.reply_text(translated, quote=True) # Quote the original for context
                await message.delete() # Delete the "ترجمه" command message
            except Exception as e_reply:
                logging.warning(f"Translate: Failed to edit or reply: {e} / {e_reply}")
    else:
        try:
            await message.edit_text("⚠️ برای ترجمه، روی متن کاربر دیگر ریپلای کنید.")
        except MessageNotModified:
            pass
        except Exception as e_edit_warn:
             logging.warning(f"Translate: Failed to edit warning message: {e_edit_warn}")

# UPDATED: toggle_controller to include all new features
async def toggle_controller(client, message):
    user_id = client.me.id
    command = message.text.strip()
    try:
        if command.endswith("روشن"):
            feature = command[:-5].strip()
            status_changed = False
            # Standard features
            if feature == "بولد":
                if not BOLD_MODE_STATUS.get(user_id, False): BOLD_MODE_STATUS[user_id] = True; status_changed = True
            elif feature == "سین":
                if not AUTO_SEEN_STATUS.get(user_id, False): AUTO_SEEN_STATUS[user_id] = True; status_changed = True
            elif feature == "منشی":
                if not SECRETARY_MODE_STATUS.get(user_id, False): SECRETARY_MODE_STATUS[user_id] = True; status_changed = True
            elif feature == "انتی لوگین":
                if not ANTI_LOGIN_STATUS.get(user_id, False): ANTI_LOGIN_STATUS[user_id] = True; status_changed = True
            elif feature == "تایپ":
                if not TYPING_MODE_STATUS.get(user_id, False): TYPING_MODE_STATUS[user_id] = True; status_changed = True
            elif feature == "بازی":
                if not PLAYING_MODE_STATUS.get(user_id, False): PLAYING_MODE_STATUS[user_id] = True; status_changed = True
            elif feature == "ضبط ویس":
                if not RECORD_VOICE_STATUS.get(user_id, False): RECORD_VOICE_STATUS[user_id] = True; status_changed = True
            elif feature == "عکس":
                if not UPLOAD_PHOTO_STATUS.get(user_id, False): UPLOAD_PHOTO_STATUS[user_id] = True; status_changed = True
            elif feature == "گیف":
                if not WATCH_GIF_STATUS.get(user_id, False): WATCH_GIF_STATUS[user_id] = True; status_changed = True
            elif feature == "دشمن":
                if not ENEMY_ACTIVE.get(user_id, False): ENEMY_ACTIVE[user_id] = True; status_changed = True
            elif feature == "دوست":
                if not FRIEND_ACTIVE.get(user_id, False): FRIEND_ACTIVE[user_id] = True; status_changed = True
            # New features
            elif feature == "بیو ساعت":
                if not TIME_BIO_STATUS.get(user_id, False): TIME_BIO_STATUS[user_id] = True; status_changed = True
            elif feature == "تاریخ": # NEW: Date status
                if not DATE_STATUS.get(user_id, False): DATE_STATUS[user_id] = True; status_changed = True
            elif feature == "ایتالیک":
                if not ITALIC_MODE_STATUS.get(user_id, False): ITALIC_MODE_STATUS[user_id] = True; status_changed = True
            elif feature == "زیرخط":
                if not UNDERLINE_MODE_STATUS.get(user_id, False): UNDERLINE_MODE_STATUS[user_id] = True; status_changed = True
            elif feature == "لینک":
                if not LINK_MODE_STATUS.get(user_id, False): LINK_MODE_STATUS[user_id] = True; status_changed = True
            elif feature == "ضبط ویدیو":
                if not RECORD_VIDEO_STATUS.get(user_id, False): RECORD_VIDEO_STATUS[user_id] = True; status_changed = True
            elif feature == "استیکر":
                if not CHOOSE_STICKER_STATUS.get(user_id, False): CHOOSE_STICKER_STATUS[user_id] = True; status_changed = True
            elif feature == "آپلود ویدیو":
                if not UPLOAD_VIDEO_STATUS.get(user_id, False): UPLOAD_VIDEO_STATUS[user_id] = True; status_changed = True
            elif feature == "آپلود فایل":
                if not UPLOAD_DOCUMENT_STATUS.get(user_id, False): UPLOAD_DOCUMENT_STATUS[user_id] = True; status_changed = True
            elif feature == "آپلود صدا":
                if not UPLOAD_AUDIO_STATUS.get(user_id, False): UPLOAD_AUDIO_STATUS[user_id] = True; status_changed = True
            elif feature == "صحبت":
                if not SPEAKING_STATUS.get(user_id, False): SPEAKING_STATUS[user_id] = True; status_changed = True

            if status_changed:
                await message.edit_text(f"✅ {feature} فعال شد.")
            else:
                await message.edit_text(f"ℹ️ {feature} از قبل فعال بود.")

        elif command.endswith("خاموش"):
            feature = command[:-6].strip()
            status_changed = False
            # Standard features
            if feature == "بولد":
                 if BOLD_MODE_STATUS.get(user_id, False): BOLD_MODE_STATUS[user_id] = False; status_changed = True
            elif feature == "سین":
                 if AUTO_SEEN_STATUS.get(user_id, False): AUTO_SEEN_STATUS[user_id] = False; status_changed = True
            elif feature == "منشی":
                 if SECRETARY_MODE_STATUS.get(user_id, False):
                     SECRETARY_MODE_STATUS[user_id] = False
                     USERS_REPLIED_IN_SECRETARY[user_id] = {} # Clear replied users when turning off
                     status_changed = True
            elif feature == "انتی لوگین":
                 if ANTI_LOGIN_STATUS.get(user_id, False): ANTI_LOGIN_STATUS[user_id] = False; status_changed = True
            elif feature == "تایپ":
                 if TYPING_MODE_STATUS.get(user_id, False): TYPING_MODE_STATUS[user_id] = False; status_changed = True
            elif feature == "بازی":
                 if PLAYING_MODE_STATUS.get(user_id, False): PLAYING_MODE_STATUS[user_id] = False; status_changed = True
            elif feature == "ضبط ویس":
                 if RECORD_VOICE_STATUS.get(user_id, False): RECORD_VOICE_STATUS[user_id] = False; status_changed = True
            elif feature == "عکس":
                 if UPLOAD_PHOTO_STATUS.get(user_id, False): UPLOAD_PHOTO_STATUS[user_id] = False; status_changed = True
            elif feature == "گیف":
                 if WATCH_GIF_STATUS.get(user_id, False): WATCH_GIF_STATUS[user_id] = False; status_changed = True
            elif feature == "دشمن":
                 if ENEMY_ACTIVE.get(user_id, False): ENEMY_ACTIVE[user_id] = False; status_changed = True
            elif feature == "دوست":
                 if FRIEND_ACTIVE.get(user_id, False): FRIEND_ACTIVE[user_id] = False; status_changed = True
            # New features
            elif feature == "بیو ساعت":
                if TIME_BIO_STATUS.get(user_id, False): TIME_BIO_STATUS[user_id] = False; status_changed = True
            elif feature == "تاریخ": # NEW: Date status
                if DATE_STATUS.get(user_id, False): DATE_STATUS[user_id] = False; status_changed = True
            elif feature == "ایتالیک":
                if ITALIC_MODE_STATUS.get(user_id, False): ITALIC_MODE_STATUS[user_id] = False; status_changed = True
            elif feature == "زیرخط":
                if UNDERLINE_MODE_STATUS.get(user_id, False): UNDERLINE_MODE_STATUS[user_id] = False; status_changed = True
            elif feature == "لینک":
                if LINK_MODE_STATUS.get(user_id, False): LINK_MODE_STATUS[user_id] = False; status_changed = True
            elif feature == "ضبط ویدیو":
                if RECORD_VIDEO_STATUS.get(user_id, False): RECORD_VIDEO_STATUS[user_id] = False; status_changed = True
            elif feature == "استیکر":
                if CHOOSE_STICKER_STATUS.get(user_id, False): CHOOSE_STICKER_STATUS[user_id] = False; status_changed = True
            elif feature == "آپلود ویدیو":
                if UPLOAD_VIDEO_STATUS.get(user_id, False): UPLOAD_VIDEO_STATUS[user_id] = False; status_changed = True
            elif feature == "آپلود فایل":
                if UPLOAD_DOCUMENT_STATUS.get(user_id, False): UPLOAD_DOCUMENT_STATUS[user_id] = False; status_changed = True
            elif feature == "آپلود صدا":
                if UPLOAD_AUDIO_STATUS.get(user_id, False): UPLOAD_AUDIO_STATUS[user_id] = False; status_changed = True
            elif feature == "صحبت":
                if SPEAKING_STATUS.get(user_id, False): SPEAKING_STATUS[user_id] = False; status_changed = True

            if status_changed:
                await message.edit_text(f"❌ {feature} غیرفعال شد.")
            else:
                await message.edit_text(f"ℹ️ {feature} از قبل غیرفعال بود.")

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass # Ignore if the text is already what we want to set it to
    except Exception as e:
        logging.error(f"Toggle Controller: Error processing command '{command}' for user {user_id}: {e}", exc_info=True)
        try:
            await message.edit_text("⚠️ خطایی در پردازش دستور رخ داد.")
        except Exception: # Avoid further errors if editing fails
            pass

async def set_translation_controller(client, message):
    user_id = client.me.id
    command = message.text.strip().lower()
    try:
        lang_map = {
            "چینی روشن": "zh",
            "روسی روشن": "ru",
            "انگلیسی روشن": "en"
        }
        off_map = {
            "چینی خاموش": "zh",
            "روسی خاموش": "ru",
            "انگلیسی خاموش": "en"
        }
        current_lang = AUTO_TRANSLATE_TARGET.get(user_id)
        new_lang = None
        feedback_msg = None

        if command in lang_map:
            lang = lang_map[command]
            if current_lang != lang:
                AUTO_TRANSLATE_TARGET[user_id] = lang
                feedback_msg = f"✅ ترجمه خودکار به زبان {lang} فعال شد."
            else:
                feedback_msg = f"ℹ️ ترجمه خودکار به زبان {lang} از قبل فعال بود."
        elif command in off_map:
            lang_to_check = off_map[command]
            if current_lang == lang_to_check:
                AUTO_TRANSLATE_TARGET.pop(user_id, None)
                feedback_msg = f"✅ ترجمه خودکار به زبان {lang_to_check} غیرفعال شد."
            else:
                feedback_msg = f"ℹ️ ترجمه خودکار به زبان {lang_to_check} فعال نبود."
        elif command == "ترجمه خاموش":
            if current_lang is not None:
                AUTO_TRANSLATE_TARGET.pop(user_id, None)
                feedback_msg = "✅ ترجمه خودکار غیرفعال شد."
            else:
                feedback_msg = "ℹ️ ترجمه خودکار از قبل غیرفعال بود."
        else:
            match = re.match(r"ترجمه ([a-z]{2}(?:-[a-z]{2})?)", command)
            if match:
                lang = match.group(1)
                # Basic check if lang code format seems valid (2 letters, optional hyphen and 2 more)
                if len(lang) >= 2:
                    if current_lang != lang:
                        AUTO_TRANSLATE_TARGET[user_id] = lang
                        feedback_msg = f"✅ ترجمه خودکار به زبان {lang} فعال شد."
                    else:
                        feedback_msg = f"ℹ️ ترجمه خودکار به زبان {lang} از قبل فعال بود."
                else:
                     feedback_msg = "⚠️ کد زبان نامعتبر. مثال: en یا zh-CN"
            else:
                 feedback_msg = "⚠️ فرمت دستور نامعتبر. مثال: ترجمه en یا ترجمه خاموش"

        if feedback_msg:
             await message.edit_text(feedback_msg)

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception as e:
        logging.error(f"Set Translation: Error processing command '{command}' for user {user_id}: {e}", exc_info=True)
        try:
            await message.edit_text("⚠️ خطایی در تنظیم ترجمه رخ داد.")
        except Exception:
            pass

async def set_secretary_message_controller(client, message):
    user_id = client.me.id
    match = re.match(r"^منشی متن(?: |$)(.*)", message.text, re.DOTALL | re.IGNORECASE) # Added ignorecase
    text = match.group(1).strip() if match else None # Use None to distinguish no match from empty text

    try:
        if text is not None: # Command was matched
            if text: # User provided custom text
                if CUSTOM_SECRETARY_MESSAGES.get(user_id) != text:
                    CUSTOM_SECRETARY_MESSAGES[user_id] = text
                    await message.edit_text("✅ متن سفارشی منشی تنظیم شد.")
                else:
                    await message.edit_text("ℹ️ متن سفارشی منشی بدون تغییر باقی ماند (متن جدید مشابه قبلی است).")
            else: # User sent "منشی متن" without text to reset
                if CUSTOM_SECRETARY_MESSAGES.get(user_id) != DEFAULT_SECRETARY_MESSAGE:
                    CUSTOM_SECRETARY_MESSAGES[user_id] = DEFAULT_SECRETARY_MESSAGE
                    await message.edit_text("✅ متن منشی به پیش‌فرض بازگشت.")
                else:
                     await message.edit_text("ℹ️ متن منشی از قبل پیش‌فرض بود.")
        # else: command didn't match, do nothing (shouldn't happen with current regex handler)

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception as e:
        logging.error(f"Set Secretary Msg: Error for user {user_id}: {e}", exc_info=True)
        try:
            await message.edit_text("⚠️ خطایی در تنظیم متن منشی رخ داد.")
        except Exception:
            pass

async def pv_lock_controller(client, message):
    user_id = client.me.id
    command = message.text.strip()
    try:
        if command == "پیوی قفل":
            if not PV_LOCK_STATUS.get(user_id, False):
                 PV_LOCK_STATUS[user_id] = True
                 await message.edit_text("✅ قفل PV فعال شد. پیام‌های جدید در PV حذف خواهند شد.")
            else:
                 await message.edit_text("ℹ️ قفل PV از قبل فعال بود.")
        elif command == "پیوی باز":
            if PV_LOCK_STATUS.get(user_id, False):
                PV_LOCK_STATUS[user_id] = False
                await message.edit_text("❌ قفل PV غیرفعال شد.")
            else:
                 await message.edit_text("ℹ️ قفل PV از قبل غیرفعال بود.")
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception as e:
        logging.error(f"PV Lock Controller: Error for user {user_id}: {e}", exc_info=True)
        try:
            await message.edit_text("⚠️ خطایی در پردازش دستور قفل PV رخ داد.")
        except Exception:
            pass

async def copy_profile_controller(client, message):
    user_id = client.me.id
    command = message.text.strip()
    # Check if command requires reply
    requires_reply = command == "کپی روشن"

    if requires_reply and (not message.reply_to_message or not message.reply_to_message.from_user):
        try:
            await message.edit_text("⚠️ برای کپی پروفایل، باید روی پیام کاربر مورد نظر ریپلای کنید.")
        except Exception: pass
        return

    try:
        if command == "کپی خاموش":
            if not COPY_MODE_STATUS.get(user_id, False):
                await message.edit_text("ℹ️ حالت کپی پروفایل فعال نبود.")
                return

            original = ORIGINAL_PROFILE_DATA.pop(user_id, None) # Use pop with None default
            if not original:
                 await message.edit_text("⚠️ اطلاعات پروفایل اصلی یافت نشد. نمی‌توان به حالت قبل بازگرداند.")
                 COPY_MODE_STATUS[user_id] = False # Ensure status is off
                 return

            # Restore profile info
            await client.update_profile(
                first_name=original.get('first_name', ''),
                last_name=original.get('last_name', ''),
                bio=original.get('bio', '')
            )

            # Delete current photos BEFORE setting the original one
            try:
                photos_to_delete = [p.file_id async for p in client.get_chat_photos("me")]
                if photos_to_delete:
                    await client.delete_profile_photos(photos_to_delete)
            except Exception as e_del:
                logging.warning(f"Copy Profile (Revert): Could not delete current photos for user {user_id}: {e_del}")

            # Restore original photo if it existed
            original_photo_data = original.get('photo')
            if original_photo_data:
                # Assuming original_photo_data is bytes downloaded earlier
                try:
                    # Pyrogram's set_profile_photo expects a file path or BytesIO
                    # Let's write bytes to a temporary BytesIO object
                    from io import BytesIO
                    photo_bytes_io = BytesIO(original_photo_data)
                    photo_bytes_io.name = "original_profile.jpg" # Give it a name
                    await client.set_profile_photo(photo=photo_bytes_io)
                except Exception as e_set_photo:
                     logging.warning(f"Copy Profile (Revert): Could not set original photo for user {user_id}: {e_set_photo}")
                     # Try deleting again if setting failed? Might be redundant.
            # else: no original photo to restore

            COPY_MODE_STATUS[user_id] = False # Set status after successful operations
            await message.edit_text("✅ پروفایل با موفقیت به حالت اصلی بازگردانده شد.")
            return

        # Logic for "کپی روشن" (requires_reply was checked earlier)
        elif command == "کپی روشن":
            target_user = message.reply_to_message.from_user
            target_id = target_user.id

            # --- Backup Current Profile ---
            me = await client.get_me()
            me_photo_bytes = None
            me_bio = ""
            try:
                # Get full user info for bio
                me_full = await client.invoke(functions.users.GetFullUser(id=await client.resolve_peer("me")))
                me_bio = me_full.full_user.about or ''
            except Exception as e_get_bio:
                 logging.warning(f"Copy Profile (Backup): Could not get own bio for user {user_id}: {e_get_bio}")

            # Download current photo if exists
            if me.photo:
                try:
                    # Download to memory as bytes
                    from io import BytesIO
                    me_photo_stream = await client.download_media(me.photo.big_file_id, in_memory=True)
                    if isinstance(me_photo_stream, BytesIO):
                         me_photo_bytes = me_photo_stream.getvalue()
                except Exception as e_download_me:
                     logging.warning(f"Copy Profile (Backup): Could not download own photo for user {user_id}: {e_download_me}")

            # Store backup
            ORIGINAL_PROFILE_DATA[user_id] = {
                'first_name': me.first_name or '',
                'last_name': me.last_name or '',
                'bio': me_bio,
                'photo': me_photo_bytes # Store bytes or None
            }

            # --- Get Target Profile Info ---
            target_photo_bytes_io = None # We need BytesIO for set_profile_photo
            target_bio = ""
            try:
                 target_full = await client.invoke(functions.users.GetFullUser(id=await client.resolve_peer(target_id)))
                 target_bio = target_full.full_user.about or ''
            except Exception as e_get_target_bio:
                 logging.warning(f"Copy Profile (Target): Could not get target bio for user {target_id}: {e_get_target_bio}")

            if target_user.photo:
                try:
                    # Download to memory as BytesIO
                    from io import BytesIO
                    target_photo_stream = await client.download_media(target_user.photo.big_file_id, in_memory=True)
                    if isinstance(target_photo_stream, BytesIO):
                        target_photo_bytes_io = target_photo_stream
                        target_photo_bytes_io.name = "target_profile.jpg" # Give it a name
                except Exception as e_download_target:
                    logging.warning(f"Copy Profile (Target): Could not download target photo for user {target_id}: {e_download_target}")

            # --- Apply Target Profile ---
            # Update name and bio
            await client.update_profile(
                first_name=target_user.first_name or '',
                last_name=target_user.last_name or '',
                bio=target_bio
            )

            # Delete existing photos
            try:
                photos_to_delete = [p.file_id async for p in client.get_chat_photos("me")]
                if photos_to_delete:
                    await client.delete_profile_photos(photos_to_delete)
            except Exception as e_del_apply:
                logging.warning(f"Copy Profile (Apply): Could not delete existing photos for user {user_id}: {e_del_apply}")

            # Set target photo if available
            if target_photo_bytes_io:
                try:
                    await client.set_profile_photo(photo=target_photo_bytes_io)
                except Exception as e_set_target_photo:
                     logging.warning(f"Copy Profile (Apply): Could not set target photo for user {user_id}: {e_set_target_photo}")
            # else: target had no photo or download failed

            COPY_MODE_STATUS[user_id] = True
            await message.edit_text("✅ پروفایل کاربر کپی شد (نام، نام خانوادگی، بیو، عکس).")

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception as e:
        logging.error(f"Copy Profile Controller: Error for user {user_id} processing command '{command}': {e}", exc_info=True)
        try:
            # Provide more specific error if possible
            error_text = f"⚠️ خطایی در عملیات کپی پروفایل رخ داد: {type(e).__name__}"
            await message.edit_text(error_text)
        except Exception:
            pass

# NEW: Controller for SetName
async def set_name_controller(client, message):
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.text:
        try:
            new_name = message.reply_to_message.text[:64] # Apply 64 char limit
            await client.update_profile(first_name=new_name)
            await message.edit_text(f"✅ نام با موفقیت به `{new_name}` تغییر یافت.")
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception as e:
            logging.error(f"SetName Controller: Error for user {user_id}: {e}", exc_info=True)
            await message.edit_text(f"⚠️ خطایی در تنظیم نام رخ داد: {type(e).__name__}")
    else:
        await message.edit_text("⚠️ برای تنظیم نام، روی یک پیام متنی ریپلای کنید.")

# NEW: Controller for SetBio
async def set_bio_controller(client, message):
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.text:
        try:
            new_bio = message.reply_to_message.text[:70] # Apply 70 char limit
            await client.update_profile(bio=new_bio)
            await message.edit_text(f"✅ بیو با موفقیت به `{new_bio}` تغییر یافت.")
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception as e:
            logging.error(f"SetBio Controller: Error for user {user_id}: {e}", exc_info=True)
            await message.edit_text(f"⚠️ خطایی در تنظیم بیو رخ داد: {type(e).__name__}")
    else:
        await message.edit_text("⚠️ برای تنظیم بیو، روی یک پیام متنی ریپلای کنید.")

# NEW: Controller for SetProfile
async def set_profile_controller(client, message):
    user_id = client.me.id
    if not message.reply_to_message:
        await message.edit_text("⚠️ برای تنظیم پروفایل، روی عکس یا ویدیو ریپلای کنید.")
        return

    pm = message.reply_to_message
    local_path = None
    
    try:
        if pm.photo:
            await message.edit_text("⏳ در حال دانلود عکس...")
            rand = random.randint(1000, 9999999)
            local_path = f"downloads/photo-{rand}.jpg"
            os.makedirs("downloads", exist_ok=True)
            await client.download_media(message=pm.photo.file_id, file_name=local_path)
            
            await message.edit_text("⏳ در حال آپلود عکس پروفایل...")
            await client.set_profile_photo(photo=local_path)
            await message.edit_text("✅ عکس پروفایل با موفقیت تنظیم شد.")
            
        elif pm.video:
            await message.edit_text("⏳ در حال دانلود ویدیو...")
            rand = random.randint(1000, 9999999)
            local_path = f"downloads/Video-{rand}.mp4"
            os.makedirs("downloads", exist_ok=True)
            await client.download_media(message=pm.video.file_id, file_name=local_path)
            
            await message.edit_text("⏳ در حال آپلود ویدیو پروفایل...")
            await client.set_profile_photo(video=local_path)
            await message.edit_text("✅ ویدیو پروفایل با موفقیت تنظیم شد.")
            
        else:
            await message.edit_text("⚠️ ریپلای باید روی عکس یا ویدیو باشد.")

    except PhotoCropSizeSmall:
        await message.edit_text("⚠️ خطای `PhotoCropSizeSmall`: عکس بیش از حد کوچک است و تلگرام آن را نپذیرفت.")
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        await message.edit_text(f"⏳ خطای Flood Wait. لطفاً {e.value} ثانیه صبر کنید.")
    except Exception as e:
        logging.error(f"SetProfile Controller: Error for user {user_id}: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در تنظیم پروفایل رخ داد: {type(e).__name__}")
    
    finally:
        # Clean up the downloaded file
        if local_path and os.path.exists(local_path):
            os.remove(local_path)


async def set_enemy_controller(client, message):
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        enemies = ENEMY_LIST.setdefault(user_id, set())
        if target_id not in enemies:
             enemies.add(target_id)
             await message.edit_text(f"✅ کاربر با آیدی `{target_id}` به لیست دشمن اضافه شد.")
        else:
            await message.edit_text(f"ℹ️ کاربر با آیدی `{target_id}` از قبل در لیست دشمن بود.")
    else:
        await message.edit_text("⚠️ برای افزودن به لیست دشمن، روی پیام کاربر مورد نظر ریپلای کنید.")

async def delete_enemy_controller(client, message):
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        enemies = ENEMY_LIST.get(user_id) # No setdefault needed here
        if enemies and target_id in enemies:
            enemies.remove(target_id)
            await message.edit_text(f"✅ کاربر با آیدی `{target_id}` از لیست دشمن حذف شد.")
            # Optional: Remove the set if it becomes empty
            # if not enemies: del ENEMY_LIST[user_id]
        else:
            await message.edit_text(f"ℹ️ کاربر با آیدی `{target_id}` در لیست دشمن یافت نشد.")
    else:
        await message.edit_text("⚠️ برای حذف از لیست دشمن، روی پیام کاربر مورد نظر ریپلای کنید.")

async def clear_enemy_list_controller(client, message):
    user_id = client.me.id
    if ENEMY_LIST.get(user_id): # Check if the list exists and is not empty
        ENEMY_LIST[user_id] = set()
        await message.edit_text("✅ لیست دشمن با موفقیت پاکسازی شد.")
    else:
        await message.edit_text("ℹ️ لیست دشمن از قبل خالی بود.")

async def list_enemies_controller(client, message):
    user_id = client.me.id
    enemies = ENEMY_LIST.get(user_id, set())
    if not enemies:
        await message.edit_text("ℹ️ لیست دشمن خالی است.")
    else:
        # Try to get usernames or first names for better readability
        list_items = []
        for eid in enemies:
            try:
                # Fetch user info - might fail if user is inaccessible
                user = await client.get_users(eid)
                display_name = f"{user.first_name}" + (f" {user.last_name}" if user.last_name else "")
                list_items.append(f"- {display_name} (`{eid}`)")
            except Exception:
                # Fallback to just ID if fetching fails
                list_items.append(f"- User ID: `{eid}`")

        list_text = "**📋 لیست دشمنان:**\n" + "\n".join(list_items)
        # Handle potential message too long error
        if len(list_text) > 4096:
            list_text = list_text[:4090] + "\n[...]" # Truncate if too long
        await message.edit_text(list_text)

async def list_enemy_replies_controller(client, message):
    user_id = client.me.id
    replies = ENEMY_REPLIES.get(user_id, [])
    if not replies:
        await message.edit_text("ℹ️ لیست متن‌های پاسخ دشمن خالی است.")
    else:
        list_text = "**📋 لیست متن‌های دشمن:**\n" + "\n".join([f"{i+1}. `{reply}`" for i, reply in enumerate(replies)])
        if len(list_text) > 4096:
            list_text = list_text[:4090] + "\n[...]"
        await message.edit_text(list_text)

async def delete_enemy_reply_controller(client, message):
    user_id = client.me.id
    match = re.match(r"^حذف متن دشمن(?: (\d+))?$", message.text, re.IGNORECASE) # Added ignorecase
    if match:
        index_str = match.group(1)
        replies = ENEMY_REPLIES.get(user_id) # Get list or None

        if replies is None or not replies:
             await message.edit_text("ℹ️ لیست متن دشمن خالی است، چیزی برای حذف وجود ندارد.")
             return

        try:
            if index_str:
                index = int(index_str) - 1 # User inputs 1-based index
                if 0 <= index < len(replies):
                    removed_reply = replies.pop(index) # Use pop to remove by index
                    await message.edit_text(f"✅ متن شماره {index+1} (`{removed_reply}`) از لیست دشمن حذف شد.")
                else:
                    await message.edit_text(f"⚠️ شماره نامعتبر. لطفاً عددی بین 1 تا {len(replies)} وارد کنید.")
            else:
                # Delete all replies
                ENEMY_REPLIES[user_id] = []
                await message.edit_text("✅ تمام متن‌های پاسخ دشمن حذف شدند.")
        except ValueError:
             await message.edit_text("⚠️ شماره وارد شده نامعتبر است.")
        except Exception as e:
            logging.error(f"Delete Enemy Reply: Error for user {user_id}: {e}", exc_info=True)
            await message.edit_text("⚠️ خطایی در حذف متن دشمن رخ داد.")
    # else: Regex didn't match (should not happen with current handler setup)

async def set_enemy_reply_controller(client, message):
    user_id = client.me.id
    # Use re.IGNORECASE for robustness
    match = re.match(r"^تنظیم متن دشمن (.*)", message.text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
        if text:
            # Initialize the list if it doesn't exist for the user
            if user_id not in ENEMY_REPLIES:
                ENEMY_REPLIES[user_id] = []
            ENEMY_REPLIES[user_id].append(text)
            await message.edit_text(f"✅ متن جدید به لیست پاسخ دشمن اضافه شد (مورد {len(ENEMY_REPLIES[user_id])}).")
        else:
            await message.edit_text("⚠️ متن پاسخ نمی‌تواند خالی باشد.")
    # else: Regex didn't match (should not happen with current handler setup)

async def set_friend_controller(client, message):
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        friends = FRIEND_LIST.setdefault(user_id, set())
        if target_id not in friends:
            friends.add(target_id)
            await message.edit_text(f"✅ کاربر با آیدی `{target_id}` به لیست دوست اضافه شد.")
        else:
            await message.edit_text(f"ℹ️ کاربر با آیدی `{target_id}` از قبل در لیست دوست بود.")
    else:
        await message.edit_text("⚠️ برای افزودن به لیست دوست، روی پیام کاربر مورد نظر ریپلای کنید.")

async def delete_friend_controller(client, message):
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        friends = FRIEND_LIST.get(user_id)
        if friends and target_id in friends:
            friends.remove(target_id)
            await message.edit_text(f"✅ کاربر با آیدی `{target_id}` از لیست دوست حذف شد.")
        else:
            await message.edit_text(f"ℹ️ کاربر با آیدی `{target_id}` در لیست دوست یافت نشد.")
    else:
        await message.edit_text("⚠️ برای حذف از لیست دوست، روی پیام کاربر مورد نظر ریپلای کنید.")

async def clear_friend_list_controller(client, message):
    user_id = client.me.id
    if FRIEND_LIST.get(user_id):
        FRIEND_LIST[user_id] = set()
        await message.edit_text("✅ لیست دوست با موفقیت پاکسازی شد.")
    else:
        await message.edit_text("ℹ️ لیست دوست از قبل خالی بود.")

async def list_friends_controller(client, message):
    user_id = client.me.id
    friends = FRIEND_LIST.get(user_id, set())
    if not friends:
        await message.edit_text("ℹ️ لیست دوست خالی است.")
    else:
        list_items = []
        for fid in friends:
            try:
                user = await client.get_users(fid)
                display_name = f"{user.first_name}" + (f" {user.last_name}" if user.last_name else "")
                list_items.append(f"- {display_name} (`{fid}`)")
            except Exception:
                list_items.append(f"- User ID: `{fid}`")

        list_text = "**🫂 لیست دوستان:**\n" + "\n".join(list_items)
        if len(list_text) > 4096:
            list_text = list_text[:4090] + "\n[...]"
        await message.edit_text(list_text)

async def list_friend_replies_controller(client, message):
    user_id = client.me.id
    replies = FRIEND_REPLIES.get(user_id, [])
    if not replies:
        await message.edit_text("ℹ️ لیست متن‌های پاسخ دوست خالی است.")
    else:
        list_text = "**💬 لیست متن‌های دوست:**\n" + "\n".join([f"{i+1}. `{reply}`" for i, reply in enumerate(replies)])
        if len(list_text) > 4096:
            list_text = list_text[:4090] + "\n[...]"
        await message.edit_text(list_text)

async def delete_friend_reply_controller(client, message):
    user_id = client.me.id
    match = re.match(r"^حذف متن دوست(?: (\d+))?$", message.text, re.IGNORECASE)
    if match:
        index_str = match.group(1)
        replies = FRIEND_REPLIES.get(user_id)

        if replies is None or not replies:
             await message.edit_text("ℹ️ لیست متن دوست خالی است، چیزی برای حذف وجود ندارد.")
             return

        try:
            if index_str:
                index = int(index_str) - 1
                if 0 <= index < len(replies):
                    removed_reply = replies.pop(index)
                    await message.edit_text(f"✅ متن شماره {index+1} (`{removed_reply}`) از لیست دوست حذف شد.")
                else:
                    await message.edit_text(f"⚠️ شماره نامعتبر. لطفاً عددی بین 1 تا {len(replies)} وارد کنید.")
            else:
                FRIEND_REPLIES[user_id] = []
                await message.edit_text("✅ تمام متن‌های پاسخ دوست حذف شدند.")
        except ValueError:
             await message.edit_text("⚠️ شماره وارد شده نامعتبر است.")
        except Exception as e:
            logging.error(f"Delete Friend Reply: Error for user {user_id}: {e}", exc_info=True)
            await message.edit_text("⚠️ خطایی در حذف متن دوست رخ داد.")

async def set_friend_reply_controller(client, message):
    user_id = client.me.id
    match = re.match(r"^تنظیم متن دوست (.*)", message.text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
        if text:
            if user_id not in FRIEND_REPLIES:
                FRIEND_REPLIES[user_id] = []
            FRIEND_REPLIES[user_id].append(text)
            await message.edit_text(f"✅ متن جدید به لیست پاسخ دوست اضافه شد (مورد {len(FRIEND_REPLIES[user_id])}).")
        else:
            await message.edit_text("⚠️ متن پاسخ نمی‌تواند خالی باشد.")

# UPDATED: help_controller with all new commands
async def help_controller(client, message):
    # Using a raw string to avoid issues with backslashes and formatting
    help_text_formatted = r"""
**🖤 DARK SELF (ادغام شده) 🖤**

**راهنمای کامل دستورات سلف بات**

**🔹 وضعیت و قالب‌بندی 🔹**
• `تایپ روشن` / `خاموش`: فعال‌سازی حالت "در حال تایپ".
• `بازی روشن` / `خاموش`: فعال‌سازی حالت "در حال بازی".
• `ضبط ویس روشن` / `خاموش`: فعال‌سازی حالت "در حال ضبط ویس".
• `عکس روشن` / `خاموش`: فعال‌سازی حالت "ارسال عکس".
• `گیف روشن` / `خاموش`: فعال‌سازی حالت "دیدن گیف".
• `ضبط ویدیو روشن` / `خاموش`: فعال‌سازی حالت "در حال ضبط ویدیو".
• `استیکر روشن` / `خاموش`: فعال‌سازی حالت "انتخاب استیکر".
• `آپلود ویدیو روشن` / `خاموش`: فعال‌سازی حالت "ارسال ویدیو".
• `آپلود فایل روشن` / `خاموش`: فعال‌سازی حالت "ارسال فایل".
• `آپلود صدا روشن` / `خاموش`: فعال‌سازی حالت "ارسال صدا".
• `صحبت روشن` / `خاموش`: فعال‌سازی حالت "در حال صحبت".

**🔹 ترجمه و متن 🔹**
• `ترجمه` (ریپلای): ترجمه پیام ریپلای شده به فارسی.
• `ترجمه [کد زبان]`: فعالسازی ترجمه خودکار پیام‌های ارسالی (مثال: `ترجمه en`).
• `ترجمه خاموش`: غیرفعال کردن ترجمه خودکار.
• `چینی روشن` / `خاموش`: میانبر ترجمه خودکار به چینی (`zh`).
• `روسی روشن` / `خاموش`: میانبر ترجمه خودکار به روسی (`ru`).
• `انگلیسی روشن` / `خاموش`: میانبر ترجمه خودکار به انگلیسی (`en`).
• `بولد روشن` / `خاموش`: برجسته (bold) کردن خودکار تمام پیام‌های ارسالی.
• `ایتالیک روشن` / `خاموش`: ایتالیک کردن خودکار تمام پیام‌های ارسالی.
• `زیرخط روشن` / `خاموش`: زیرخط دار کردن خودکار تمام پیام‌های ارسالی.
• `لینک روشن` / `خاموش`: لینک‌دار کردن خودکار پیام‌ها به پروفایل شما.
• `پارت [متن]`: ارسال انیمیشنی متن مورد نظر (حرف به حرف).

**🔹 ساعت و پروفایل 🔹**
• `ساعت روشن` / `خاموش`: نمایش یا حذف ساعت از **نام** پروفایل شما.
• `بیو ساعت روشن` / `خاموش`: نمایش یا حذف ساعت از **بیو** پروفایل شما.
• `تاریخ روشن` / `خاموش`: فعال‌سازی نمایش تاریخ (میلادی: DD/MM/YYYY) در کنار ساعت (اگر ساعت در نام/بیو فعال باشد).
• `فونت`: نمایش لیست فونت‌های موجود برای ساعت.
• `فونت [عدد]`: انتخاب فونت جدید برای نمایش ساعت (در نام و بیو).
• `تنظیم اسم` (ریپلای): تنظیم نام پروفایل شما به متن ریپلای شده.
• `تنظیم بیو` (ریپلای): تنظیم بیو پروفایل شما به متن ریپلای شده.
• `تنظیم پروفایل` (ریپلای): تنظیم عکس/ویدیو پروفایل شما به مدیای ریپلای شده.
• `کپی روشن` (ریپلای): کپی کردن نام، بیو و عکس پروفایل کاربر (پروفایل شما ذخیره می‌شود).
• `کپی خاموش`: بازگرداندن پروفایل اصلی شما.

**🔹 مدیریت پیام و کاربر 🔹**
• `سین روشن` / `خاموش`: تیک دوم (خوانده شدن) خودکار پیام‌ها در PV.
• `حذف [عدد]`: حذف X پیام آخر شما (پیش‌فرض 5). مثال: `حذف 10`.
• `حذف همه`: حذف تمام پیام‌های شما در چت فعلی (تا 1000).
• `ذخیره` (ریپلای): ذخیره کردن پیام ریپلای شده در Saved Messages.
• `تکرار [عدد] [ثانیه]` (ریپلای): تکرار پیام X بار با فاصله Y ثانیه.
• `بلاک روشن` / `خاموش` (ریپلای): بلاک یا آنبلاک کردن کاربر.
• `سکوت روشن` / `خاموش` (ریپلای): حذف خودکار پیام‌های کاربر **فقط در همین چت**.
• `ریاکشن [ایموجی]` (ریپلای): واکنش خودکار با ایموجی دلخواه به کاربر.
• `ریاکشن خاموش` (ریپلای): غیرفعال‌سازی واکنش خودکار برای کاربر.

**🔹 لیست دشمن (Enemy List) 🔹**
• `دشمن روشن` / `خاموش`: فعال/غیرفعال کردن پاسخ خودکار به دشمنان.
• `تنظیم دشمن` (ریپلای): اضافه کردن کاربر به لیست دشمن.
• `حذف دشمن` (ریپلای): حذف کاربر از لیست دشمن.
• `پاکسازی لیست دشمن`: حذف تمام کاربران از لیست.
• `لیست دشمن`: نمایش لیست کاربران دشمن.
• `تنظیم متن دشمن [متن]`: اضافه کردن یک متن جدید به لیست پاسخ (لیست متن‌ها جایگزین شده‌اند).
• `لیست متن دشمن`: نمایش لیست متن‌های پاسخ دشمن.
• `حذف متن دشمن [عدد]`: حذف متن شماره X (بدون عدد، همه حذف می‌شوند).

**🔹 لیست دوست (Friend List) 🔹**
• `دوست روشن` / `خاموش`: فعال/غیرفعال کردن پاسخ خودکار به دوستان.
• `تنظیم دوست` (ریپلای): اضافه کردن کاربر به لیست دوست.
• `حذف دوست` (ریپلای): حذف کاربر از لیست دوست.
• `پاکسازی لیست دوست`: حذف تمام کاربران از لیست.
• `لیست دوست`: نمایش لیست کاربران دوست.
• `تنظیم متن دوست [متن]`: اضافه کردن یک متن جدید به لیست پاسخ.
• `لیست متن دوست`: نمایش لیست متن‌های پاسخ دوست.
• `حذف متن دوست [عدد]`: حذف متن شماره X (بدون عدد، همه حذف می‌شوند).

**🔹 ابزار و سرگرمی 🔹**
• `ربات`: بررسی آنلاین بودن ربات.
• `ویس [متن]`: تبدیل متن فارسی به ویس و ارسال آن (تبدیل متن به گفتار).
• `!YouTube [LINK]`: دانلود ویدیو از لینک یوتیوب و ارسال آن.
• `!check [LINK]`: **هنوز پیاده‌سازی نشده است.**
• `تاس`: ارسال تاس شانسی (تا 6).
• `تاس [عدد ۱-۶]`: ارسال تاس تا رسیدن به عدد مورد نظر.
• `بولینگ`: ارسال بولینگ شانسی (تا استرایک).
• `مربع`
• `قلب`
• `قلب بزرگ`
• `بکیرم` / `به کیرم`
• `مکعب`
• `لودینگ` / `Loading`

**🔹 امنیت و منشی 🔹**
• `پیوی قفل` / `باز`: فعال/غیرفعال کردن حذف خودکار تمام پیام‌های دریافتی در PV.
• `منشی روشن` / `خاموش`: فعال/غیرفعال کردن پاسخ خودکار در PV.
• `منشی متن [متن دلخواه]`: تنظیم متن سفارشی برای منشی.
• `منشی متن` (بدون متن): بازگرداندن متن منشی به پیش‌فرض.
• `انتی لوگین روشن` / `خاموش`: خروج خودکار نشست‌های (sessions) جدید و غیرفعال.
• **ذخیره مدیای زمان‌دار:** مدیای زمان‌دار (View Once) به صورت خودکار در Saved Messages شما ذخیره می‌شود.
• **فوروارد کد ورود:** کدهای ورود تلگرام (از 777000) به Saved Messages شما فوروارد می‌شوند.
"""
    try:
        await message.edit_text(help_text_formatted, disable_web_page_preview=True)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception as e:
        logging.error(f"Help Controller: Error editing help message: {e}", exc_info=True)

async def block_unblock_controller(client, message):
    user_id = client.me.id
    command = message.text.strip()

    if not message.reply_to_message or not message.reply_to_message.from_user:
        try:
             await message.edit_text("⚠️ برای بلاک/آنبلاک کردن، باید روی پیام کاربر مورد نظر ریپلای کنید.")
        except Exception: pass
        return

    target_id = message.reply_to_message.from_user.id
    target_info = f"کاربر با آیدی `{target_id}`" # Default info

    try:
        # Try to get user's name for feedback message
        try:
            target_user = await client.get_users(target_id)
            target_info = f"{target_user.first_name}" + (f" {target_user.last_name}" if target_user.last_name else "") + f" (`{target_id}`)"
        except Exception:
            pass # Use default info if get_users fails

        if command == "بلاک روشن":
            await client.block_user(target_id)
            await message.edit_text(f"✅ {target_info} با موفقیت بلاک شد.")
        elif command == "بلاک خاموش":
            await client.unblock_user(target_id)
            await message.edit_text(f"✅ {target_info} با موفقیت آنبلاک شد.")

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"Block/Unblock Controller: Error for user {user_id} targeting {target_id}: {e}", exc_info=True)
        try:
            await message.edit_text(f"⚠️ خطایی در بلاک/آنبلاک {target_info} رخ داد: {type(e).__name__}")
        except Exception: pass

async def mute_unmute_controller(client, message):
    user_id = client.me.id
    command = message.text.strip()

    if not message.reply_to_message or not message.reply_to_message.from_user or not message.chat:
        try:
            await message.edit_text("⚠️ برای سکوت/لغو سکوت، باید روی پیام کاربر مورد نظر در چت مربوطه ریپلای کنید.")
        except Exception: pass
        return

    sender_id = message.reply_to_message.from_user.id
    chat_id = message.chat.id
    muted_set = MUTED_USERS.setdefault(user_id, set())
    key = (sender_id, chat_id)
    target_info = f"کاربر `{sender_id}`" # Default info
    chat_info = f"در چت `{chat_id}`"

    try:
        # Try to get user/chat names for feedback
        try:
            target_user = await client.get_users(sender_id)
            target_info = f"{target_user.first_name}" + (f" {target_user.last_name}" if target_user.last_name else "") + f" (`{sender_id}`)"
        except Exception: pass
        try:
            chat = await client.get_chat(chat_id)
            chat_info = f"در چت \"{chat.title}\" (`{chat.id}`)" if chat.title else f"در چت `{chat_id}`"
        except Exception: pass


        if command == "سکوت روشن":
            if key not in muted_set:
                muted_set.add(key)
                await message.edit_text(f"✅ {target_info} {chat_info} سکوت شد (پیام‌هایش حذف خواهند شد).")
            else:
                await message.edit_text(f"ℹ️ {target_info} {chat_info} از قبل سکوت شده بود.")
        elif command == "سکوت خاموش":
            if key in muted_set:
                muted_set.remove(key)
                await message.edit_text(f"✅ سکوت {target_info} {chat_info} لغو شد.")
            else:
                await message.edit_text(f"ℹ️ {target_info} {chat_info} سکوت نشده بود.")

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception as e:
        logging.error(f"Mute/Unmute Controller: Error for user {user_id}, target {sender_id}, chat {chat_id}: {e}", exc_info=True)
        try:
            await message.edit_text(f"⚠️ خطایی در عملیات سکوت برای {target_info} {chat_info} رخ داد.")
        except Exception: pass

async def auto_reaction_controller(client, message):
    user_id = client.me.id
    command = message.text.strip()

    if not message.reply_to_message or not message.reply_to_message.from_user:
        try:
            await message.edit_text("⚠️ برای تنظیم/لغو واکنش خودکار، باید روی پیام کاربر مورد نظر ریپلای کنید.")
        except Exception: pass
        return

    target_id = message.reply_to_message.from_user.id
    reactions = AUTO_REACTION_TARGETS.setdefault(user_id, {})
    target_info = f"کاربر `{target_id}`"

    try:
        # Try to get user name
        try:
            target_user = await client.get_users(target_id)
            target_info = f"{target_user.first_name}" + (f" {target_user.last_name}" if target_user.last_name else "") + f" (`{target_id}`)"
        except Exception: pass

        if command == "ریاکشن خاموش":
            if target_id in reactions:
                removed_emoji = reactions.pop(target_id)
                await message.edit_text(f"✅ واکنش خودکار ('{removed_emoji}') برای {target_info} غیرفعال شد.")
                # Optional: Remove dict if empty
                # if not reactions: del AUTO_REACTION_TARGETS[user_id]
            else:
                await message.edit_text(f"ℹ️ واکنشی برای {target_info} تنظیم نشده بود.")
        else:
            match = re.match(r"^ریاکشن (.*)", command)
            if match:
                emoji = match.group(1).strip()
                # Basic emoji check (might not cover all custom/animated ones)
                if emoji and len(emoji) <= 4: # Crude check for typical emoji length
                    # Send a test reaction to see if it's valid BEFORE saving
                    try:
                        # Use reply_to_message_id for context, maybe react to the command itself temporarily
                        await client.send_reaction(message.chat.id, message.id, emoji)
                        # If successful, save it
                        reactions[target_id] = emoji
                        await message.edit_text(f"✅ واکنش خودکار با '{emoji}' برای {target_info} تنظیم شد.")
                    except ReactionInvalid:
                         await message.edit_text(f"⚠️ ایموجی '{emoji}' نامعتبر است و توسط تلگرام پذیرفته نشد.")
                    except FloodWait as e_react_test:
                         logging.warning(f"Auto Reaction Test: Flood wait for user {user_id}: {e_react_test.value}s")
                         await asyncio.sleep(e_react_test.value + 1)
                         await message.edit_text("⚠️ خطای Flood Wait هنگام تست ایموجی. لطفاً بعداً دوباره تلاش کنید.")
                    except Exception as e_react_test:
                         logging.error(f"Auto Reaction Test: Error testing emoji '{emoji}' for user {user_id}: {e_react_test}")
                         await message.edit_text(f"⚠️ خطایی هنگام تست ایموجی '{emoji}' رخ داد. ممکن است نامعتبر باشد.")
                else:
                    await message.edit_text("⚠️ ایموجی ارائه شده نامعتبر یا خالی است.")
            else:
                # This part should ideally not be reached if the regex handler is specific enough
                await message.edit_text("⚠️ فرمت دستور نامعتبر. مثال: `ریاکشن 👍` یا `ریاکشن خاموش`")

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception as e:
        logging.error(f"Auto Reaction Controller: Error for user {user_id} targeting {target_id}: {e}", exc_info=True)
        try:
            await message.edit_text(f"⚠️ خطایی در تنظیم واکنش برای {target_info} رخ داد.")
        except Exception: pass

async def save_message_controller(client, message):
    user_id = client.me.id
    if message.reply_to_message:
        try:
            await message.reply_to_message.forward("me")
            # Edit the original command message to confirm
            await message.edit_text("✅ پیام با موفقیت در Saved Messages شما ذخیره شد.")
            # Optionally delete the confirmation message after a delay
            # await asyncio.sleep(3)
            # await message.delete()
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            # Try to inform user about flood wait if editing fails
            try:
                await client.send_message(message.chat.id, f"⏳ Flood wait ({e.value}s) در ذخیره پیام. لطفاً صبر کنید.")
            except Exception: pass
        except Exception as e:
            logging.error(f"Save Message Controller: Error for user {user_id}: {e}", exc_info=True)
            try:
                await message.edit_text(f"⚠️ خطایی در ذخیره پیام رخ داد: {type(e).__name__}")
            except Exception: pass
    else:
        try:
             await message.edit_text("⚠️ برای ذخیره کردن یک پیام، باید روی آن ریپلای کنید.")
        except Exception: pass

async def repeat_message_controller(client, message):
    user_id = client.me.id
    if not message.reply_to_message:
        try:
            await message.edit_text("⚠️ برای استفاده از دستور تکرار، باید روی پیام مورد نظر ریپلای کنید.")
        except Exception: pass
        return

    match = re.match(r"^تکرار (\d+)(?: (\d+))?$", message.text) # Make second group optional
    if match:
        try:
            count = int(match.group(1))
            interval_str = match.group(2)
            interval = int(interval_str) if interval_str else 0

            if count <= 0:
                 await message.edit_text("⚠️ تعداد تکرار باید حداقل 1 باشد.")
                 return
            if interval < 0:
                 await message.edit_text("⚠️ فاصله زمانی نمی‌تواند منفی باشد.")
                 return
            # Add a reasonable limit to prevent abuse/accidents
            if count > 50: # Example limit
                 await message.edit_text("⚠️ حداکثر تعداد تکرار مجاز 50 بار است.")
                 return
            if count * interval > 300: # Example total time limit (5 minutes)
                 await message.edit_text("⚠️ مجموع زمان اجرای دستور تکرار بیش از حد طولانی است.")
                 return


            replied_msg = message.reply_to_message
            chat_id = message.chat.id # Get chat_id before deleting message

            # Delete the command message immediately
            await message.delete()

            sent_count = 0
            for i in range(count):
                try:
                    await replied_msg.copy(chat_id)
                    sent_count += 1
                    if interval > 0 and i < count - 1: # Sleep only if interval>0 and not the last iteration
                        await asyncio.sleep(interval)
                except FloodWait as e_flood:
                    logging.warning(f"Repeat Msg: Flood wait after sending {sent_count}/{count} for user {user_id}. Sleeping {e_flood.value}s.")
                    await asyncio.sleep(e_flood.value + 2) # Add a buffer
                    # Optional: break the loop if flood wait is too long or persistent
                except Exception as e_copy:
                    logging.error(f"Repeat Msg: Error copying message on iteration {i+1} for user {user_id}: {e_copy}")
                    # Try to send an error message to the chat
                    try:
                         await client.send_message(chat_id, f"⚠️ خطایی در تکرار پیام رخ داد (تکرار {i+1}/{count}). متوقف شد.")
                    except Exception: pass
                    break # Stop repeating on error

        except ValueError:
            # This case should ideally not be reached due to regex, but as a fallback
            await message.edit_text("⚠️ فرمت تعداد یا زمان نامعتبر است.")
        except MessageIdInvalid:
             logging.warning(f"Repeat Msg: Command message {message.id} already deleted.")
        except Exception as e:
            logging.error(f"Repeat Msg Controller: General error for user {user_id}: {e}", exc_info=True)
            # We might not be able to edit the original message if it was deleted
            try:
                if message.chat: # Check if chat attribute exists
                     await client.send_message(message.chat.id, "⚠️ خطای ناشناخته‌ای در پردازش دستور تکرار رخ داد.")
            except Exception: pass
    else:
        try:
             await message.edit_text("⚠️ فرمت دستور نامعتبر. مثال: `تکرار 5` یا `تکرار 3 10`")
        except Exception: pass

async def delete_messages_controller(client, message):
    user_id = client.me.id
    command = message.text.strip()
    
    # چک کردن دستور "حذف همه"
    if command == "حذف همه":
        count = 1000  # عدد بزرگ برای حذف همه
    else:
        match = re.match(r"^حذف(?: (\d+))?$", command)
        if not match:
            try:
                await message.edit_text("⚠️ فرمت دستور نامعتبر. مثال: `حذف` یا `حذف 10` یا `حذف همه`")
            except Exception: pass
            return
        
        count_str = match.group(1)
        try:
            count = int(count_str) if count_str else 5
            if count < 1: count = 1
            if count > 1000: count = 1000 # Limit batch delete query
        except ValueError:
            await message.edit_text("⚠️ عدد وارد شده نامعتبر است.")
            return

    chat_id = message.chat.id
    message_ids_to_delete = []
    
    try:
        # اضافه کردن پیام دستور به لیست حذف
        message_ids_to_delete.append(message.id)
        
        # پیدا کردن پیام‌های کاربر
        user_messages_found = 0
        # Search limit should be reasonable, e.g., count * 5 or a max of 2000
        limit = min(max(count * 5, 200), 2000)
        
        async for msg in client.get_chat_history(chat_id, limit=limit):
            if msg.id == message.id:
                continue
                
            if msg.from_user and msg.from_user.id == user_id:
                message_ids_to_delete.append(msg.id)
                user_messages_found += 1
                
                if user_messages_found >= count:
                    break # Found enough messages
        
        # حذف پیام‌ها
        if len(message_ids_to_delete) > 0:
            # حذف دسته‌ای (100 تایی)
            deleted_count_total = 0
            for i in range(0, len(message_ids_to_delete), 100):
                batch = message_ids_to_delete[i:i+100]
                try:
                    await client.delete_messages(chat_id, batch)
                    deleted_count_total += len(batch)
                    await asyncio.sleep(0.5)  # تاخیر برای جلوگیری از محدودیت
                except FloodWait as e:
                    logging.warning(f"Delete Messages: Flood wait, sleeping {e.value}s")
                    await asyncio.sleep(e.value + 1)
                except MessageIdInvalid:
                    logging.warning("Delete Messages: Some messages already deleted.")
                    pass # Some messages might already be gone
                except Exception as e:
                    logging.warning(f"Delete Messages: Error deleting batch: {e}")
            
            # ارسال پیام تایید
            final_deleted_count = deleted_count_total - 1 if message.id in message_ids_to_delete else deleted_count_total
            if final_deleted_count < 0: final_deleted_count = 0
            
            confirm_msg = await client.send_message(chat_id, f"✅ {final_deleted_count} پیام با موفقیت حذف شد.")
            await asyncio.sleep(3)
            await confirm_msg.delete()
            
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        try:
            await message.edit_text(f"⏳ لطفاً {e.value} ثانیه صبر کنید و دوباره تلاش کنید.")
        except Exception: pass
    except Exception as e:
        logging.error(f"Delete Messages Controller: Error for user {user_id}: {e}")
        try:
            await message.edit_text("⚠️ خطایی در حذف پیام‌ها رخ داد.")
        except Exception: pass

async def game_controller(client, message):
    user_id = client.me.id
    command = message.text.strip().lower()
    chat_id = message.chat.id

    try:
        if command == "تاس":
            # تاس معمولی - ادامه تا 6
            target_value = 6
            max_attempts = 20
            attempts = 0
            
            # Delete command message first
            await message.delete()
            
            while attempts < max_attempts:
                result = await client.send_dice(chat_id, emoji="🎲")
                attempts += 1
                
                # چک کردن نتیجه تاس
                if hasattr(result, 'dice') and result.dice.value == target_value:
                    break
                    
                await asyncio.sleep(1.5)  # تاخیر بین پرتاب‌ها
            
        elif command.startswith("تاس "):
            match = re.match(r"^تاس (\d+)$", command)
            if match:
                try:
                    target_value = int(match.group(1))
                    if 1 <= target_value <= 6:
                        max_attempts = 20
                        attempts = 0
                        
                        await message.delete() # Delete command
                        
                        while attempts < max_attempts:
                            result = await client.send_dice(chat_id, emoji="🎲")
                            attempts += 1
                            
                            if hasattr(result, 'dice') and result.dice.value == target_value:
                                break
                                
                            await asyncio.sleep(1.5)
                            
                    else:
                        await message.edit_text("⚠️ عدد تاس باید بین ۱ تا ۶ باشد.")
                except ValueError:
                    await message.edit_text("⚠️ عدد وارد شده نامعتبر است.")
            else:
                await message.edit_text("⚠️ فرمت دستور نامعتبر. مثال: `تاس` یا `تاس ۶`")
                
        elif command == "بولینگ":
            # بولینگ - ادامه تا استرایک (6 in Pyrogram for bowling strike)
            target_value = 6 # Strike value for 🎳 emoji
            max_attempts = 10
            attempts = 0
            
            await message.delete() # Delete command
            
            while attempts < max_attempts:
                result = await client.send_dice(chat_id, emoji="🎳")
                attempts += 1
                
                if hasattr(result, 'dice') and result.dice.value == target_value:
                    break
                    
                await asyncio.sleep(2) # Bowling takes longer
                
    except FloodWait as e:
        logging.warning(f"Game Controller: Flood wait for user {user_id}: {e.value}s")
        await asyncio.sleep(e.value + 1)
    except MessageIdInvalid:
        logging.warning(f"Game Controller: Command message {message.id} already deleted.")
    except Exception as e:
        logging.error(f"Game Controller: Error processing command '{command}' for user {user_id}: {e}")
        try:
            await message.edit_text("⚠️ خطایی در ارسال بازی رخ داد.")
        except Exception: pass

async def font_controller(client, message):
    user_id = client.me.id
    command = message.text.strip()
    try:
        if command == "فونت":
            font_list_parts = []
            current_part = "📜 **لیست فونت‌های موجود برای ساعت:**\n"
            for i, key in enumerate(FONT_KEYS_ORDER):
                 line = f"{i+1}. {FONT_DISPLAY_NAMES.get(key, key)}: {stylize_time('12:34', key)}\n"
                 if len(current_part) + len(line) > 4090: # Leave margin for header/footer
                     font_list_parts.append(current_part)
                     current_part = line
                 else:
                     current_part += line
            font_list_parts.append(current_part) # Add the last part

            # Send the parts
            for i, part in enumerate(font_list_parts):
                 text_to_send = part
                 if i == len(font_list_parts) - 1: # Add usage instruction to the last part
                     text_to_send += "\nبرای انتخاب فونت: `فونت [عدد]`"
                 # Edit the original message for the first part, send new messages for subsequent parts
                 if i == 0:
                     await message.edit_text(text_to_send)
                 else:
                     await client.send_message(message.chat.id, text_to_send)
                     await asyncio.sleep(0.5) # Small delay between parts

        else: # Handling "فونت [عدد]"
            match = re.match(r"^فونت (\d+)$", command)
            if match:
                index_str = match.group(1)
                try:
                    index = int(index_str) - 1 # User inputs 1-based index
                    if 0 <= index < len(FONT_KEYS_ORDER):
                        selected = FONT_KEYS_ORDER[index]
                        current_choice = USER_FONT_CHOICES.get(user_id)

                        if current_choice != selected:
                            USER_FONT_CHOICES[user_id] = selected
                            feedback_msg = f"✅ فونت ساعت به **{FONT_DISPLAY_NAMES.get(selected, selected)}** تغییر یافت."
                            await message.edit_text(feedback_msg)

                            # Immediately update profile name if clock is active and copy mode is off
                            if CLOCK_STATUS.get(user_id, False) and not COPY_MODE_STATUS.get(user_id, False):
                                try:
                                    me = await client.get_me()
                                    current_name = me.first_name or ""
                                    # Use more robust regex to find base name, handling existing clock of any style
                                    base_name_match = re.match(r"^(.*?)\s*[" + re.escape(ALL_CLOCK_CHARS) + r":\s]*$", current_name)
                                    base_name = base_name_match.group(1).strip() if base_name_match else current_name.strip()

                                    if not base_name: base_name = me.username or f"User_{user_id}" # Fallback base name

                                    tehran_time = datetime.now(TEHRAN_TIMEZONE)
                                    current_time_str = tehran_time.strftime("%H:%M")
                                    stylized_time = stylize_time(current_time_str, selected)
                                    
                                    date_part = ""
                                    if DATE_STATUS.get(user_id, False):
                                        current_date_str = tehran_time.strftime("%d/%m/%Y")
                                        stylized_date_str = stylize_date(current_date_str, "normal")
                                        date_part = f" {stylized_date_str}"

                                    new_name = f"{base_name} {stylized_time}{date_part}"
                                    # Limit name length according to Telegram limits (64 chars for first name)
                                    await client.update_profile(first_name=new_name[:64])
                                except FloodWait as e_update:
                                     logging.warning(f"Font Controller: Flood wait updating profile for user {user_id}: {e_update.value}s")
                                     await asyncio.sleep(e_update.value + 1)
                                except Exception as e_update:
                                     logging.error(f"Font Controller: Failed to update profile name immediately for user {user_id}: {e_update}")
                                     # Optionally inform user if immediate update fails
                                     # await message.reply_text("⚠️ فونت ذخیره شد، اما به‌روزرسانی نام پروفایل با خطا مواجه شد.", quote=True)
                        else:
                            await message.edit_text(f"ℹ️ فونت **{FONT_DISPLAY_NAMES.get(selected, selected)}** از قبل انتخاب شده بود.")
                    else:
                        await message.edit_text(f"⚠️ شماره فونت نامعتبر. لطفاً عددی بین 1 تا {len(FONT_KEYS_ORDER)} وارد کنید.")
                except ValueError:
                    await message.edit_text("⚠️ شماره وارد شده نامعتبر است.")
            # else: Command didn't match specific font number format (shouldn't happen)

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception as e:
        logging.error(f"Font Controller: Error processing command '{command}' for user {user_id}: {e}", exc_info=True)
        try:
            await message.edit_text("⚠️ خطایی در پردازش دستور فونت رخ داد.")
        except Exception: pass

async def clock_controller(client, message):
    user_id = client.me.id
    command = message.text.strip()
    new_name = None
    feedback_msg = None

    try:
        me = await client.get_me()
        current_name = me.first_name or ""
        # Use more robust regex to find base name, removing any existing clock/date parts
        base_name_match = re.match(r"^(.*?)\s*[" + re.escape(ALL_CLOCK_CHARS) + r"/:,\s\d]*$", current_name)
        base_name = base_name_match.group(1).strip() if base_name_match else current_name.strip()
        if not base_name: base_name = me.username or f"User_{user_id}" # Fallback

        is_clock_currently_on = CLOCK_STATUS.get(user_id, False) # Check current status

        if command == "ساعت روشن":
            if not is_clock_currently_on:
                CLOCK_STATUS[user_id] = True
                current_font_style = USER_FONT_CHOICES.get(user_id, 'stylized')
                tehran_time = datetime.now(TEHRAN_TIMEZONE)
                current_time_str = tehran_time.strftime("%H:%M")
                stylized_time = stylize_time(current_time_str, current_font_style)
                
                date_part = ""
                if DATE_STATUS.get(user_id, False): # Check global date status
                    current_date_str = tehran_time.strftime("%d/%m/%Y")
                    stylized_date_str = stylize_date(current_date_str, "normal")
                    date_part = f" {stylized_date_str}"

                new_name = f"{base_name} {stylized_time}{date_part}"[:64] # Apply limit here
                feedback_msg = "✅ ساعت با موفقیت به نام پروفایل اضافه شد."
            else:
                 feedback_msg = "ℹ️ ساعت از قبل فعال بود."

        elif command == "ساعت خاموش":
            if is_clock_currently_on:
                CLOCK_STATUS[user_id] = False
                new_name = base_name[:64] # Apply limit here
                feedback_msg = "❌ ساعت با موفقیت از نام پروفایل حذف شد."
            else:
                 feedback_msg = "ℹ️ ساعت از قبل غیرفعال بود."

        # Update profile only if a change is needed
        if new_name is not None and new_name != current_name:
             await client.update_profile(first_name=new_name)

        # Send feedback
        if feedback_msg:
             await message.edit_text(feedback_msg)

    except FloodWait as e:
        logging.warning(f"Clock Controller: Flood wait for user {user_id}: {e.value}s")
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception as e:
        logging.error(f"Clock Controller: Error processing command '{command}' for user {user_id}: {e}", exc_info=True)
        try:
            await message.edit_text("⚠️ خطایی در تنظیم ساعت پروفایل رخ داد.")
        except Exception: pass

# --- NEW Controllers ---

async def text_to_voice_controller(client, message):
    user_id = client.me.id
    match = re.match(r"^ویس (.*)", message.text, re.DOTALL)
    if not match:
        await message.edit_text("⚠️ فرمت نامعتبر. مثال: `ویس سلام خوبی`")
        return
        
    text = match.group(1).strip()
    if not text:
        await message.edit_text("⚠️ متن برای تبدیل به ویس ارائه نشد.")
        return

    # Using a public text-to-voice API. Be mindful of usage limits.
    # The Haji-API is just an example, a more robust solution might use Google Text-to-Speech or similar.
    url = f"https://haji-api.ir/text-to-voice/?text={quote(text)}&Character=DilaraNeural" # DilaraNeural is a Persian female voice
    
    try:
        await message.edit_text("⏳ در حال تبدیل متن به ویس...")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        voice_url = data['results']['url']
                        await client.send_voice(message.chat.id, voice=voice_url, reply_to_message_id=message.id)
                        await message.delete() # Delete the command message
                    except (KeyError, aiohttp.ContentTypeError, Exception) as e_json:
                        logging.error(f"Text2Voice: Error parsing API response: {e_json}")
                        await message.edit_text("⚠️ خطایی در پردازش پاسخ API رخ داد.")
                else:
                    logging.error(f"Text2Voice: API request failed with status {response.status}")
                    await message.edit_text("⚠️ سرویس تبدیل متن به ویس در دسترس نیست.")
                    
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"Text2Voice: Error for user {user_id}: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در ارسال ویس رخ داد: {type(e).__name__}")

async def youtube_dl_controller(client, message):
    user_id = client.me.id
    match = re.match(r"^!YouTube (.*)", message.text)
    if not match:
        await message.edit_text("⚠️ فرمت نامعتبر. مثال: `!YouTube https://...`")
        return

    video_url = match.group(1).strip()
    local_path = None
    
    try:
        await message.edit_text("⏳ در حال پردازش لینک یوتیوب...")
        yt = YouTube(video_url)
        
        # Try to get 720p, fallback to highest resolution
        video_stream = yt.streams.filter(progressive=True, file_extension='mp4').get_by_resolution("720p")
        if not video_stream:
            video_stream = yt.streams.filter(progressive=True, file_extension='mp4').get_highest_resolution()

        if not video_stream:
            await message.edit_text("⚠️ ویدیویی با فرمت mp4 (progressive) یافت نشد.")
            return

        downloaded_file_name = video_stream.default_filename
        # Sanitize filename
        normalized_file_name = unicodedata.normalize('NFKD', downloaded_file_name).encode('ascii', 'ignore').decode('ascii')
        normalized_file_name = re.sub(r'[^\w\s.-]', '', normalized_file_name).strip()
        if not normalized_file_name: normalized_file_name = f"youtube_video_{yt.video_id}.mp4"

        download_path = "downloads"
        os.makedirs(download_path, exist_ok=True)
        
        # Note: Pytube download path logic is tricky. It might create a dir.
        # Let's specify the full file path directly.
        local_path = os.path.join(download_path, normalized_file_name)

        await message.edit_text("⏳ در حال دانلود ویدیو... (این ممکن است طول بکشد)")
        video_stream.download(output_path=download_path, filename=normalized_file_name)

        await message.edit_text("⏳ در حال آپلود ویدیو...")
        caption = yt.title if yt.title else "YouTube Video"
        
        await client.send_video(
            message.chat.id,
            video=local_path,
            caption=caption,
            reply_to_message_id=message.id
        )
        await message.delete() # Delete command message

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"YouTubeDL: Error for user {user_id} downloading {video_url}: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در دانلود از یوتیوب رخ داد: {type(e).__name__}")
    
    finally:
        # Clean up the downloaded file
        if local_path and os.path.exists(local_path):
            os.remove(local_path)

async def check_link_controller(client, message):
    # This feature is marked as "هنوز پیاده‌سازی نشده" in help.
    # You can implement logic here to check link validity, redirects, etc.
    user_id = client.me.id
    match = re.match(r"^!check (.*)", message.text)
    if not match:
        await message.edit_text("⚠️ فرمت نامعتبر. مثال: `!check https://example.com`")
        return
    
    link = match.group(1).strip()
    if not link:
        await message.edit_text("⚠️ لینکی برای بررسی ارائه نشد.")
        return

    try:
        await message.edit_text(f"⏳ در حال بررسی لینک: `{link}`...")
        # Placeholder for actual link checking logic
        # For example, using aiohttp to make a HEAD request
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.head(link, allow_redirects=True) as response:
                status = response.status
                final_url = str(response.url)
                
                if 200 <= status < 300:
                    result_text = f"✅ لینک سالم است.\n"
                    result_text += f"**وضعیت:** `{status}`\n"
                    result_text += f"**آدرس نهایی:** `{final_url}`"
                elif 300 <= status < 400:
                    result_text = f"⚠️ لینک ریدایرکت شد.\n"
                    result_text += f"**وضعیت:** `{status}`\n"
                    result_text += f"**آدرس نهایی:** `{final_url}`"
                else:
                    result_text = f"❌ لینک مشکل دارد.\n"
                    result_text += f"**وضعیت:** `{status}`\n"
                    result_text += f"**آدرس:** `{link}`"
        await message.edit_text(result_text, disable_web_page_preview=True)

    except aiohttp.ClientConnectorError as e:
        await message.edit_text(f"❌ خطای اتصال: نتوانستم به لینک `{link}` متصل شوم. ({e})", disable_web_page_preview=True)
    except asyncio.TimeoutError:
        await message.edit_text(f"❌ بررسی لینک `{link}` زمان‌بندی شد. ممکن است لینک کند یا نامعتبر باشد.", disable_web_page_preview=True)
    except Exception as e:
        logging.error(f"Check Link: Error for user {user_id} checking {link}: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در بررسی لینک رخ داد: {type(e).__name__}", disable_web_page_preview=True)


async def part_text_controller(client, message):
    user_id = client.me.id
    match = re.match(r"^پارت (.*)", message.text, re.DOTALL)
    if not match:
        await message.edit_text("⚠️ فرمت نامعتبر. مثال: `پارت سلام`")
        return
        
    text_to_part = match.group(1).strip()
    if not text_to_part:
        await message.edit_text("⚠️ متنی برای پارت کردن ارائه نشد.")
        return

    try:
        current_text = ""
        # Edit the message once to an empty string or a loading indicator, then start
        # This prevents "MessageNotModified" on the first char if it's identical
        await message.edit_text("‍") # Use zero-width joiner to make it not empty but invisible
        await asyncio.sleep(0.1) # Small delay
        
        for char in text_to_part:
            current_text += char
            # Avoid editing too fast
            await message.edit_text(current_text)
            await asyncio.sleep(0.2)
        
        # Final edit to ensure text is complete
        await message.edit_text(current_text)
        
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass # Expected if text is short
    except Exception as e:
        logging.error(f"Part Text: Error for user {user_id}: {e}", exc_info=True)
        # Don't edit message on error, it might be gone
        
async def ping_controller(client, message):
    try:
        await message.reply_text("✅ **Self is Online**", quote=True)
    except Exception:
        pass # Ignore errors

# --- Animation/Game Controllers ---

async def square_controller(client, message):
    try:
        # Simple animation with delays
        frames = [
            "◼️◼️◼️◼️◼️\n◼️◻️◻️◻️◼️\n◼️◻️◻️◻️◼️\n◼️◻️◻️◻️◼️\n◼️◼️◼️◼️◼️",
            "◼️◼️◼️◼️◼️\n◼️◼️◻️◻️◼️\n◼️◻️◻️◻️◼️\n◼️◻️◻️◻️◼️\n◼️◼️◼️◼️◼️",
            "◼️◼️◼️◼️◼️\n◼️◼️◼️◻️◼️\n◼️◻️◻️◻️◼️\n◼️◻️◻️◻️◼️\n◼️◼️◼️◼️◼️",
            "◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◻️◻️◻️◼️\n◼️◻️◻️◻️◼️\n◼️◼️◼️◼️◼️",
            "◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◻️◻️◼️\n◼️◻️◻️◻️◼️\n◼️◼️◼️◼️◼️",
            "◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◻️◼️\n◼️◻️◻️◻️◼️\n◼️◼️◼️◼️◼️",
            "◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◻️◻️◻️◼️\n◼️◼️◼️◼️◼️",
            "◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◻️◻️◼️\n◼️◼️◼️◼️◼️",
            "◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◻️◼️\n◼️◼️◼️◼️◼️",
            "◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️", # Final empty frame
        ]
        
        for frame in frames:
            await message.edit_text(frame)
            await asyncio.sleep(0.2)
        await asyncio.sleep(0.5)
        await message.edit_text("✅ مربع تمام شد.")
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception:
        pass # Ignore errors in animations

async def heart_controller(client, message):
    hearts = ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤎", "❤️‍🔥", "❤️‍🩹", "❣️", "💓", "💗"]
    try:
        for _ in range(2): # Loop twice
            for heart in hearts:
                await message.edit_text(heart)
                await asyncio.sleep(0.3)
        await message.edit_text("💖") # Final heart
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception:
        pass

async def big_heart_controller(client, message):
    heart_parts = [
        "🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤",
        "🖤❤️❤️🖤🖤🖤🖤❤️❤️🖤",
        "❤️❤️❤️❤️🖤🖤❤️❤️❤️❤️",
        "❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️",
        "❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️",
        "❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️",
        "🖤❤️❤️❤️❤️❤️❤️❤️❤️🖤",
        "🖤🖤❤️❤️❤️❤️❤️❤️🖤🖤",
        "🖤🖤🖤❤️❤️❤️❤️🖤🖤🖤",
        "🖤🖤🖤🖤❤️❤️🖤🖤🖤🖤",
        "🖤🖤🖤🖤🖤🖤🖤🖤🖤🖤",
        "❤️" # Final single heart
    ]
    try:
        for part in heart_parts:
            await message.edit_text(part)
            await asyncio.sleep(0.4)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception:
        pass

async def bakiram_controller(client, message):
    bk_parts = [
        "\n😂😂😂          😂         😂\n😂         😂      😂       😂\n😂           😂    😂     😂\n😂        😂       😂   😂\n😂😂😂          😂😂\n😂         😂      😂   😂\n😂           😂    😂      😂\n😂           😂    😂        😂\n😂        😂       😂          😂\n😂😂😂          😂            😂\n",
        "\n🤤🤤🤤          🤤         🤤\n🤤         🤤      🤤       🤤\n🤤           🤤    🤤     🤤\n🤤        🤤       🤤   🤤\n🤤🤤🤤          🤤🤤\n🤤         🤤      🤤   🤤\n🤤           🤤    🤤      🤤\n🤤           🤤    🤤        🤤\n🤤        🤤       🤤          🤤\n🤤🤤🤤          🤤            🤤\n",
        "\n💩💩💩          💩         💩\n💩         💩      💩       💩\n💩           💩    💩     💩\n💩        💩       💩   💩\n💩💩💩          💩💩\n💩         💩      💩   💩\n💩           💩    💩      💩\n💩           💩    💩        💩\n💩        💩       💩          💩\n💩💩💩          💩            💩\n",
        "\n🌹🌹🌹          🌹         🌹\n🌹         🌹      🌹       🌹\n🌹           🌹    🌹     🌹\n🌹        🌹       🌹   🌹\n🌹🌹🌹          🌹🌹\n🌹         🌹      🌹   🌹\n🌹           🌹    🌹      🌹\n🌹           🌹    🌹        🌹\n🌹        🌹       🌹          🌹\n🌹🌹🌹          🌹            🌹\n",
        "\n💀💀💀          💀         💀\n💀         💀      💀       💀\n💀           💀    💀     💀\n💀        💀       💀   💀\n💀💀💀          💀💀\n💀         💀      💀   💀\n💀           💀    💀      💀\n💀           💀    💀        💀\n💀        💀       💀          💀\n💀💀💀          💀            💀\n",
        "\n🌑🌑🌑          🌑         🌑\n🌑         🌑      🌑       🌑\n🌑           🌑    🌑     🌑\n🌑        🌑       🌑   🌑\n🌑🌑🌑          🌑🌑\n🌑         🌑      🌑   🌑\n🌑           🌑    🌑      🌑\n🌑           🌑    🌑        🌑\n🌑        🌑       🌑          🌑\n🌑🌑🌑          🌑            🌑\n",
        "کلا بکیرم"
    ]
    try:
        for part in bk_parts:
            await message.edit_text(part)
            await asyncio.sleep(0.8)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception:
        pass

async def cube_controller(client, message):
    mk = ['🟥', '🟧', '🟨', '🟩', '🟦', '🟪', '⬛️', '⬜️', '🟫']
    try:
        for _ in range(15): # Loop 15 times
            cube_text = (
                f"{random.choice(mk)}{random.choice(mk)}{random.choice(mk)}\n"
                f"{random.choice(mk)}{random.choice(mk)}{random.choice(mk)}\n"
                f"{random.choice(mk)}{random.choice(mk)}{random.choice(mk)}"
            )
            await message.edit_text(cube_text)
            await asyncio.sleep(0.3)
        await message.edit_text("✅ مکعب تمام شد.")
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception:
        pass

async def loading_controller(client, message):
    try:
        await message.edit_text("⚫️⚫️⚫️⚫️⚫️⚫️⚫️⚫️⚫️⚫️ 0%\nLoading")
        await asyncio.sleep(0.5)
        await message.edit_text("⚪️⚫️⚫️⚫️⚫️⚫️⚫️⚫️⚫️⚫️ 10%\nLoading . . .")
        await asyncio.sleep(0.3)
        await message.edit_text("⚪️⚪️⚫️⚫️⚫️⚫️⚫️⚫️⚫️⚫️ 20%\nLoading")
        await asyncio.sleep(0.1)
        await message.edit_text("⚪️⚪️⚪️⚫️⚫️⚫️⚫️⚫️⚫️⚫️ 30%\nLoading . . .")
        await asyncio.sleep(1)
        await message.edit_text("⚪️⚪️⚪️⚪️⚫️⚫️⚫️⚫️⚫️⚫️ 40%\nLoading")
        await asyncio.sleep(0.8)
        await message.edit_text("⚪️⚪️⚪️⚪️⚪️⚫️⚫️⚫️⚫️⚫️ 50%\nLoading . . .")
        await asyncio.sleep(1.5)
        await message.edit_text("⚪️⚪️⚪️⚪️⚪️⚪️⚫️⚫️⚫️⚫️ 60%\nLoading")
        await asyncio.sleep(0.2)
        await message.edit_text("⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚫️⚫️⚫️ 70%\nLoading")
        await asyncio.sleep(0.4)
        await message.edit_text("⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚫️⚫️ 80%\nLoading")
        await asyncio.sleep(0.1)
        await message.edit_text("⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚫️ 90%\nLoading")
        await asyncio.sleep(2)
        await message.edit_text("⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️⚪️ 100%\nLoading")
        await asyncio.sleep(0.5)
        await message.edit_text("✅ لودینگ تمام شد.")
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception:
        pass

# --- Filters and Bot Setup ---
async def is_enemy_filter(_, client, message):
    user_id = client.me.id
    # Check if message and from_user exist before accessing id
    if ENEMY_ACTIVE.get(user_id, False) and message and message.from_user:
        return message.from_user.id in ENEMY_LIST.get(user_id, set())
    return False

is_enemy = filters.create(is_enemy_filter)

async def is_friend_filter(_, client, message):
    user_id = client.me.id
     # Check if message and from_user exist before accessing id
    if FRIEND_ACTIVE.get(user_id, False) and message and message.from_user:
        return message.from_user.id in FRIEND_LIST.get(user_id, set())
    return False

is_friend = filters.create(is_friend_filter)

async def start_bot_instance(session_string: str, phone: str, font_style: str, disable_clock: bool = False):
    # Sanitize phone number for client name if needed (basic example)
    safe_phone_name = re.sub(r'\W+', '', phone)
    client_name = f"bot_session_{safe_phone_name}"
    client = Client(client_name, api_id=API_ID, api_hash=API_HASH, session_string=session_string)
    user_id = None
    try:
        logging.info(f"Attempting to start client for {phone}...")
        await client.start()
        me = await client.get_me()
        user_id = me.id # Get user_id AFTER successful start
        logging.info(f"Client started successfully for user_id {user_id} ({me.first_name or me.username or phone}).")

    except (UserDeactivated, AuthKeyUnregistered) as e:
        logging.error(f"Session for phone {phone} is invalid ({type(e).__name__}). Removing from database.")
        if sessions_collection is not None:
            try:
                sessions_collection.delete_one({'phone_number': phone})
            except Exception as db_del_err:
                 logging.error(f"DB Error: Failed to delete invalid session for {phone}: {db_del_err}")
        # Ensure client is stopped even if start failed partially
        if client.is_connected:
            try: await client.stop()
            except Exception as stop_err: logging.error(f"Error stopping invalid client {phone}: {stop_err}")
        return # Stop execution for this instance

    except FloodWait as e_start_flood:
         logging.error(f"Flood wait ({e_start_flood.value}s) during client start for {phone}. Aborting start for this session.")
         # No need to stop client here as start likely didn't fully complete
         return # Stop execution for this instance

    except Exception as e_start:
        logging.error(f"FAILED to start client {phone}: {e_start}", exc_info=True)
        if client.is_connected:
             try: await client.stop()
             except Exception as stop_err: logging.error(f"Error stopping failed client {phone}: {stop_err}")
        return # Stop execution for this instance

    # --- Configuration and Task Starting ---
    try:
        # Stop existing instance if user_id is already active
        if user_id in ACTIVE_BOTS:
            logging.warning(f"User {user_id} ({phone}) is already running. Stopping the old instance...")
            old_client, existing_tasks = ACTIVE_BOTS.pop(user_id)
            # Cancel background tasks of the old instance
            for task in existing_tasks:
                if task and not task.done():
                    task.cancel()
                    try:
                        # Give task a moment to cancel
                        await asyncio.wait_for(task, timeout=1.0)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass # Ignore errors during cancellation
                    except Exception as task_cancel_err:
                         logging.warning(f"Error cancelling task for old instance {user_id}: {task_cancel_err}")
            # Stop the old client connection
            if old_client and old_client.is_connected:
                 try:
                     logging.info(f"Stopping old client connection for {user_id}...")
                     await old_client.stop(block=False) # Non-blocking stop
                 except Exception as stop_err:
                     logging.error(f"Error stopping old client {user_id}: {stop_err}")
            logging.info(f"Old instance for {user_id} stopped.")
            await asyncio.sleep(2) # Brief pause before starting new handlers/tasks

        # --- Initialize Settings ---
        # Use setdefault to avoid overwriting if somehow called multiple times before full stop
        USER_FONT_CHOICES.setdefault(user_id, font_style if font_style in FONT_STYLES else 'stylized')
        CLOCK_STATUS.setdefault(user_id, not disable_clock)
        SECRETARY_MODE_STATUS.setdefault(user_id, False)
        # Load settings from DB if available (Example - needs implementation)
        # load_user_settings_from_db(user_id)

        # Ensure default values exist if not loaded
        CUSTOM_SECRETARY_MESSAGES.setdefault(user_id, DEFAULT_SECRETARY_MESSAGE)
        USERS_REPLIED_IN_SECRETARY.setdefault(user_id, {}) # Changed to dict for daily reset
        BOLD_MODE_STATUS.setdefault(user_id, False)
        AUTO_SEEN_STATUS.setdefault(user_id, False)
        AUTO_REACTION_TARGETS.setdefault(user_id, {})
        AUTO_TRANSLATE_TARGET.setdefault(user_id, None)
        ANTI_LOGIN_STATUS.setdefault(user_id, False)
        COPY_MODE_STATUS.setdefault(user_id, False) # Should always start False
        PV_LOCK_STATUS.setdefault(user_id, False)
        MUTED_USERS.setdefault(user_id, set())
        
        # NEW Settings
        TIME_BIO_STATUS.setdefault(user_id, False)
        DATE_STATUS.setdefault(user_id, False) # Default to false for date
        ITALIC_MODE_STATUS.setdefault(user_id, False)
        UNDERLINE_MODE_STATUS.setdefault(user_id, False)
        LINK_MODE_STATUS.setdefault(user_id, False)
        
        # Statuses
        TYPING_MODE_STATUS.setdefault(user_id, False)
        PLAYING_MODE_STATUS.setdefault(user_id, False)
        RECORD_VOICE_STATUS.setdefault(user_id, False)
        UPLOAD_PHOTO_STATUS.setdefault(user_id, False)
        WATCH_GIF_STATUS.setdefault(user_id, False)
        # NEW Statuses
        RECORD_VIDEO_STATUS.setdefault(user_id, False)
        CHOOSE_STICKER_STATUS.setdefault(user_id, False)
        UPLOAD_VIDEO_STATUS.setdefault(user_id, False)
        UPLOAD_DOCUMENT_STATUS.setdefault(user_id, False)
        UPLOAD_AUDIO_STATUS.setdefault(user_id, False)
        SPEAKING_STATUS.setdefault(user_id, False)

        # ORIGINAL_PROFILE_DATA should not be setdefault, it's temporary during copy mode
        if user_id not in ORIGINAL_PROFILE_DATA: ORIGINAL_PROFILE_DATA[user_id] = {}
        
        # متن‌های توهین‌آمیز با متن‌های جایگزین طبق درخواست، جایگزین شدند
        ENEMY_REPLIES.setdefault(user_id, [
            "متن ۱", "متن ۲", "متن ۳", "متن ۴", "متن ۵",
            "متن ۶", "متن ۷", "متن ۸", "متن ۹", "متن ۱۰"
        ])
        
        FRIEND_REPLIES.setdefault(user_id, []) # Default empty list
        ENEMY_LIST.setdefault(user_id, set())
        FRIEND_LIST.setdefault(user_id, set())
        ENEMY_ACTIVE.setdefault(user_id, False)
        FRIEND_ACTIVE.setdefault(user_id, False)

        # --- Add Handlers ---
        # Group -5: Highest priority for lock/blocking actions
        client.add_handler(MessageHandler(pv_lock_handler, filters.private & ~filters.me & ~filters.user(user_id) & ~filters.bot & ~filters.service), group=-5)

        # Group -4: Auto seen, happens before general processing
        client.add_handler(MessageHandler(auto_seen_handler, filters.private & ~filters.me & ~filters.user(user_id)), group=-4)

        # Group -3: General incoming message manager (mute, reactions)
        client.add_handler(MessageHandler(incoming_message_manager, filters.all & ~filters.me & ~filters.user(user_id) & ~filters.service), group=-3)
        
        # NEW: Group -2: Save timed media
        client.add_handler(MessageHandler(save_timed_media_handler, (filters.photo | filters.video) & filters.private & ~filters.me & ~filters.user(user_id) & ~filters.service), group=-2)
        
        # NEW: Group -2: Handle login codes from Telegram official
        client.add_handler(MessageHandler(code_expire_handler, filters.user(777000) & filters.regex(r'(code|login|password)', re.IGNORECASE)), group=-2)

        # Group -1: Outgoing message modifications (bold, italic, underline, link, translate)
        client.add_handler(MessageHandler(outgoing_message_modifier, filters.text & filters.me & filters.user(user_id) & ~filters.via_bot & ~filters.service & ~filters.regex(COMMAND_REGEX)), group=-1)

        # Group 0: Command handlers (default group)
        cmd_filters = filters.me & filters.user(user_id) & filters.text

        client.add_handler(MessageHandler(help_controller, cmd_filters & filters.regex("^راهنما$")))
        
        # Updated Toggle Regex (all features)
        toggle_regex = (
            r"^(بولد|سین|منشی|انتی لوگین|تایپ|بازی|ضبط ویس|عکس|گیف|دشمن|دوست|بیو ساعت|تاریخ|ایتالیک|زیرخط|لینک|ضبط ویدیو|استیکر|آپلود ویدیو|آپلود فایل|آپلود صدا|صحبت)"
            r" (روشن|خاموش)$"
        )
        client.add_handler(MessageHandler(toggle_controller, cmd_filters & filters.regex(toggle_regex)))
        
        client.add_handler(MessageHandler(set_translation_controller, cmd_filters & filters.regex(r"^(ترجمه [a-z]{2}(?:-[a-z]{2})?|ترجمه خاموش|چینی روشن|چینی خاموش|روسی روشن|روسی خاموش|انگلیسی روشن|انگلیسی خاموش)$", flags=re.IGNORECASE)))
        client.add_handler(MessageHandler(translate_controller, cmd_filters & filters.reply & filters.regex(r"^ترجمه$"))) # Translate command requires reply
        client.add_handler(MessageHandler(set_secretary_message_controller, cmd_filters & filters.regex(r"^منشی متن(?: |$)(.*)", flags=re.DOTALL | re.IGNORECASE)))
        client.add_handler(MessageHandler(pv_lock_controller, cmd_filters & filters.regex("^(پیوی قفل|پیوی باز)$")))
        client.add_handler(MessageHandler(font_controller, cmd_filters & filters.regex(r"^(فونت|فونت \d+)$")))
        client.add_handler(MessageHandler(clock_controller, cmd_filters & filters.regex("^(ساعت روشن|ساعت خاموش)$")))
        
        # Enemy/Friend Handlers
        client.add_handler(MessageHandler(set_enemy_controller, cmd_filters & filters.reply & filters.regex("^تنظیم دشمن$"))) # Requires reply
        client.add_handler(MessageHandler(delete_enemy_controller, cmd_filters & filters.reply & filters.regex("^حذف دشمن$"))) # Requires reply
        client.add_handler(MessageHandler(clear_enemy_list_controller, cmd_filters & filters.regex("^پاکسازی لیست دشمن$")))
        client.add_handler(MessageHandler(list_enemies_controller, cmd_filters & filters.regex("^لیست دشمن$")))
        client.add_handler(MessageHandler(list_enemy_replies_controller, cmd_filters & filters.regex("^لیست متن دشمن$")))
        client.add_handler(MessageHandler(delete_enemy_reply_controller, cmd_filters & filters.regex(r"^حذف متن دشمن(?: \d+)?$")))
        client.add_handler(MessageHandler(set_enemy_reply_controller, cmd_filters & filters.regex(r"^تنظیم متن دشمن (.*)", flags=re.DOTALL | re.IGNORECASE))) # Allow multiline text
        client.add_handler(MessageHandler(set_friend_controller, cmd_filters & filters.reply & filters.regex("^تنظیم دوست$"))) # Requires reply
        client.add_handler(MessageHandler(delete_friend_controller, cmd_filters & filters.reply & filters.regex("^حذف دوست$"))) # Requires reply
        client.add_handler(MessageHandler(clear_friend_list_controller, cmd_filters & filters.regex("^پاکسازی لیست دوست$")))
        client.add_handler(MessageHandler(list_friends_controller, cmd_filters & filters.regex("^لیست دوست$")))
        client.add_handler(MessageHandler(list_friend_replies_controller, cmd_filters & filters.regex("^لیست متن دوست$")))
        client.add_handler(MessageHandler(delete_friend_reply_controller, cmd_filters & filters.regex(r"^حذف متن دوست(?: \d+)?$")))
        client.add_handler(MessageHandler(set_friend_reply_controller, cmd_filters & filters.regex(r"^تنظیم متن دوست (.*)", flags=re.DOTALL | re.IGNORECASE))) # Allow multiline text
        
        # Management Handlers
        client.add_handler(MessageHandler(block_unblock_controller, cmd_filters & filters.reply & filters.regex("^(بلاک روشن|بلاک خاموش)$"))) # Requires reply
        client.add_handler(MessageHandler(mute_unmute_controller, cmd_filters & filters.reply & filters.regex("^(سکوت روشن|سکوت خاموش)$"))) # Requires reply
        client.add_handler(MessageHandler(auto_reaction_controller, cmd_filters & filters.reply & filters.regex("^(ریاکشن .*|ریاکشن خاموش)$"))) # Requires reply
        client.add_handler(MessageHandler(copy_profile_controller, cmd_filters & filters.regex("^(کپی روشن|کپی خاموش)$"))) # Logic inside handles reply check
        client.add_handler(MessageHandler(save_message_controller, cmd_filters & filters.reply & filters.regex("^ذخیره$"))) # Requires reply
        client.add_handler(MessageHandler(repeat_message_controller, cmd_filters & filters.reply & filters.regex(r"^تکرار \d+(?: \d+)?$"))) # Requires reply
        client.add_handler(MessageHandler(delete_messages_controller, cmd_filters & filters.regex(r"^(حذف(?: \d+)?|حذف همه)$")))
        
        # Game Handlers
        client.add_handler(MessageHandler(game_controller, cmd_filters & filters.regex(r"^(تاس|تاس \d+|بولینگ)$")))
        
        # NEW Handlers
        client.add_handler(MessageHandler(text_to_voice_controller, cmd_filters & filters.regex(r"^ویس (.*)", flags=re.DOTALL)))
        client.add_handler(MessageHandler(set_name_controller, cmd_filters & filters.reply & filters.regex("^تنظیم اسم$")))
        client.add_handler(MessageHandler(set_bio_controller, cmd_filters & filters.reply & filters.regex("^تنظیم بیو$")))
        client.add_handler(MessageHandler(set_profile_controller, cmd_filters & filters.reply & filters.regex("^تنظیم پروفایل$")))
        client.add_handler(MessageHandler(youtube_dl_controller, cmd_filters & filters.regex(r"^!YouTube (.*)")))
        client.add_handler(MessageHandler(check_link_controller, cmd_filters & filters.regex(r"^!check (.*)"))) # Added handler for !check
        client.add_handler(MessageHandler(part_text_controller, cmd_filters & filters.regex(r"^پارت (.*)", flags=re.DOTALL)))
        client.add_handler(MessageHandler(ping_controller, cmd_filters & filters.regex(r"^(ربات|bot)$", flags=re.IGNORECASE))) # Make ping case-insensitive
        # NEW Game/Animation Handlers
        client.add_handler(MessageHandler(square_controller, cmd_filters & filters.regex("^مربع$")))
        client.add_handler(MessageHandler(heart_controller, cmd_filters & filters.regex("^قلب$")))
        client.add_handler(MessageHandler(big_heart_controller, cmd_filters & filters.regex("^قلب بزرگ$")))
        client.add_handler(MessageHandler(bakiram_controller, cmd_filters & filters.regex(r"^(بکیرم|به کیرم)$", flags=re.IGNORECASE)))
        client.add_handler(MessageHandler(cube_controller, cmd_filters & filters.regex("^مکعب$")))
        client.add_handler(MessageHandler(loading_controller, cmd_filters & filters.regex(r"^(لودینگ|Loading)$", flags=re.IGNORECASE)))

        # Group 1: Auto-reply handlers (lower priority than commands and basic management)
        # Added ~filters.user(user_id) to ensure these don't trigger on own messages if filters somehow match
        client.add_handler(MessageHandler(enemy_handler, is_enemy & ~filters.me & ~filters.user(user_id) & ~filters.bot & ~filters.service), group=1)
        client.add_handler(MessageHandler(friend_handler, is_friend & ~filters.me & ~filters.user(user_id) & ~filters.bot & ~filters.service), group=1)
        client.add_handler(MessageHandler(secretary_auto_reply_handler, filters.private & ~filters.me & ~filters.user(user_id) & ~filters.bot & ~filters.service), group=1)

        # --- Start Background Tasks ---
        tasks = [
            asyncio.create_task(update_profile_clock(client, user_id)),
            asyncio.create_task(update_profile_bio(client, user_id)), # NEW Task
            asyncio.create_task(anti_login_task(client, user_id)),
            asyncio.create_task(status_action_task(client, user_id))
        ]
        # Store the client and its tasks
        ACTIVE_BOTS[user_id] = (client, tasks)
        logging.info(f"Instance for user_id {user_id} configured successfully, background tasks started.")

    except Exception as e_config:
        logging.error(f"FAILED instance configuration or task starting for {user_id} ({phone}): {e_config}", exc_info=True)
        # Clean up if configuration fails after client started
        if user_id and user_id in ACTIVE_BOTS: # Check if it was added to ACTIVE_BOTS
             client_to_stop, tasks_to_cancel = ACTIVE_BOTS.pop(user_id)
             for task in tasks_to_cancel:
                 if task and not task.done(): task.cancel()
             if client_to_stop and client_to_stop.is_connected:
                 try: await client_to_stop.stop(block=False)
                 except Exception as stop_err: logging.error(f"Error stopping client {user_id} after config fail: {stop_err}")
        elif client.is_connected: # If it failed before adding to ACTIVE_BOTS but after starting
             try: await client.stop(block=False)
             except Exception as stop_err: logging.error(f"Error stopping client {phone} after config fail: {stop_err}")
        # Ensure it's removed from ACTIVE_BOTS if config fails at any point
        ACTIVE_BOTS.pop(user_id, None)

# --- Web Section (Flask) ---
HTML_TEMPLATE = """
<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>سلف بات تلگرام</title><style>@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;700&display=swap');body{font-family:'Vazirmatn',sans-serif;background-color:#f0f2f5;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;padding:20px;box-sizing:border-box;}.container{background:white;padding:30px 40px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.1);text-align:center;width:100%;max-width:480px;}h1{color:#333;margin-bottom:20px;font-size:1.5em;}p{color:#666;line-height:1.6;}form{display:flex;flex-direction:column;gap:15px;margin-top:20px;}input[type="tel"],input[type="text"],input[type="password"]{padding:12px;border:1px solid #ddd;border-radius:8px;font-size:16px;text-align:left;direction:ltr;}button{padding:12px;background-color:#007bff;color:white;border:none;border-radius:8px;font-size:16px;cursor:pointer;transition:background-color .2s;}.error{color:#d93025;margin-top:15px;font-weight:bold;}label{font-weight:bold;color:#555;display:block;margin-bottom:5px;text-align:right;}.font-options{border:1px solid #ddd;border-radius:8px;overflow:hidden;max-height: 200px; overflow-y: auto; text-align: right;}.font-option{display:flex;align-items:center;padding:10px 12px;border-bottom:1px solid #eee;cursor:pointer;}.font-option:last-child{border-bottom:none;}.font-option input[type="radio"]{margin-left:15px; flex-shrink: 0;}.font-option label{display:flex;justify-content:space-between;align-items:center;width:100%;font-weight:normal;cursor:pointer;}.font-option .preview{font-size:1.2em;font-weight:bold;direction:ltr;color:#0056b3; margin-right: 10px; white-space: nowrap;}.success{color:#1e8e3e;}.checkbox-option{display:flex;align-items:center;justify-content:flex-end;gap:10px;margin-top:10px;padding:8px;background-color:#f8f9fa;border-radius:8px;}.checkbox-option label{margin-bottom:0;font-weight:normal;cursor:pointer;color:#444;}</style></head><body><div class="container">
{% if step == 'GET_PHONE' %}<h1>ورود به سلف بات</h1><p>شماره و تنظیمات خود را انتخاب کنید تا ربات فعال شود.</p>{% if error_message %}<p class="error">{{ error_message }}</p>{% endif %}<form action="{{ url_for('login') }}" method="post"><input type="hidden" name="action" value="phone"><div><label for="phone">شماره تلفن (با کد کشور)</label><input type="tel" id="phone" name="phone_number" placeholder="+989123456789" required autofocus></div><div><label>استایل فونت ساعت</label><div class="font-options">{% for name, data in font_previews.items() %}<div class="font-option" onclick="document.getElementById('font-{{ data.style }}').checked = true;"><input type="radio" name="font_style" value="{{ data.style }}" id="font-{{ data.style }}" {% if loop.first %}checked{% endif %}><label for="font-{{ data.style }}"><span>{{ name }}</span><span class="preview">{{ data.preview }}</span></label></div>{% endfor %}</div></div><div class="checkbox-option"><input type="checkbox" id="disable_clock" name="disable_clock"><label for="disable_clock">فعال‌سازی بدون ساعت</label></div><button type="submit">ارسال کد تایید</button></form>
{% elif step == 'GET_CODE' %}<h1>کد تایید</h1><p>کدی به تلگرام شما با شماره <strong>{{ phone_number }}</strong> ارسال شد.</p>{% if error_message %}<p class="error">{{ error_message }}</p>{% endif %}<form action="{{ url_for('login') }}" method="post"><input type="hidden" name="action" value="code"><input type="text" name="code" placeholder="کد تایید" required><button type="submit">تایید کد</button></form>
{% elif step == 'GET_PASSWORD' %}<h1>رمز دو مرحله‌ای</h1><p>حساب شما نیاز به رمز تایید دو مرحله‌ای دارد.</p>{% if error_message %}<p class="error">{{ error_message }}</p>{% endif %}<form action="{{ url_for('login') }}" method="post"><input type="hidden" name="action" value="password"><input type="password" name="password" placeholder="رمز عبور دو مرحله ای" required><button type="submit">ورود</button></form>
{% elif step == 'SHOW_SUCCESS' %}<h1>✅ ربات فعال شد!</h1><p>ربات با موفقیت فعال شد. برای دسترسی به قابلیت‌ها، در تلگرام پیام `راهنما` را ارسال کنید.</p><form action="{{ url_for('home') }}" method="get" style="margin-top: 20px;"><button type="submit">خروج و ورود حساب جدید</button></form>{% endif %}</div></body></html>
"""

def get_font_previews():
    sample_time = "12:34"
    return { FONT_DISPLAY_NAMES.get(key, key.capitalize()): {"style": key, "preview": stylize_time(sample_time, key)} for key in FONT_KEYS_ORDER }

async def cleanup_client(phone):
     """Safely disconnects and removes a temporary client."""
     if client := ACTIVE_CLIENTS.pop(phone, None):
         if client.is_connected:
             try:
                 logging.debug(f"Disconnecting temporary client for {phone}...")
                 await client.disconnect()
                 logging.debug(f"Temporary client for {phone} disconnected.")
             except Exception as e:
                 logging.warning(f"Error disconnecting temporary client {phone}: {e}")
     else:
         logging.debug(f"No active temporary client found for {phone} during cleanup.")

@app_flask.route('/')
def home():
    # Clear session potentially related to a previous login attempt
    session.clear()
    logging.info("Session cleared, rendering GET_PHONE page.")
    return render_template_string(HTML_TEMPLATE, step='GET_PHONE', font_previews=get_font_previews())

@app_flask.route('/login', methods=['POST'])
def login():
    action = request.form.get('action')
    phone = session.get('phone_number') # Get phone from session if available
    error_msg = None
    # Determine current step based on action or session state
    current_step = 'GET_PHONE' # Default
    if action == 'code' or session.get('phone_code_hash'):
         current_step = 'GET_CODE'
    if action == 'password': # Should only be reached after SessionPasswordNeeded
         current_step = 'GET_PASSWORD'

    logging.info(f"Login request received: action='{action}', phone_in_session='{phone}'")

    try:
        # Ensure asyncio loop is running in the background thread
        if not EVENT_LOOP or not EVENT_LOOP.is_running():
             # This is a critical error, maybe restart is needed
             raise RuntimeError("Asyncio event loop is not running.")

        # --- Phone Number Submission ---
        if action == 'phone':
            current_step = 'GET_PHONE' # Explicitly set step for clarity
            phone_num_input = request.form.get('phone_number')
            font_style = request.form.get('font_style', 'stylized')
            disable_clock = 'disable_clock' in request.form

            # Validate phone number format
            if not phone_num_input or not re.match(r"^\+?\d{10,15}$", phone_num_input):
                 raise ValueError("فرمت شماره تلفن نامعتبر است. لطفاً با کد کشور وارد کنید (مثال: +98...).")

            # Clean phone number (e.g., ensure it starts with +)
            if not phone_num_input.startswith('+'):
                # Basic assumption: add '+' if missing (might need country-specific logic)
                logging.warning(f"Adding '+' to phone number {phone_num_input}")
                phone_num_input = "+" + phone_num_input

            # Store validated info in session
            session['phone_number'] = phone_num_input
            session['font_style'] = font_style
            session['disable_clock'] = disable_clock
            logging.info(f"Phone number {phone_num_input} received. Requesting code...")

            # Run send_code_task in the event loop and wait for result
            future = asyncio.run_coroutine_threadsafe(send_code_task(phone_num_input), EVENT_LOOP)
            future.result(timeout=45) # Wait up to 45 seconds

            logging.info(f"Code request sent for {phone_num_input}. Rendering GET_CODE page.")
            return render_template_string(HTML_TEMPLATE, step='GET_CODE', phone_number=phone_num_input)

        # --- Code Submission ---
        elif action == 'code':
            current_step = 'GET_CODE' # Set for error handling context
            code_input = request.form.get('code')
            phone = session.get('phone_number') # Re-fetch from session

            # Assert necessary info is present
            if not phone or not code_input or 'phone_code_hash' not in session:
                 logging.error("Session data missing for code submission (phone, code, or hash).")
                 raise AssertionError("اطلاعات ورود (session) نامعتبر یا منقضی شده است. لطفاً از ابتدا شروع کنید.")

            logging.info(f"Code received for {phone}. Attempting sign in...")
            # Run sign_in_task and wait
            future = asyncio.run_coroutine_threadsafe(sign_in_task(phone, code_input), EVENT_LOOP)
            next_step = future.result(timeout=45)

            if next_step == 'GET_PASSWORD':
                logging.info(f"Password required for {phone}. Rendering GET_PASSWORD page.")
                return render_template_string(HTML_TEMPLATE, step='GET_PASSWORD', phone_number=phone)
            elif next_step == 'SUCCESS':
                logging.info(f"Sign in successful for {phone}. Rendering SHOW_SUCCESS page.")
                return render_template_string(HTML_TEMPLATE, step='SHOW_SUCCESS')
            else:
                 # Should not happen if sign_in_task returns correctly
                 logging.error(f"Unexpected result from sign_in_task for {phone}: {next_step}")
                 raise Exception("مرحله ورود نامشخص پس از تایید کد.")

        # --- Password Submission ---
        elif action == 'password':
            current_step = 'GET_PASSWORD' # Set for error handling context
            password_input = request.form.get('password')
            phone = session.get('phone_number') # Re-fetch from session

            if not phone or not password_input:
                 logging.error("Session data missing for password submission (phone or password).")
                 raise AssertionError("اطلاعات ورود (session) نامعتبر یا منقضی شده است. لطفاً از ابتدا شروع کنید.")

            logging.info(f"Password received for {phone}. Checking password...")
            # Run check_password_task and wait
            future = asyncio.run_coroutine_threadsafe(check_password_task(phone, password_input), EVENT_LOOP)
            result = future.result(timeout=45)

            if result == 'SUCCESS':
                logging.info(f"Password check successful for {phone}. Rendering SHOW_SUCCESS page.")
                return render_template_string(HTML_TEMPLATE, step='SHOW_SUCCESS')
            else:
                 # Should not happen if check_password_task returns correctly
                 logging.error(f"Unexpected result from check_password_task for {phone}: {result}")
                 raise Exception("خطای نامشخص پس از بررسی رمز عبور.")

        # --- Invalid Action ---
        else:
            logging.warning(f"Invalid action received in login POST: {action}")
            error_msg = "عملیات درخواستی نامعتبر است."
            current_step = 'GET_PHONE' # Reset to start
            session.clear() # Clear potentially inconsistent session

    # --- Exception Handling ---
    except (TimeoutError, asyncio.TimeoutError):
        error_msg = "پاسخی از سرور تلگرام دریافت نشد. لطفاً از اتصال اینترنت خود مطمئن شوید و دوباره تلاش کنید (Timeout)."
        logging.warning(f"Timeout occurred during login action '{action}' for phone {phone}.")
        # Decide step based on where timeout likely occurred
        if action == 'phone': current_step = 'GET_PHONE'; session.clear()
        elif action == 'code': current_step = 'GET_CODE'
        elif action == 'password': current_step = 'GET_PASSWORD'
        else: current_step = 'GET_PHONE'; session.clear()

    except (PhoneNumberInvalid, ValueError) as e: # Catch specific validation errors
         error_msg = str(e) # Use the error message directly (e.g., from ValueError)
         logging.warning(f"Validation Error during login action '{action}' for phone {phone}: {e}")
         current_step = 'GET_PHONE' # Go back to phone input
         session.clear() # Clear session on phone error

    except (PhoneCodeInvalid, PasswordHashInvalid) as e:
         error_msg = "کد تایید یا رمز عبور وارد شده اشتباه است. لطفاً دوباره بررسی کنید."
         logging.warning(f"Invalid Code/Password during login action '{action}' for phone {phone}: {type(e).__name__}")
         # Stay on the current step (code or password)
         if action == 'code': current_step = 'GET_CODE'
         elif action == 'password': current_step = 'GET_PASSWORD'

    except PhoneCodeExpired as e:
         error_msg = "کد تایید منقضی شده است. لطفاً شماره تلفن را مجدداً وارد کنید تا کد جدید دریافت کنید."
         logging.warning(f"Phone code expired for {phone}: {e}")
         current_step = 'GET_PHONE' # Go back to start
         session.clear()

    except SessionPasswordNeeded as e:
         # This exception is expected, transition to password step
         logging.info(f"Password needed for {phone} after code entry.")
         current_step = 'GET_PASSWORD'
         # No error message needed here, just render the password form
         return render_template_string(HTML_TEMPLATE, step='GET_PASSWORD', phone_number=phone)

    except FloodWait as e:
         error_msg = f"تلگرام درخواست شما را به دلیل تعداد زیاد تلاش‌ها محدود کرده است. لطفاً {e.value} ثانیه صبر کنید و دوباره امتحان کنید."
         logging.warning(f"FloodWait ({e.value}s) during login action '{action}' for phone {phone}.")
         # Stay on the current step where flood wait occurred

    except AssertionError as e: # Catch session/input errors
         error_msg = str(e) or "خطای داخلی: اطلاعات ورود یافت نشد. لطفاً دوباره تلاش کنید."
         logging.error(f"Assertion Error during login action '{action}' for phone {phone}: {e}")
         current_step = 'GET_PHONE' # Go back to start on assertion errors
         session.clear()

    except RuntimeError as e: # Catch loop errors
         error_msg = f"خطای بحرانی در سرور رخ داده است: {e}. لطفاً بعداً تلاش کنید."
         logging.critical(f"Runtime Error during login action '{action}': {e}", exc_info=True)
         current_step = 'GET_PHONE' # Go back to start
         session.clear()

    except Exception as e: # Catch any other unexpected exception
         error_msg = f"یک خطای پیش‌بینی نشده رخ داد: {type(e).__name__}. لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
         logging.error(f"Unexpected Exception during login action '{action}' for phone {phone}: {e}", exc_info=True)
         current_step = 'GET_PHONE' # Go back to start
         session.clear()

    # --- Cleanup and Render Error Page ---
    # If an error occurred (except SessionPasswordNeeded), try cleaning up temporary client
    # Only cleanup if phone number is known and error wasn't SessionPasswordNeeded
    if error_msg and phone and current_step != 'GET_PASSWORD':
         logging.info(f"Cleaning up temporary client for {phone} due to error: {error_msg}")
         try:
             # Run cleanup in the background loop, don't wait for it here
             if EVENT_LOOP.is_running():
                 asyncio.run_coroutine_threadsafe(cleanup_client(phone), EVENT_LOOP)
         except Exception as cleanup_err:
             logging.error(f"Error submitting cleanup task for {phone}: {cleanup_err}")

    # Render the appropriate template with error message
    logging.debug(f"Rendering step '{current_step}' with error: {error_msg}")
    return render_template_string(HTML_TEMPLATE,
                                step=current_step,
                                error_message=error_msg,
                                phone_number=phone, # Pass phone even on error if available
                                font_previews=get_font_previews())

# --- Async Tasks for Login Flow ---
async def send_code_task(phone):
    """Creates a client, connects, sends code, and stores hash in session."""
    # Ensure previous client for this number is cleaned up
    await cleanup_client(phone)

    # Use unique name for temporary client, maybe with timestamp or random part
    # Using in_memory=True means session won't be saved to disk here
    client = Client(f"login_attempt_{re.sub(r'\W+', '', phone)}_{int(time.time())}",
                    api_id=API_ID, api_hash=API_HASH, in_memory=True)
    ACTIVE_CLIENTS[phone] = client # Store client associated with phone number
    logging.info(f"Temporary client created for {phone}.")

    try:
        logging.debug(f"Connecting temporary client for {phone}...")
        await client.connect()
        logging.debug(f"Temporary client connected for {phone}. Sending code...")
        sent_code = await client.send_code(phone)

        # Important: Store phone_code_hash in Flask session (accessible by web thread)
        session['phone_code_hash'] = sent_code.phone_code_hash
        logging.info(f"Code sent successfully to {phone}. Hash stored in session.")
        # Keep client connected for sign_in or check_password

    except (FloodWait, PhoneNumberInvalid, Exception) as e:
        # If sending code fails, disconnect and remove the client
        logging.error(f"Error sending code to {phone}: {type(e).__name__} - {e}")
        await cleanup_client(phone) # Cleanup on failure
        raise e # Re-raise the exception to be caught by the Flask route

async def sign_in_task(phone, code):
    """Attempts to sign in using the code. Handles SessionPasswordNeeded."""
    client = ACTIVE_CLIENTS.get(phone)
    if not client or not client.is_connected:
        logging.error(f"Sign in failed for {phone}: Temporary client not found or disconnected.")
        raise AssertionError("Session expired or client disconnected. Please try again.")

    phone_code_hash = session.get('phone_code_hash')
    if not phone_code_hash:
        logging.error(f"Sign in failed for {phone}: phone_code_hash missing from session.")
        raise AssertionError("Session data corrupted (missing code hash). Please try again.")

    try:
        logging.debug(f"Attempting sign in for {phone} with code...")
        await client.sign_in(phone, phone_code_hash, code)
        logging.info(f"Sign in successful for {phone} (no password needed). Exporting session.")

        # --- Session Export and DB Update ---
        session_str = await client.export_session_string()
        font_style = session.get('font_style', 'stylized')
        disable_clock = session.get('disable_clock', False)

        if sessions_collection is not None:
            try:
                logging.debug(f"Updating/inserting session into DB for {phone}...")
                sessions_collection.update_one(
                    {'phone_number': phone},
                    {'$set': {'session_string': session_str,
                              'font_style': font_style,
                              'disable_clock': disable_clock}},
                    upsert=True
                )
                logging.debug(f"DB updated for {phone}.")
            except Exception as db_err:
                 # Log error but continue - bot can start, just won't persist on restart
                 logging.error(f"Database Error: Failed to save session for {phone}: {db_err}")

        # --- Schedule Bot Start ---
        logging.info(f"Scheduling main bot instance start for {phone}...")
        # Ensure it runs in the main asyncio loop
        EVENT_LOOP.create_task(start_bot_instance(session_str, phone, font_style, disable_clock))

        # --- Cleanup ---
        await cleanup_client(phone) # Clean up temporary client after success
        session.clear() # Clear Flask session after successful login

        return 'SUCCESS' # Signal success to Flask route

    except SessionPasswordNeeded:
        # Password is required, keep client connected for password check
        logging.info(f"Password needed for {phone}. Keeping temporary client alive.")
        return 'GET_PASSWORD' # Signal password needed to Flask route

    except (FloodWait, PhoneCodeInvalid, PhoneCodeExpired, Exception) as e:
        # On error (except PasswordNeeded), cleanup and re-raise
        logging.error(f"Error during sign in for {phone}: {type(e).__name__} - {e}")
        await cleanup_client(phone) # Cleanup on failure
        session.clear() # Clear session on failure
        raise e # Re-raise to be caught by Flask

async def check_password_task(phone, password):
    """Checks the 2FA password."""
    client = ACTIVE_CLIENTS.get(phone)
    if not client or not client.is_connected:
        logging.error(f"Password check failed for {phone}: Temporary client not found or disconnected.")
        raise AssertionError("Session expired or client disconnected. Please try again.")

    try:
        logging.debug(f"Checking password for {phone}...")
        await client.check_password(password)
        logging.info(f"Password check successful for {phone}. Exporting session.")

        # --- Session Export and DB Update ---
        session_str = await client.export_session_string()
        font_style = session.get('font_style', 'stylized')
        disable_clock = session.get('disable_clock', False)

        if sessions_collection is not None:
            try:
                logging.debug(f"Updating/inserting session into DB for {phone} after password...")
                sessions_collection.update_one(
                    {'phone_number': phone},
                    {'$set': {'session_string': session_str,
                              'font_style': font_style,
                              'disable_clock': disable_clock}},
                    upsert=True
                )
                logging.debug(f"DB updated for {phone}.")
            except Exception as db_err:
                 logging.error(f"Database Error: Failed to save session for {phone} after password: {db_err}")

        # --- Schedule Bot Start ---
        logging.info(f"Scheduling main bot instance start for {phone} after password...")
        EVENT_LOOP.create_task(start_bot_instance(session_str, phone, font_style, disable_clock))

        # --- Cleanup ---
        await cleanup_client(phone) # Clean up temporary client
        session.clear() # Clear Flask session

        return 'SUCCESS' # Signal success

    except (FloodWait, PasswordHashInvalid, Exception) as e:
        # On error, cleanup and re-raise
        logging.error(f"Error during password check for {phone}: {type(e).__name__} - {e}")
        await cleanup_client(phone) # Cleanup on failure
        session.clear() # Clear session on failure
        raise e # Re-raise to be caught by Flask

# --- Running the Application ---
def run_flask():
    port = int(os.environ.get("PORT", 10000)); logging.info(f"Starting Flask web server on host 0.0.0.0, port {port}")
    try:
        # Use Waitress for a more production-ready server if available
        from waitress import serve
        logging.info("Using Waitress production WSGI server.")
        serve(app_flask, host='0.0.0.0', port=port, threads=8) # Adjust threads as needed
    except ImportError:
        logging.warning("Waitress package not found. Falling back to Flask's built-in development server (NOT recommended for production).")
        # Flask's dev server is not suitable for production
        app_flask.run(host='0.0.0.0', port=port)
    except Exception as flask_err:
         logging.critical(f"Flask server failed to start: {flask_err}", exc_info=True)

def run_asyncio_loop():
    global EVENT_LOOP
    # Set the event loop for the current thread
    asyncio.set_event_loop(EVENT_LOOP)
    logging.info("Asyncio event loop set for background thread.")

    # --- Auto-Login from Database ---
    if sessions_collection is not None:
        logging.info("Attempting auto-login for existing sessions from database...")
        started_count = 0
        try:
             # Use find() to get a cursor and iterate
             session_docs = list(sessions_collection.find()) # Fetch all first to avoid cursor issues if collection changes
             logging.info(f"Found {len(session_docs)} potential session(s) in DB.")
             for doc in session_docs:
                 try:
                     session_string = doc['session_string']
                     # Use phone_number if available, otherwise generate a placeholder ID
                     phone = doc.get('phone_number', f"db_user_{doc.get('_id', f'unk_{started_count}')}")
                     font_style = doc.get('font_style', 'stylized') # Default if missing
                     disable_clock = doc.get('disable_clock', False) # Default if missing

                     logging.info(f"Scheduling auto-start for session: {phone}...")
                     # Create task in the running loop
                     EVENT_LOOP.create_task(start_bot_instance(session_string, phone, font_style, disable_clock))
                     started_count += 1
                     # Optional small delay between starts to avoid overwhelming resources/APIs
                     # time.sleep(1) # Consider async sleep if this causes issues
                 except KeyError:
                     logging.error(f"DB AutoLogin Error: Document missing 'session_string'. Skipping. Doc ID: {doc.get('_id')}")
                 except Exception as e_doc:
                     logging.error(f"DB AutoLogin Error: Failed to schedule start for session {doc.get('phone_number', doc.get('_id', 'unknown'))}: {e_doc}", exc_info=True)
             logging.info(f"Finished scheduling auto-start. {started_count} session(s) scheduled.")
        except Exception as e_db_query:
             logging.error(f"DB AutoLogin Error: Failed to query database for sessions: {e_db_query}", exc_info=True)
    else:
        logging.info("MongoDB not configured. Skipping auto-login from database.")

    # --- Start Event Loop ---
    try:
        logging.info("Starting asyncio event loop run_forever()...")
        EVENT_LOOP.run_forever()
        # Code here will run after loop.stop() is called
        logging.info("Asyncio event loop has stopped.")

    except (KeyboardInterrupt, SystemExit):
        logging.info("Shutdown signal (KeyboardInterrupt/SystemExit) received by asyncio loop.")
        # Loop might already be stopping, but call stop() just in case
        if EVENT_LOOP.is_running():
            EVENT_LOOP.stop()
    except Exception as e_loop:
        logging.critical(f"CRITICAL ASYNCIO LOOP ERROR: {e_loop}", exc_info=True)
        # Try to stop the loop gracefully if possible
        if EVENT_LOOP.is_running():
            EVENT_LOOP.stop()

    # --- Cleanup Sequence (after loop stops) ---
    finally:
        logging.info("Asyncio loop cleanup sequence initiated...")
        cleanup_completed = False
        if EVENT_LOOP.is_running(): # Should ideally be false here, but check just in case
            logging.warning("Event loop was still running at the start of finally block. Forcing stop.")
            EVENT_LOOP.stop()

        # Run final cleanup tasks within the loop before closing
        try:
            async def shutdown_tasks():
                """Gather and run all cleanup tasks concurrently."""
                nonlocal cleanup_completed
                logging.info("Starting asynchronous shutdown tasks...")
                active_bot_stops = []
                # Stop active bot instances
                for user_id, (client, bg_tasks) in list(ACTIVE_BOTS.items()):
                    logging.debug(f"Initiating shutdown for active bot instance {user_id}...")
                    # Cancel background tasks first
                    for task in bg_tasks:
                        if task and not task.done():
                            task.cancel()
                    # Schedule client stop (non-blocking)
                    if client and client.is_connected:
                        active_bot_stops.append(client.stop(block=False))
                    ACTIVE_BOTS.pop(user_id, None) # Remove immediately

                # Disconnect temporary login clients
                active_client_disconnects = []
                for phone, client in list(ACTIVE_CLIENTS.items()):
                    if client and client.is_connected:
                        logging.debug(f"Initiating disconnect for temporary client {phone}...")
                        active_client_disconnects.append(client.disconnect())
                    ACTIVE_CLIENTS.pop(phone, None)

                # Wait for all stop/disconnect tasks
                all_cleanup_ops = active_bot_stops + active_client_disconnects
                if all_cleanup_ops:
                    logging.info(f"Waiting for {len(all_cleanup_ops)} client stops/disconnects...")
                    results = await asyncio.gather(*all_cleanup_ops, return_exceptions=True)
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                             logging.warning(f"Error during client cleanup operation {i}: {result}")
                logging.info("Client stop/disconnect operations complete.")

                # Cancel any remaining asyncio tasks (should be few now)
                logging.debug("Cancelling any remaining asyncio tasks...")
                current_task = asyncio.current_task()
                tasks_to_cancel = [t for t in asyncio.all_tasks() if t is not current_task]
                if tasks_to_cancel:
                    for task in tasks_to_cancel: task.cancel()
                    await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
                logging.debug("Remaining asyncio tasks cancelled.")
                cleanup_completed = True

            # Run the shutdown coroutine until it completes
            EVENT_LOOP.run_until_complete(shutdown_tasks())
            logging.info("Asynchronous shutdown tasks completed.")

        except Exception as e_shutdown:
            logging.error(f"Error during asyncio shutdown sequence: {e_shutdown}", exc_info=True)

        finally:
             # Close the event loop
             if not EVENT_LOOP.is_closed():
                 EVENT_LOOP.close()
                 logging.info("Asyncio event loop closed.")
             if not cleanup_completed:
                 logging.warning("Cleanup sequence did not fully complete before loop closure.")

if __name__ == "__main__":
    logging.info("========================================")
    logging.info(" Starting Telegram Self Bot Service... ")
    logging.info("========================================")

    # Start the asyncio loop in a separate thread
    loop_thread = Thread(target=run_asyncio_loop, name="AsyncioLoopThread", daemon=True)
    loop_thread.start()

    # Start the Flask server in the main thread
    # This will block until Flask stops (e.g., via CTRL+C)
    run_flask()

    # --- Post-Flask Shutdown ---
    logging.info("Flask server has stopped.")

    # Signal the asyncio loop thread to stop
    if loop_thread.is_alive() and EVENT_LOOP.is_running():
        logging.info("Signaling asyncio loop thread to stop...")
        # Use call_soon_threadsafe to schedule loop.stop() from this thread
        EVENT_LOOP.call_soon_threadsafe(EVENT_LOOP.stop)
    elif not EVENT_LOOP.is_running():
         logging.info("Asyncio loop was already stopped.")

    # Wait for the asyncio thread to finish its cleanup
    logging.info("Waiting for asyncio loop thread to finish cleanup (max 15 seconds)...")
    loop_thread.join(timeout=15)

    if loop_thread.is_alive():
        logging.warning("Asyncio thread did not exit gracefully within the timeout.")
    else:
        logging.info("Asyncio thread joined successfully.")

    # Close MongoDB client if it was initialized
    if mongo_client:
        try:
            logging.info("Closing MongoDB connection...")
            mongo_client.close()
            logging.info("MongoDB connection closed.")
        except Exception as mongo_close_err:
             logging.error(f"Error closing MongoDB connection: {mongo_close_err}")

    logging.info("========================================")
    logging.info(" Application shutdown complete.        ")
    logging.info("========================================")
