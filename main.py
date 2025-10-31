import asyncio
import os
import logging
import re
import aiohttp
import time
import unicodedata
import shutil
import random
import jdatetime # <--- NEW: For Jalali (Persian) Date
import math # <--- NEW: For Calc
import json # <--- NEW: For JSON
from urllib.parse import quote
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.enums import ChatType, ChatAction, UserStatus, ParseMode
from pyrogram.errors import (
    FloodWait, SessionPasswordNeeded, PhoneCodeInvalid,
    PasswordHashInvalid, PhoneNumberInvalid, PhoneCodeExpired, UserDeactivated, AuthKeyUnregistered,
    ReactionInvalid, MessageIdInvalid, MessageNotModified, PeerIdInvalid, UserNotParticipant, PhotoCropSizeSmall,
    UserIsBlocked, UserAdminInvalid, ChatAdminRequired, UsernameNotOccupied, UsernameInvalid
)
try:
    from pyrogram.raw import functions
    from pyrogram.raw.types import ChannelParticipantsSearch
except ImportError:
    logging.warning("Could not import 'pyrogram.raw.functions'. Anti-login and other features might not work.")
    functions = None

from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request, render_template_string, redirect, session, url_for
from threading import Thread
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pytube import YouTube
import certifi
from io import BytesIO # <--- NEW: For in-memory operations

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
if MONGO_URI and "<db_password>" not in MONGO_URI:
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
    logging.warning("MONGO_URI is not configured correctly. Please set your password. Session persistence will be disabled.")

# --- Application Variables ---
TEHRAN_TIMEZONE = ZoneInfo("Asia/Tehran")
app_flask = Flask(__name__)
app_flask.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

# --- Clock Font Dictionaries ---
FONT_STYLES = {
    "cursive":      {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':', '/':'/'},
    "stylized":     {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵',':':':', '/':'/'},
    "doublestruck": {'0':'𝟘','1':'𝟙','2':'𝟚','3':'𝟛','4':'𝟜','5':'𝟝','6':'𝟞','7':'𝟟','8':'𝟠','9':'𝟡',':':':', '/':'/'},
    "monospace":    {'0':'𝟶','1':'𝟷','2':'𝟸','3':'𝟹','4':'𝟺','5':'𝟻','6':'𝟼','7':'𝟽','8':'𝟾','9':'𝟿',':':':', '/':'/'},
    "normal":       {'0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9',':':':', '/':'/'},
    "circled":      {'0':'⓪','1':'①','2':'②','3':'③','4':'④','5':'⑤','6':'⑥','7':'⑦','8':'⑧','9':'⑨',':':'∶', '/':'/'},
    "fullwidth":    {'0':'０','1':'１','2':'２','3':'３','4':'４','5':'５','6':'６','7':'７','8':'８','9':'９',':':'：', '/':'/'},
    "sans_normal":  {'0':'𝟢','1':'𝟣','2':'𝟤','3':'𝟥','4':'𝟦','5':'𝟧','6':'𝟨','7':'𝟩','8':'𝟪','9':'𝟫',':':'∶', '/':'/'},
    "negative_circled": {'0':'⓿','1':'❶','2':'❷','3':'❸','4':'❹','5':'❺','6':'❻','7':'❼','8':'❽','9':'❾',':':'∶', '/':'/'},
    "parenthesized": {'0':'🄀','1':'⑴','2':'⑵','3':'⑶','4':'⑷','5':'⑸','6':'⑹','7':'⑺','8':'⑻','9':'⑼',':':'∶', '/':'/'},
    "dot":          {'0':'🄀','1':'⒈','2':'⒉','3':'⒊','4':'⒋','5':'⒌','6':'⒍','7':'⒎','8':'⒏','9':'⒐',':':'∶', '/':'/'},
    "thai":         {'0':'๐','1':'๑','2':'๒','3':'๓','4':'๔','5':'๕','6':'๖','7':'๗','8':'๘','9':'๙',':':' : ', '/':'/'},
    "devanagari":   {'0':'०','1':'१','2':'२','3':'۳','4':'४','5':'५','6':'६','7':'७','8':'८','9':'९',':':' : ', '/':'/'},
    "arabic_indic": {'0':'٠','1':'١','2':'٢','3':'٣','4':'٤','5':'٥','6':'٦','7':'٧','8':'٨','9':'٩',':':' : ', '/':'/'},
    "keycap":       {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣',':':':', '/':'/'},
    "superscript":  {'0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹',':':':', '/':'/'}, # Used for "small" date
    "subscript":    {'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉',':':':', '/':'/'},
    "tibetan":      {'0':'༠','1':'༡','2':'༢','3':'༣','4':'༤','5':'༥','6':'༦','7':'༧','8':'༨','9':'༩',':':' : ', '/':'/'},
    "bengali":      {'0':'০','1':'১','2':'২','3':'৩','4':'৪','5':'۵','6':'۶','7':'۷','8':'۸','9':'۹',':':' : ', '/':'/'},
    "gujarati":     {'0':'૦','1':'૧','2':'૨','3':'૩','4':'૪','5':'૫','6':'૬','7':'૭','8':'૮','9':'૯',':':' : ', '/':'/'},
    "mongolian":    {'0':'᠐','1':'᠑','2':'᠒','3':'᠓','4':'᠔','5':'᠕','6':'᠖','7':'᠗','8':'᠘','9':'᠙',':':' : ', '/':'/'},
    "lao":          {'0':'໐','1':'໑','2':'໒','3':'໓','4':'໔','5':'໕','6':'໖','7':'໗','8':'໘','9':'໙',':':' : ', '/':'/'},
    "fraktur":      {'0':'𝔃','1':'𝔄','2':'𝔅','3':'𝔆','4':'𝔇','5':'𝔈','6':'𝔉','7':'𝔊','8':'𝔋','9':'𝔌',':':':', '/':'/'},
    "bold_fraktur": {'0':'𝖀','1':'𝖁','2':'𝖂','3':'𝖃','4':'𝖄','5':'𝖅','6':'𝖆','7':'𝖇','8':'𝖈','9':'𝖉',':':':', '/':'/'},
    "script":       {'0':'𝟢','1':'𝟣','2':'𝟤','3':'𝟥','4':'𝟦','5':'𝟧','6':'𝟨','7':'𝟩','8':'𝟪','9':'𝟫',':':':', '/':'/'},
    "bold_script":  {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':', '/':'/'},
    "squared":      {'0':'🄀','1':'🄁','2':'🄂','3':'🄃','4':'🄄','5':'_','6':'🄆','7':'🄇','8':'🄈','9':'🄉',':':'∶', '/':'/'},
    "negative_squared": {'0':'🅀','1':'🅁','2':'🅂','3':'🅃','4':'🅄','5':'🅅','6':'🅆','7':'🅇','8':'🅈','9':'🅉',':':'∶', '/':'/'},
    "roman":        {'0':'⓪','1':'Ⅰ','2':'Ⅱ','3':'Ⅲ','4':'Ⅳ','5':'Ⅴ','6':'Ⅵ','7':'Ⅶ','8':'Ⅷ','9':'Ⅸ',':':':', '/':'/'},
    "small_caps":   {'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉',':':':', '/':'/'},
    "oldstyle":     {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':', '/':'/'},
    "inverted":     {'0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9',':':':', '/':'/'},
    "mirror":       {'0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'9','7':'7','8':'8','9':'6',':':':', '/':'/'},
    "strike":       {'0':'0̶','1':'1̶','2':'2̶','3':'3̶','4':'4̶','5':'5̶','6':'6̶','7':'7̶','8':'8̶','9':'9̶',':':':', '/':'/'},
    "bubble":       {'0':'⓪','1':'①','2':'②','3':'③','4':'④','5':'⑤','6':'⑥','7':'⑦','8':'⑧','9':'⑨',':':'∶', '/':'/'},
    "fancy1":       {'0':'０','1':'１','2':'２','3':'３','4':'４','5':'５','6':'６','7':'۷','8':'８','9':'９',':':'：', '/':'/'},
    "fancy2":       {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵',':':':', '/':'/'},
    "fancy3":       {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':', '/':'/'},
    "fancy4":       {'0':'⓿','1':'❶','2':'❷','3':'❸','4':'❹','5':'❺','6':'❻','7':'❼','8':'❽','9':'❾',':':'∶', '/':'/'},
    # Additional cool fonts
    "ethiopic":     {'0':'፩','1':'፪','2':'፫','3':'፬','4':'፭','5':'፮','6':'፯','7':'፰','8':'፱','9':'፲',':':' : ', '/':'/'},  # Approximate
    "gothic":       {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':', '/':'/'},  # Bold variant
    "runic":        {'0':'ᛟ','1':'ᛁ','2':'ᛒ','3':'ᛏ','4':'ᚠ','5':'ᚢ','6':'ᛋ','7':'ᚷ','8':'ᚺ','9':'ᛉ',':':' : ', '/':'/'},  # Approximate runic
    "math_bold":    {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':', '/':'/'},
    "math_italic":  {'0':'𝟢','1':'𝟣','2':'𝟤','3':'𝟥','4':'𝟦','5':'𝟧','6':'𝟨','7':'𝟩','8':'𝟪','9':'𝟫',':':':', '/':'/'},
    "math_sans":    {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵',':':':', '/':'/'},
    "math_monospace": {'0':'𝟶','1':'𝟷','2':'𝟸','3':'𝟹','4':'𝟺','5':'𝟻','6':'𝟼','7':'𝟽','8':'𝟾','9':'𝟿',':':':', '/':'/'},
    "math_double":  {'0':'𝟘','1':'𝟙','2':'𝟚','3':'𝟛','4':'𝟜','5':'𝟝','6':'𝟞','7':'𝟟','8':'𝟠','9':'𝟡',':':':', '/':'/'},
    "japanese":     {'0':'零','1':'壱','2':'弐','3':'参','4':'四','5':'伍','6':'陸','7':'漆','8':'捌','9':'玖',':':' : ', '/':'/'},  # Kanji numbers
    "emoji":        {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣',':':':', '/':'/'},
    "shadow":       {'0':'🅾','1':'🅰','2':'🅱','3':'🅲','4':'🅳','5':'🅴','6':'🅵','7':'🅶','8':'🅷','9':'🅸',':':' : ', '/':'/'},  # Approximate
}
FONT_KEYS_ORDER = list(FONT_STYLES.keys())
FONT_DISPLAY_NAMES = {
    "cursive": "کشیده", "stylized": "فانتزی", "doublestruck": "توخالی",
    "monospace": "کامپیوتری", "normal": "ساده", "circled": "دایره‌ای", "fullwidth": "پهن",
    "sans_normal": "ساده ۲", "negative_circled": "دایره‌ای معکوس",
    "parenthesized": "پرانتزی", "dot": "نقطه‌دار", "thai": "تایلندی", "devanagari": "هندی", "arabic_indic": "عربی",
    "keycap": "کیکپ", "superscript": "بالانویس (کوچک)", "subscript": "زیرنویس", "tibetan": "تبتی", "bengali": "بنگالی",
    "gujarati": "گجراتی", "mongolian": "مغولی", "lao": "لائوسی",
    "fraktur": "فراکتور", "bold_fraktur": "فراکتور بولد", "script": "اسکریپت", "bold_script": "اسکریپت بولد", "squared": "مربعی", "negative_squared": "مربعی معکوس", "roman": "رومی", "small_caps": "کوچک کپس", "oldstyle": "قدیمی", "inverted": "وارونه", "mirror": "آینه‌ای", "strike": "خط خورده", "bubble": "حبابی", "fancy1": "فانتزی ۱", "fancy2": "فانتزی ۲", "fancy3": "فانتزی ۳", "fancy4": "فانتزی ۴",
    "ethiopic": "اتیوپیک", "gothic": "گوتیک", "runic": "رونیک", "math_bold": "ریاضی بولد", "math_italic": "ریاضی ایتالیک", "math_sans": "ریاضی سنس", "math_monospace": "ریاضی مونوسپیس", "math_double": "ریاضی دوبل", "japanese": "ژاپنی", "emoji": "ایموجی", "shadow": "سایه‌دار",
}
# Add slash '/' to all font maps for date formatting
for font_map in FONT_STYLES.values():
    if '/' not in font_map:
        font_map['/'] = '/'

ALL_CLOCK_CHARS = "".join(set(char for font in FONT_STYLES.values() for char in font.values()))
CLOCK_CHARS_REGEX_CLASS = f"[{re.escape(ALL_CLOCK_CHARS)}]"

# --- Feature Variables ---
# (متن‌های توهین‌آمیز با متن‌های جایگزین طبق درخواست، جایگزین شدند)
REPLACEMENT_TEXTS = [f"متن {i+1}" for i in range(20)] # List of replacement texts

ENEMY_REPLIES = {}  # {user_id: list of replies}
FRIEND_REPLIES = {} # {user_id: list of replies}
ENEMY_LIST = {} # {user_id: set of enemy user_ids}
FRIEND_LIST = {}    # {user_id: set of friend user_ids}
ENEMY_ACTIVE = {}   # {user_id: bool}
FRIEND_ACTIVE = {}  # {user_id: bool}
SECRETARY_MODE_STATUS = {}
CUSTOM_SECRETARY_MESSAGES = {}
USERS_REPLIED_IN_SECRETARY = {}
MUTED_USERS = {}    # {user_id: set of (sender_id, chat_id)}
USER_FONT_CHOICES = {}
CLOCK_STATUS = {}
TIME_BIO_STATUS = {} # For Bio Clock
TIME_DATE_STATUS = {} # <--- NEW: For Bio Date
TIME_DATE_FORMAT = {} # <--- NEW: For Bio Date format ('jalali' or 'gregorian')
BOLD_MODE_STATUS = {}
ITALIC_MODE_STATUS = {} # For Italic
UNDERLINE_MODE_STATUS = {} # For Underline
LINK_MODE_STATUS = {} # For Link
AUTO_SEEN_STATUS = {}
AUTO_REACTION_TARGETS = {}  # {user_id: {target_user_id: emoji}}
AUTO_TRANSLATE_TARGET = {}  # {user_id: lang_code}
ANTI_LOGIN_STATUS = {}
COPY_MODE_STATUS = {}
ORIGINAL_PROFILE_DATA = {}
PV_LOCK_STATUS = {}
# Statuses
TYPING_MODE_STATUS = {}
PLAYING_MODE_STATUS = {}
RECORD_VOICE_STATUS = {}
UPLOAD_PHOTO_STATUS = {}
WATCH_GIF_STATUS = {}
# NEW Statuses from bot.txt
RECORD_VIDEO_STATUS = {}
CHOOSE_STICKER_STATUS = {}
UPLOAD_VIDEO_STATUS = {}
UPLOAD_DOCUMENT_STATUS = {}
UPLOAD_AUDIO_STATUS = {}
SPEAKING_STATUS = {}

# NEW Feature States
AFK_STATUS = {} # <--- NEW: For AFK mode {user_id: {"reason": "...", "since": ...}}
NOTES = {}      # <--- NEW: For Notes {user_id: {"note_name": "note_content"}}
BLOCKED_USERS_CACHE = {} # <--- NEW: For Blocklist

# --- Task Management ---
EVENT_LOOP = asyncio.new_event_loop()
ACTIVE_CLIENTS = {}
ACTIVE_BOTS = {}

DEFAULT_SECRETARY_MESSAGE = "سلام! در حال حاضر آفلاین هستم و پیام شما را دریافت کردم. در اولین فرصت پاسخ خواهم داد. ممنون از پیامتون."

# NEW: Updated COMMAND_REGEX with all new commands
COMMAND_REGEX_STR = (
    r"^(تایپ روشن|تایپ خاموش|بازی روشن|بازی خاموش|ضبط ویس روشن|ضبط ویس خاموش|عکس روشن|عکس خاموش|گیف روشن|گیف خاموش|"
    r"ترجمه [a-z]{2}(?:-[a-z]{2})?|ترجمه خاموش|چینی روشن|چینی خاموش|روسی روشن|روسی خاموش|انگلیسی روشن|انگلیسی خاموش|"
    r"بولد روشن|بولد خاموش|سین روشن|سین خاموش|ساعت روشن|ساعت خاموش|فونت|فونت \d+|"
    r"منشی روشن|منشی خاموش|منشی متن(?: |$)(.*)|انتی لوگین روشن|انتی لوگین خاموش|پیوی قفل|پیوی باز|"
    r"ذخیره|تکرار \d+(?: \d+)?|حذف همه|حذف(?: \d+)?|" # Added optional space for repeat interval
    r"دشمن روشن|دشمن خاموش|تنظیم دشمن|حذف دشمن|پاکسازی لیست دشمن|لیست دشمن|لیست متن دشمن|تنظیم متن دشمن (.*)|حذف متن دشمن(?: \d+)?|"
    r"دوست روشن|دوست خاموش|تنظیم دوست|حذف دوست|پاکسازی لیست دوست|لیست دوست|لیست متن دوست|تنظیم متن دوست (.*)|حذف متن دوست(?: \d+)?|"
    r"بلاک روشن|بلاک خاموش|سکوت روشن|سکوت خاموش|ریاکشن .*|ریاکشن خاموش|کپی روشن|کپی خاموش|"
    r"تاس|تاس \d+|بولینگ|راهنما|ترجمه|"
    # --- New commands from bot.txt & user request ---
    r"بیو ساعت روشن|بیو ساعت خاموش|ایتالیک روشن|ایتالیک خاموش|زیرخط روشن|زیرخط خاموش|لینک روشن|لینک خاموش|"
    r"ضبط ویدیو روشن|ضبط ویدیو خاموش|استیکر روشن|استیکر خاموش|آپلود ویدیو روشن|آپلود ویدیو خاموش|آپلود فایل روشن|آپلود فایل خاموش|آپلود صدا روشن|آپلود صدا خاموش|صحبت روشن|صحبت خاموش|"
    r"تنظیم اسم|تنظیم بیو|تنظیم پروفایل|مربع|قلب|قلب بزرگ|بکیرم|به کیرم|مکعب|لودینگ|Loading|ربات|"
    r"یوتوب .*|ویس .*|پارت .*|" # <--- CHANGED: !YouTube to یوتوب
    # --- New Bio Date Commands ---
    r"تاریخ روشن|تاریخ خاموش|فونت تاریخ 1|فونت تاریخ 2|"
    # --- NEW Utility Features ---
    r"id|پینگ|ping|info|"
    r"afk(?: (.*))?$|afk خاموش|" # afk [reason] or afk
    r"note \S+ (.*)|note \S+|notes|delnote \S+|" # note name text | note name | notes | delnote name
    r"purge|webshot .+" # <--- Fixed webshot regex
    # --- NEW BATCH 2 Features ---
    r"|تگ همگانی|تگ همه|ترک|هواشناسی .*|جستجو .*|پین|آنپین|ادمین|عزل|" # <--- NEW
    r"دیکشنری .*|ud .*|حساب .*|calc .*|کیو آر .*|qr .*|جیسون|json|این کیه \S+|whois \S+|لیست بلاک|blocklist" # <--- NEW
    r")$"
)
COMMAND_REGEX = re.compile(COMMAND_REGEX_STR, re.IGNORECASE | re.DOTALL)


# --- Main Bot Functions ---
def stylize_time(time_str: str, style: str) -> str:
    """Applies the selected font style to the time string (clock or date)."""
    font_map = FONT_STYLES.get(style, FONT_STYLES["stylized"]) # Default to stylized
    return ''.join(font_map.get(char, char) for char in time_str)

async def update_profile_clock(client: Client, user_id: int):
    """Background task to update the user's first name with the current time."""
    log_message = f"Starting clock loop for user_id {user_id}..."
    logging.info(log_message)
    
    while user_id in ACTIVE_BOTS:
        try:
            # Only update if clock is enabled and copy mode is off
            if CLOCK_STATUS.get(user_id, True) and not COPY_MODE_STATUS.get(user_id, False):
                current_font_style = USER_FONT_CHOICES.get(user_id, 'stylized')
                me = await client.get_me()
                # Ensure current_name is a string, even if first_name is None
                current_name = me.first_name or ""
                
                # Remove existing clock from name (more robustly)
                # This regex tries to remove a space followed by clock characters at the end
                base_name = re.sub(r'\s+[' + re.escape(ALL_CLOCK_CHARS) + r':\s]+$', '', current_name).strip()
                # If only clock chars were present, base_name might become empty, handle this?
                if not base_name: base_name = me.username or f"User_{user_id}" # Fallback if name removed completely

                # Get current time and format it
                tehran_time = datetime.now(TEHRAN_TIMEZONE)
                current_time_str = tehran_time.strftime("%H:%M")
                stylized_time = stylize_time(current_time_str, current_font_style)
                
                # Combine base name and stylized time
                new_name = f"{base_name} {stylized_time}"
                
                # Update profile only if the name has actually changed
                if new_name != current_name:
                    # Limit name length to Telegram's max (usually 64 chars)
                    await client.update_profile(first_name=new_name[:64])
            
            # Calculate sleep duration until the start of the next minute
            now = datetime.now(TEHRAN_TIMEZONE)
            sleep_duration = 60 - now.second + 0.1 # Add a small buffer
            await asyncio.sleep(sleep_duration)

        except (UserDeactivated, AuthKeyUnregistered):
            logging.error(f"Clock Task: Session for user_id {user_id} is invalid. Stopping task.")
            break # Exit the loop for this user
        except FloodWait as e:
            logging.warning(f"Clock Task: Flood wait of {e.value}s for user_id {user_id}.")
            await asyncio.sleep(e.value + 5) # Wait longer than the flood wait
        except Exception as e:
            logging.error(f"An error occurred in clock task for user_id {user_id}: {e}", exc_info=True)
            await asyncio.sleep(60) # Wait a minute before retrying after an error
    
    logging.info(f"Clock task for user_id {user_id} has stopped.")


# NEW: Task for TimeBio, with Date functionality
async def update_profile_bio(client: Client, user_id: int):
    """Background task to update the user's bio with time and/or date."""
    logging.info(f"Starting TimeBio loop for user_id {user_id}...")
    last_bio_set = None # Cache last set bio to avoid redundant updates

    while user_id in ACTIVE_BOTS:
        try:
            is_clock = TIME_BIO_STATUS.get(user_id, False)
            is_date = TIME_DATE_STATUS.get(user_id, False)
            
            # If copy mode is on, skip bio update
            if COPY_MODE_STATUS.get(user_id, False):
                await asyncio.sleep(60)
                continue
            
            new_bio = "" # Default empty bio
            
            # If clock or date is on
            if is_clock or is_date:
                bio_parts = []
                now_tehran = datetime.now(TEHRAN_TIMEZONE)

                # Add Time (if clock is on, OR if date is on)
                # Per user request: "تاریخ روشن کردم هردو دقیق بشن"
                if is_clock or is_date:
                    font_style = USER_FONT_CHOICES.get(user_id, 'stylized')
                    time_str = now_tehran.strftime("%H:%M")
                    stylized_time = stylize_time(time_str, font_style)
                    bio_parts.append(stylized_time)

                # Add Date (if date is on)
                if is_date:
                    date_format = TIME_DATE_FORMAT.get(user_id, 'jalali') # Default to Jalali (Persian)
                    date_str_raw = ""
                    
                    if date_format == 'jalali':
                        now_jalali = jdatetime.datetime.now(TEHRAN_TIMEZONE)
                        date_str_raw = now_jalali.strftime("%Y/%m/%d")
                    else: # gregorian
                        date_str_raw = now_tehran.strftime("%Y/%m/%d")
                    
                    # Use 'superscript' as the "small" font
                    stylized_date = stylize_time(date_str_raw, 'superscript')
                    bio_parts.append(stylized_date)

                new_bio = " | ".join(bio_parts)

            # Update profile only if bio has changed
            if new_bio != last_bio_set:
                await client.update_profile(bio=new_bio[:70]) # Apply 70 char limit
                last_bio_set = new_bio

            # Calculate sleep duration (same as clock)
            now_seconds = datetime.now(TEHRAN_TIMEZONE).second
            sleep_duration = 60 - now_seconds + 0.1
            await asyncio.sleep(sleep_duration)

        except (UserDeactivated, AuthKeyUnregistered):
            logging.error(f"TimeBio Task: Session for user_id {user_id} is invalid. Stopping task.")
            break
        except FloodWait as e:
            logging.warning(f"TimeBio Task: Flood wait of {e.value}s for user_id {user_id}.")
            last_bio_set = None # Force update after flood wait
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            logging.error(f"An error occurred in TimeBio task for user_id {user_id}: {e}", exc_info=True)
            last_bio_set = None # Force update after error
            await asyncio.sleep(60)

    logging.info(f"TimeBio task for user_id {user_id} has stopped.")


async def anti_login_task(client: Client, user_id: int):
    """Background task to terminate unauthorized sessions."""
    logging.info(f"Starting anti-login task for user_id {user_id}...")
    while user_id in ACTIVE_BOTS:
        try:
            # Check if feature is enabled and 'functions' module was imported
            if ANTI_LOGIN_STATUS.get(user_id, False) and functions:
                auths = await client.invoke(functions.account.GetAuthorizations())
                
                current_hash = None
                # Find the hash of the current session
                for auth in auths.authorizations:
                    if auth.current:
                        current_hash = auth.hash
                        break
                
                # If current session found, terminate others
                if current_hash:
                    sessions_terminated = 0
                    for auth in auths.authorizations:
                        if not auth.current: # Terminate if not the current session
                            try:
                                await client.invoke(functions.account.ResetAuthorization(hash=auth.hash))
                                sessions_terminated += 1
                                logging.info(f"Anti-Login: Terminated session for user {user_id} (Hash: {auth.hash})")
                                # Send notification to user
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
                    #if sessions_terminated > 0:
                    #    logging.info(f"Anti-Login: Terminated {sessions_terminated} session(s) for user {user_id}.")

            # Wait before checking again
            await asyncio.sleep(60 * 5) # Check every 5 minutes

        except (UserDeactivated, AuthKeyUnregistered):
            logging.error(f"Anti-Login Task: Session for user_id {user_id} is invalid. Stopping task.")
            break # Exit loop
        except AttributeError:
             # This happens if 'functions' could not be imported
             logging.error(f"Anti-Login Task: 'pyrogram.raw.functions' module not available for user_id {user_id}. Feature disabled.")
             ANTI_LOGIN_STATUS[user_id] = False # Disable the feature for this user
             await asyncio.sleep(3600) # Sleep for an hour if disabled
        except Exception as e:
            logging.error(f"An error occurred in anti-login task for user_id {user_id}: {e}", exc_info=True)
            await asyncio.sleep(120) # Wait 2 minutes after an error

    logging.info(f"Anti-login task for user_id {user_id} has stopped.")


# UPDATED: status_action_task to include all new statuses
async def status_action_task(client: Client, user_id: int):
    """Background task to send Typing or Playing status actions."""
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

            # Prioritize which action to send
            action_to_send = None
            if typing_mode: action_to_send = ChatAction.TYPING
            elif playing_mode: action_to_send = ChatAction.PLAYING
            elif record_voice: action_to_send = ChatAction.RECORD_AUDIO
            elif upload_photo: action_to_send = ChatAction.UPLOAD_PHOTO
            elif watch_gif: action_to_send = ChatAction.CHOOSE_STICKER # Note: Pyrogram might map this
            elif record_video: action_to_send = ChatAction.RECORD_VIDEO
            elif choose_sticker: action_to_send = ChatAction.CHOOSE_STICKER
            elif upload_video: action_to_send = ChatAction.UPLOAD_VIDEO
            elif upload_doc: action_to_send = ChatAction.UPLOAD_DOCUMENT
            elif upload_audio: action_to_send = ChatAction.UPLOAD_AUDIO
            elif speaking_mode: action_to_send = ChatAction.SPEAKING

            if not action_to_send:
                await asyncio.sleep(5) # No action active, check again soon
                continue

            # Refresh chat list if needed
            now = asyncio.get_event_loop().time()
            if not chat_ids_cache or (now - last_dialog_fetch_time > FETCH_INTERVAL):
                logging.info(f"Status Action: Refreshing dialog list for user_id {user_id}...")
                new_chat_ids = []
                try:
                    async for dialog in client.get_dialogs(limit=75):
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
                     logging.debug(f"Status Action: Not participant in chat {chat_id}. Removing from cache.") # Log as debug
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


# --- Feature Handlers ---
async def translate_text(text: str, target_lang: str = "fa") -> str:
    """Translates text using Google Translate API."""
    if not text or not target_lang: return text
    encoded_text = quote(text)
    # Use a different client URL to potentially avoid blocks
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={encoded_text}"
    try:
        # Use a longer timeout and specific headers
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    try:
                        data = await response.json(content_type=None) # Allow non-json content type
                        # Handle potential variations in response structure
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
        logging.error(f"Translation request failed: {e}", exc_info=True) # Log full traceback
    return text


# FIXED: outgoing_message_modifier to correctly handle HTML formatting and replies
async def outgoing_message_modifier(client, message):
    """Modifies outgoing text messages (bold, translate, etc.) if enabled."""
    user_id = client.me.id
    
    # Check if message object is valid
    if not message or not message.text:
        return
        
    # Check if it's a command
    if COMMAND_REGEX.match(message.text.strip()):
        return

    # Check for *existing* entities (like links, bold, etc. already present)
    # This prevents double-formatting
    if message.entities:
        return
        
    original_text = message.text
    modified_text = original_text
    needs_edit = False
    parse_mode = None # Default
    
    # --- Auto Translate ---
    target_lang = AUTO_TRANSLATE_TARGET.get(user_id)
    if target_lang:
        translated = await translate_text(modified_text, target_lang)
        if translated != modified_text:
             modified_text = translated
             needs_edit = True
             # Use translated text as new base for formatting
             original_text_for_formatting = translated
        else:
             original_text_for_formatting = original_text
    else:
        original_text_for_formatting = original_text

    # --- Auto Formatting ---
    is_bold = BOLD_MODE_STATUS.get(user_id, False)
    is_italic = ITALIC_MODE_STATUS.get(user_id, False)
    is_underline = UNDERLINE_MODE_STATUS.get(user_id, False)
    is_link = LINK_MODE_STATUS.get(user_id, False)

    if is_bold or is_italic or is_underline or is_link:
        parse_mode = ParseMode.HTML # Use Pyrogram's Enum
        
        # 1. Escape the text *first* to prevent HTML injection
        text_to_format = modified_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # 2. Apply text formatting (order matters for nesting)
        if is_bold:
            text_to_format = f"<b>{text_to_format}</b>"
        if is_italic:
            text_to_format = f"<i>{text_to_format}</i>"
        if is_underline:
            text_to_format = f"<u>{text_to_format}</u>"
            
        # 3. Apply link *around* the formatted text
        if is_link:
            modified_text = f'<a href="tg://openmessage?user_id={user_id}">{text_to_format}</a>'
        else:
            modified_text = text_to_format
            
        # 4. Mark for edit
        if modified_text != original_text_for_formatting:
             needs_edit = True

    # --- Edit Message ---
    if needs_edit:
        try:
            # Edit with the determined parse_mode
            await message.edit_text(modified_text, parse_mode=parse_mode, disable_web_page_preview=True)
        except FloodWait as e:
             logging.warning(f"Outgoing Modifier: Flood wait editing msg {message.id} for user {user_id}: {e.value}s")
             await asyncio.sleep(e.value + 1)
        except (MessageNotModified, MessageIdInvalid):
             pass # Ignore errors if message wasn't modified or was deleted
        except Exception as e:
            logging.warning(f"Outgoing Modifier: Could not edit msg {message.id} (ParseMode: {parse_mode}) for user {user_id}: {e}")
    

async def enemy_handler(client, message):
    """Replies with a random insult if the sender is marked as an enemy."""
    user_id = client.me.id
    # Use the replacement texts
    replies = REPLACEMENT_TEXTS
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
    """Replies with a random friendly message if the sender is marked as a friend."""
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
    """Sends an auto-reply in PV if secretary mode is on and user hasn't been replied to yet."""
    owner_user_id = client.me.id
    # Check conditions: private chat, not self, not bot, secretary mode on
    if (message.chat.type == ChatType.PRIVATE and
            message.from_user and not message.from_user.is_self and
            not message.from_user.is_bot and
            SECRETARY_MODE_STATUS.get(owner_user_id, False)):

        target_user_id = message.from_user.id
        
        # Also check if user is AFK, if so, AFK handler takes priority
        if AFK_STATUS.get(owner_user_id):
            return # Let AFK handler manage the reply

        # Use setdefault to ensure the set exists for the owner
        replied_users_today = USERS_REPLIED_IN_SECRETARY.setdefault(owner_user_id, set())
        
        # Check if user has already been replied to
        if target_user_id not in replied_users_today:
            # Use custom message if available, otherwise default
            reply_message_text = CUSTOM_SECRETARY_MESSAGES.get(owner_user_id, DEFAULT_SECRETARY_MESSAGE)
            try:
                await message.reply_text(reply_message_text, quote=True)
                # Add user to replied set *after* successful reply
                replied_users_today.add(target_user_id)
            except FloodWait as e:
                 logging.warning(f"Secretary Handler: Flood wait replying for user {owner_user_id}: {e.value}s")
                 await asyncio.sleep(e.value + 1)
                 # Optionally retry once after flood wait?
            except Exception as e:
                logging.warning(f"Secretary Handler: Could not auto-reply to user {target_user_id} for owner {owner_user_id}: {e}")


async def pv_lock_handler(client, message):
    """Deletes incoming messages in PV if PV lock is enabled."""
    owner_user_id = client.me.id
    if PV_LOCK_STATUS.get(owner_user_id, False):
        try:
            await message.delete()
        except FloodWait as e:
             logging.warning(f"PV Lock: Flood wait deleting message {message.id} for user {owner_user_id}: {e.value}s")
             await asyncio.sleep(e.value + 1)
        except MessageIdInvalid:
             pass # Message already deleted
        except Exception as e:
            # Avoid logging too verbosely for common errors like message deletion failure
            if "Message to delete not found" not in str(e):
                 logging.warning(f"PV Lock: Could not delete message {message.id} for user {owner_user_id}: {e}")


async def incoming_message_manager(client, message):
    """Handles auto-reactions and muting for incoming messages."""
    try:
        # Basic checks first
        if not message.from_user or message.from_user.is_self or message.chat is None: # Added check for message.chat
             return
        
        user_id = client.me.id # Owner ID
        sender_id = message.from_user.id
        chat_id = message.chat.id

        # --- Mute User ---
        muted_list = MUTED_USERS.get(user_id, set())
        if (sender_id, chat_id) in muted_list:
            try:
                await message.delete()
                return # Stop processing if message deleted
            except FloodWait as e:
                 logging.warning(f"Mute: Flood wait deleting msg {message.id} for owner {user_id}: {e.value}s")
                 await asyncio.sleep(e.value + 1)
                 return # Still return after wait
            except MessageIdInvalid:
                 return # Message already deleted, nothing more to do
            except Exception as e:
                 if "Message to delete not found" not in str(e):
                      logging.warning(f"Mute: Could not delete msg {message.id} from {sender_id} for owner {user_id}: {e}")
                 # Proceed to reaction even if delete fails
                 pass # Let's proceed to reaction even if delete fails, maybe permissions are weird

        # --- Auto Reaction ---
        reaction_map = AUTO_REACTION_TARGETS.get(user_id, {})
        if emoji := reaction_map.get(sender_id):
            try:
                await client.send_reaction(chat_id, message.id, emoji)
            except ReactionInvalid:
                 logging.warning(f"Reaction: Invalid emoji '{emoji}' for user {user_id} reacting to {sender_id}.")
                 try: # Notify owner about invalid emoji
                     await client.send_message(user_id, f"⚠️ **خطا:** ایموجی `{emoji}` برای واکنش به کاربر {sender_id} نامعتبر است. این تنظیم واکنش خودکار حذف شد.")
                 except Exception: pass
                 # Remove invalid setting
                 if user_id in AUTO_REACTION_TARGETS and sender_id in AUTO_REACTION_TARGETS[user_id]:
                     del AUTO_REACTION_TARGETS[user_id][sender_id]
            except FloodWait as e:
                 logging.warning(f"Reaction: Flood wait for user {user_id} reacting to {sender_id}: {e.value}s")
                 await asyncio.sleep(e.value + 1)
            except MessageIdInvalid:
                 pass # Message might have been deleted between mute check and reaction
            except Exception as e:
                 # Avoid overly verbose logging for common reaction errors
                 if "MESSAGE_ID_INVALID" not in str(e):
                     logging.error(f"Reaction: Error for user {user_id} on msg {message.id}: {e}")
                
    except PeerIdInvalid as e_peer:
        # Log less verbosely for PeerIdInvalid as it can be common
        logging.debug(f"Incoming Manager: Caught PeerIdInvalid processing message {getattr(message, 'id', 'N/A')}: {e_peer}. Skipping message.")
    except Exception as e_main:
        logging.error(f"Incoming Manager: Unhandled error processing message {getattr(message, 'id', 'N/A')}: {e_main}", exc_info=True)
    

async def auto_seen_handler(client, message):
    """Marks messages in private chats as read if auto-seen is enabled."""
    user_id = client.me.id
    # Ensure it's a private chat and auto-seen is on
    if message.chat.type == ChatType.PRIVATE and AUTO_SEEN_STATUS.get(user_id, False):
        try:
            await client.read_chat_history(message.chat.id)
        except FloodWait as e:
             logging.warning(f"AutoSeen: Flood wait marking chat {message.chat.id} read: {e.value}s")
             await asyncio.sleep(e.value + 1)
        except Exception as e:
             # Log less verbosely if chat is inaccessible
             if "Could not find the input peer" not in str(e):
                 logging.warning(f"AutoSeen: Could not mark chat {message.chat.id} as read: {e}")


# NEW: Handler for saving timed media (from bot.txt)
async def save_timed_media_handler(client, message):
    """Handles saving of timed photos and videos in PV."""
    user_id = client.me.id
    try:
        is_timed = False
        media_type = None
        file_id = None
        extension = None
        ttl = 0
        
        if message.photo and message.photo.ttl_seconds:
            is_timed = True
            media_type = "photo"
            file_id = message.photo.file_id
            extension = "jpg"
            ttl = message.photo.ttl_seconds
        elif message.video and message.video.ttl_seconds:
            is_timed = True
            media_type = "video"
            file_id = message.video.file_id
            extension = "mp4"
            ttl = message.video.ttl_seconds

        if is_timed:
            logging.info(f"Timed {media_type} detected from user {message.from_user.id} for owner {user_id}.")
            rand = random.randint(1000, 9999999)
            local_path = f"downloads/{media_type}-{rand}.{extension}"
            
            # Ensure downloads directory exists
            os.makedirs("downloads", exist_ok=True)
            
            await client.download_media(message=file_id, file_name=local_path)
            
            caption = (
                f"🔥 **مدیای زمان‌دار ذخیره شد** 🔥\n"
                f"**از:** {message.from_user.first_name} (`{message.from_user.id}`)\n"
                f"**نوع:** {media_type} ({ttl}s)\n"
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
        if 'local_path' in locals() and os.path.exists(local_path):
            try: os.remove(local_path)
            except Exception: pass

# NEW: Handler for login codes (from bot.txt)
async def code_expire_handler(client, message):
    """Forwards login codes from 777000 to Saved Messages."""
    user_id = client.me.id
    try:
        logging.info(f"Login code detected for user {user_id}. Forwarding to 'me'...")
        await message.forward("me")
    except FloodWait as e:
        logging.warning(f"Code Expire Handler: Flood wait forwarding code for user {user_id}: {e.value}s")
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"Code Expire Handler: Error forwarding login code for user {user_id}: {e}", exc_info=True)


# NEW: Handler for AFK replies
async def afk_handler(client, message):
    """Checks for mentions or PV messages while AFK."""
    user_id = client.me.id
    
    # Check if user is AFK
    afk_data = AFK_STATUS.get(user_id)
    if not afk_data:
        return
        
    # Check if we were mentioned or if it's a PV
    mentioned = False
    sender_id = 0
    if message.from_user:
        sender_id = message.from_user.id
        
    if message.mentioned:
        mentioned = True
    elif message.chat.type == ChatType.PRIVATE:
        # Ignore self, bots, and service messages in PV
        if sender_id and sender_id != user_id and not message.from_user.is_bot and not message.service:
            mentioned = True 
            
    if mentioned:
        # Don't reply to self
        if sender_id == user_id:
            return
            
        # Don't reply if the sender is also AFK (prevent loops)
        if AFK_STATUS.get(sender_id):
            return
            
        since = afk_data.get("since", "???")
        reason = afk_data.get("reason", "")
        
        reply_text = f"**من در حال حاضر `AFK` هستم.** (از: {since})"
        if reason:
            reply_text += f"\n**دلیل:** {reason}"
            
        try:
            await message.reply_text(reply_text, quote=True)
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except UserIsBlocked:
             pass # Can't reply if user blocked us
        except Exception as e:
             logging.warning(f"AFK Handler: Could not reply to mention/PV for user {user_id}: {e}")

# NEW: Handler to take user out of AFK on message
async def afk_return_handler(client, message):
    """Takes the user out of AFK mode when they send a message."""
    user_id = client.me.id
    if AFK_STATUS.pop(user_id, None): # Remove AFK status if it exists
        try:
            # Send notification message
            msg = await client.send_message(message.chat.id, "**خوش آمدید! شما دیگر `AFK` نیستید.**")
            # Delete it after a few seconds
            await asyncio.sleep(5)
            await msg.delete()
        except Exception as e:
             logging.warning(f"AFK Return: Could not send/delete return message: {e}")
             
# NEW: Handler for notes
async def note_handler(client, message):
    """Handles note saving and retrieval."""
    user_id = client.me.id
    text = message.text.strip()
    
    # note <name> <text> or note <name> (with reply)
    match_set = re.match(r"^(note|یادداشت) (\S+)(?: (.*))?$", text, re.DOTALL | re.IGNORECASE)
    # notes or لیست یادداشت
    match_list = re.match(r"^(notes|یادداشت ها)$", text, re.IGNORECASE)
    # delnote <name> or حذف یادداشت <name>
    match_del = re.match(r"^(delnote|حذف یادداشت) (\S+)$", text, re.IGNORECASE)
    # note <name> (retrieval)
    match_get = re.match(r"^(note|یادداشت) (\S+)$", text, re.IGNORECASE)

    try:
        user_notes = NOTES.setdefault(user_id, {})
        
        # --- Set Note ---
        if match_set:
            note_name = match_set.group(2).lower()
            note_content = match_set.group(3)
            
            # Check for reply
            if not note_content and message.reply_to_message:
                if message.reply_to_message.text:
                    note_content = message.reply_to_message.text
                # Future: Add support for saving media notes by file_id
                # elif message.reply_to_message.media:
                #    note_content = f"media:{message.reply_to_message.media.file_id}"
                else:
                    await message.edit_text("⚠️ برای ذخیره یادداشت از ریپلای، باید روی متن (یا در آینده مدیا) ریپلای کنید.")
                    return
            
            if not note_content:
                # This is now a "get note" command
                note_content_saved = user_notes.get(note_name)
                if note_content_saved:
                    await message.reply_text(note_content_saved, quote=False, disable_web_page_preview=True)
                    await message.delete()
                else:
                    await message.edit_text(f"⚠️ یادداشتی با نام `{note_name}` یافت نشد. برای ذخیره: `note {note_name} [متن]`")
                return

            user_notes[note_name] = note_content
            # TODO: Add database saving here
            await message.edit_text(f"✅ یادداشت `{note_name}` ذخیره/آپدیت شد.")

        # --- List Notes ---
        elif match_list:
            if not user_notes:
                await message.edit_text("ℹ️ شما هیچ یادداشتی ذخیره نکرده‌اید.")
                return
            
            note_list_text = "**📋 لیست یادداشت‌های شما:**\n\n"
            for note_name in user_notes.keys():
                note_list_text += f"- `{note_name}`\n"
            
            await message.edit_text(note_list_text)

        # --- Delete Note ---
        elif match_del:
            note_name = match_del.group(2).lower()
            if user_notes.pop(note_name, None):
                # TODO: Add database deletion here
                await message.edit_text(f"✅ یادداشت `{note_name}` حذف شد.")
            else:
                await message.edit_text(f"⚠️ یادداشتی با نام `{note_name}` یافت نشد.")

        # --- Get Note (Fallback) ---
        # This handles the case where match_set didn't have content
        elif match_get:
            note_name = match_get.group(2).lower()
            note_content = user_notes.get(note_name)
            
            if note_content:
                await message.reply_text(note_content, quote=False, disable_web_page_preview=True)
                await message.delete()
            else:
                await message.edit_text(f"⚠️ یادداشتی با نام `{note_name}` یافت نشد.")

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"Note Handler: Error for user {user_id}: {e}", exc_info=True)
        try:
            await message.edit_text("⚠️ خطایی در مدیریت یادداشت‌ها رخ داد.")
        except Exception: pass


# --- Command Controllers ---

# UPDATED: help_controller with all new commands
async def help_controller(client, message):
    """Sends the complete help text."""
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
• `پارت [متن]`: ارسال انیمیشنی متن مورد نظر.

**🔹 ساعت و پروفایل 🔹**
• `ساعت روشن` / `خاموش`: نمایش یا حذف ساعت از **نام** پروفایل شما.
• `بیو ساعت روشن` / `خاموش`: نمایش یا حذف ساعت از **بیو** پروفایل شما.
• `تاریخ روشن` / `خاموش`: نمایش یا حذف تاریخ از **بیو** (در کنار ساعت).
• `فونت`: نمایش لیست فونت‌های موجود برای ساعت.
• `فونت [عدد]`: انتخاب فونت جدید برای نمایش ساعت (در نام و بیو).
• `فونت تاریخ 1`: تنظیم فرمت تاریخ بیو به **میلادی** (کوچک).
• `فونت تاریخ 2`: تنظیم فرمت تاریخ بیو به **شمسی (جلالی)** (کوچک).
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
• `تکرار [عدد] [ثانیه]` (ریپلای): تکرار پیام X بار با فاصله Y ثانیه (فاصله اختیاری است).
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
• `تنظیم متن دشمن [متن]`: (غیرفعال - متن‌ها جایگزین شده‌اند).
• `لیست متن دشمن`: نمایش لیست متن‌های جایگزین شده.
• `حذف متن دشمن [عدد]`: (غیرفعال).

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
• `ربات` / `پینگ`: بررسی آنلاین بودن ربات و نمایش سرعت.
• `id`: (در گروه یا با ریپلای) نمایش شناسه چت، کاربر و پیام.
• `info`: (با ریپلای) نمایش اطلاعات کامل کاربر.
• `ویس [متن]`: تبدیل متن فارسی به ویس.
• `یوتوب [LINK]`: دانلود ویدیو از لینک یوتیوب.
• `دیکشنری [کلمه]` / `ud [term]`: جستجو در Urban Dictionary.
• `حساب [عبارت]` / `calc [exp]`: ماشین حساب.
• `کیو آر [متن]` / `qr [text]`: ساخت QR Code از متن.
• `جیسون` (ریپلای): نمایش مرتب JSON.
• `این کیه [id/user]` / `whois [id/user]`: دریافت اطلاعات کاربر.
• `لیست بلاک` / `blocklist`: نمایش کاربران بلاک شده (تا 100).
• `هواشناسی [شهر]`: نمایش اطلاعات آب و هوا.
• `تاس`: ارسال تاس شانسی (تا 6).
• `تاس [عدد ۱-۶]`: ارسال تاس تا رسیدن به عدد مورد نظر.
• `بولینگ`: ارسال بولینگ شانسی (تا استرایک).
• `مربع` | `قلب` | `قلب بزرگ` | `بکیرم` | `مکعب` | `لودینگ`

**🔹 امنیت و مدیریت 🔹**
• `afk [دلیل]` (اختیاری): فعال کردن حالت AFK.
• `afk خاموش`: غیرفعال کردن حالت AFK.
• `note [اسم] [متن]`: ذخیره یک یادداشت. (یا ریپلای `note [اسم]`)
• `note [اسم]`: فراخوانی یادداشت.
• `notes`: نمایش لیست همه یادداشت‌ها.
• `delnote [اسم]`: حذف یادداشت.
• `purge`: (با ریپلای) پاکسازی پیام‌های کاربر در چت (تا 100 پیام).
• `webshot [url]`: اسکرین‌شات از سایت.
• `پیوی قفل` / `باز`: فعال/غیرفعال کردن حذف خودکار تمام پیام‌های دریافتی در PV.
• `منشی روشن` / `خاموش`: فعال/غیرفعال کردن پاسخ خودکار در PV.
• `منشی متن [متن دلخواه]`: تنظیم متن سفارشی برای منشی.
• `منشی متن` (بدون متن): بازگرداندن متن منشی به پیش‌فرض.
• `انتی لوگین روشن` / `خاموش`: خروج خودکار نشست‌های (sessions) جدید و غیرفعال.

**🔹 ابزار گروه (نیازمند ادمین) 🔹**
• `تگ همه` / `تگ همگانی`: منشن کردن تمام اعضای گروه (با تاخیر).
• `جستجو [متن]`: جستجوی کاربر بر اساس نام/یوزرنیم در گروه.
• `پین` (ریپلای): پین کردن پیام ریپلای شده.
• `آنپین` (ریپلای): آنپین کردن پیام ریپلای شده.
• `ادمین` (ریپلای): ادمین کردن کاربر.
• `عزل` (ریپلای): عزل کردن ادمین.
• `ترک`: خروج ربات از گروه یا کانال.
"""
    try:
        await message.edit_text(help_text_formatted, disable_web_page_preview=True)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception as e:
        logging.error(f"Help Controller: Error editing help message: {e}", exc_info=True)


async def translate_controller(client, message):
    """Translates a replied message to Persian."""
    user_id = client.me.id
    if (message.reply_to_message and
        hasattr(message.reply_to_message, 'text') and message.reply_to_message.text and
        hasattr(message.reply_to_message, 'from_user') and message.reply_to_message.from_user):
        
        # Avoid translating own messages
        if message.reply_to_message.from_user.is_self:
             try:
                 await message.edit_text("ℹ️ برای ترجمه، روی پیام کاربر دیگر ریپلای کنید.")
             except Exception: pass
             return

        text_to_translate = message.reply_to_message.text
        
        if len(text_to_translate) > 1000:
            try:
                await message.edit_text("⚠️ متن برای ترجمه بیش از حد طولانی است (حداکثر 1000 کاراکتر).")
            except Exception: pass
            return

        try:
            await message.edit_text("⏳ در حال ترجمه...")
            translated = await translate_text(text_to_translate, "fa") # Target language Persian
            
            if translated and translated != text_to_translate:
                await message.edit_text(translated)
            else:
                await message.edit_text("ℹ️ ترجمه انجام نشد یا متن اصلی و ترجمه یکسان بودند.")
                
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception as e:
            logging.error(f"Translate Controller: Error translating text for user {user_id}: {e}", exc_info=True)
            try:
                await message.edit_text("⚠️ خطایی در سرویس ترجمه رخ داد.")
            except Exception: pass
    else:
        try:
            await message.edit_text("⚠️ برای ترجمه، روی یک پیام متنی ریپلای کنید.")
        except MessageNotModified:
            pass
        except Exception as e_edit_warn:
             logging.warning(f"Translate: Failed to edit warning message: {e_edit_warn}")


# UPDATED: toggle_controller to include all new features
async def toggle_controller(client, message):
    """Handles various on/off toggle commands."""
    user_id = client.me.id
    command = message.text.strip()
    feature = ""
    new_status = False
    status_changed = False
    feedback_msg = None

    try:
        if command.endswith("روشن"):
            feature = command[:-5].strip()
            new_status = True
        elif command.endswith("خاموش"):
            feature = command[:-6].strip()
            new_status = False
        
        # Find the corresponding status dict
        status_map = {
            "بولد": BOLD_MODE_STATUS,
            "سین": AUTO_SEEN_STATUS,
            "منشی": SECRETARY_MODE_STATUS,
            "انتی لوگین": ANTI_LOGIN_STATUS,
            "تایپ": TYPING_MODE_STATUS,
            "بازی": PLAYING_MODE_STATUS,
            "ضبط ویس": RECORD_VOICE_STATUS,
            "عکس": UPLOAD_PHOTO_STATUS,
            "گیف": WATCH_GIF_STATUS,
            "دشمن": ENEMY_ACTIVE,
            "دوست": FRIEND_ACTIVE,
            "بیو ساعت": TIME_BIO_STATUS,
            "ایتالیک": ITALIC_MODE_STATUS,
            "زیرخط": UNDERLINE_MODE_STATUS,
            "لینک": LINK_MODE_STATUS,
            "ضبط ویدیو": RECORD_VIDEO_STATUS,
            "استیکر": CHOOSE_STICKER_STATUS,
            "آپلود ویدیو": UPLOAD_VIDEO_STATUS,
            "آپلود فایل": UPLOAD_DOCUMENT_STATUS,
            "آپلود صدا": UPLOAD_AUDIO_STATUS,
            "صحبت": SPEAKING_STATUS,
            "تاریخ": TIME_DATE_STATUS, # <--- NEW
        }

        if feature in status_map:
            status_dict = status_map[feature]
            current_status = status_dict.get(user_id, False)
            
            if current_status != new_status:
                status_dict[user_id] = new_status
                status_changed = True
                
                # Special actions on toggle
                if feature == "منشی" and not new_status:
                    USERS_REPLIED_IN_SECRETARY[user_id] = set() # Clear replied list when turning off
                
                # Handle mutual exclusivity for typing/playing/etc.
                if new_status and feature in ["تایپ", "بازی", "ضبط ویس", "عکس", "گیف", "ضبط ویدیو", "استیکر", "آپلود ویدیو", "آپلود فایل", "آپلود صدا", "صحبت"]:
                    for f_name, s_dict in status_map.items():
                        if f_name != feature and f_name in ["تایپ", "بازی", "ضبط ویس", "عکس", "گیف", "ضبط ویدیو", "استیکر", "آپلود ویدیو", "آپلود فایل", "آپلود صدا", "صحبت"]:
                            s_dict[user_id] = False # Turn off other actions
                
                status_text = "فعال" if new_status else "غیرفعال"
                feedback_msg = f"✅ **{feature} {status_text} شد.**"
            else:
                status_text = "فعال" if new_status else "غیرفعال"
                feedback_msg = f"ℹ️ {feature} از قبل {status_text} بود."
        else:
            feedback_msg = "⚠️ دستور نامشخص." # Should not happen if regex matches

        if feedback_msg:
            await message.edit_text(feedback_msg)
            
        # Trigger immediate bio update if bio clock/date changed
        if feature in ["بیو ساعت", "تاریخ"]:
            asyncio.create_task(update_profile_bio(client, user_id))

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
    """Handles language setting for auto-translate."""
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
            # Match "ترجمه [code]"
            match = re.match(r"ترجمه ([a-z]{2}(?:-[a-z]{2})?)", command)
            if match:
                lang = match.group(1)
                if current_lang != lang:
                    AUTO_TRANSLATE_TARGET[user_id] = lang
                    feedback_msg = f"✅ ترجمه خودکار به زبان {lang} فعال شد."
                else:
                    feedback_msg = f"ℹ️ ترجمه خودکار به زبان {lang} از قبل فعال بود."
            else:
                 feedback_msg = "⚠️ فرمت دستور نامعتبر. مثال: `ترجمه en`"

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
    """Sets or resets the secretary auto-reply message."""
    user_id = client.me.id
    match = re.match(r"^منشی متن(?: |$)(.*)", message.text, re.DOTALL | re.IGNORECASE) # Added ignorecase
    text = match.group(1).strip() if match else None # Use None to distinguish no match from empty text

    try:
        if text is not None: # Command was matched
            if text: # User provided custom text
                if CUSTOM_SECRETARY_MESSAGES.get(user_id) != text:
                    CUSTOM_SECRETARY_MESSAGES[user_id] = text
                    await message.edit_text(f"✅ متن سفارشی منشی تنظیم شد:\n\n{text[:100]}...") # Show preview
                else:
                    await message.edit_text("ℹ️ متن سفارشی منشی بدون تغییر باقی ماند (متن جدید مشابه قبلی است).")
            else: # User sent "منشی متن" without text to reset
                if user_id in CUSTOM_SECRETARY_MESSAGES:
                    CUSTOM_SECRETARY_MESSAGES.pop(user_id) # Remove custom text to use default
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
    """Toggles PV lock mode."""
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
    """Copies target user's profile info or restores original."""
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
                try:
                    photo_bytes_io = BytesIO(original_photo_data)
                    photo_bytes_io.name = "original_profile.jpg" # Give it a name
                    await client.set_profile_photo(photo=photo_bytes_io)
                except Exception as e_set_photo:
                     logging.warning(f"Copy Profile (Revert): Could not set original photo for user {user_id}: {e_set_photo}")

            COPY_MODE_STATUS[user_id] = False # Set status after successful operations
            await message.edit_text("✅ پروفایل با موفقیت به حالت اصلی بازگردانده شد.")
            
            # Trigger immediate bio/clock update after reverting
            # This task runs in the background, we don't need to await it
            asyncio.create_task(update_profile_bio(client, user_id))
            asyncio.create_task(update_profile_clock(client, user_id))
            return

        # Logic for "کپی روشن"
        elif command == "کپی روشن":
            target_user = message.reply_to_message.from_user
            target_id = target_user.id
            
            # --- Backup Current Profile ---
            await message.edit_text("⏳ در حال ذخیره پروفایل فعلی...")
            me = await client.get_me()
            me_photo_bytes = None
            me_bio = ""
            try:
                me_full = await client.get_chat("me") # get_chat is often more reliable for bio
                me_bio = me_full.bio or ''
            except Exception as e_get_bio:
                 logging.warning(f"Copy Profile (Backup): Could not get own bio for user {user_id}: {e_get_bio}")

            if me.photo:
                try:
                    me_photo_stream = await client.download_media(me.photo.big_file_id, in_memory=True)
                    if isinstance(me_photo_stream, BytesIO):
                         me_photo_bytes = me_photo_stream.getvalue()
                except Exception as e_download_me:
                     logging.warning(f"Copy Profile (Backup): Could not download own photo for user {user_id}: {e_download_me}")

            ORIGINAL_PROFILE_DATA[user_id] = {
                'first_name': me.first_name or '',
                'last_name': me.last_name or '',
                'bio': me_bio,
                'photo': me_photo_bytes # Store bytes or None
            }

            # --- Get Target Profile Info ---
            await message.edit_text("⏳ در حال دریافت اطلاعات پروفایل هدف...")
            target_photo_bytes_io = None # We need BytesIO for set_profile_photo
            target_bio = ""
            try:
                 target_chat = await client.get_chat(target_id) # get_chat for bio
                 target_bio = target_chat.bio or ''
            except Exception as e_get_target_bio:
                 logging.warning(f"Copy Profile (Target): Could not get target bio for user {target_id}: {e_get_target_bio}")

            if target_user.photo:
                try:
                    target_photo_stream = await client.download_media(target_user.photo.big_file_id, in_memory=True)
                    if isinstance(target_photo_stream, BytesIO):
                        target_photo_bytes_io = target_photo_stream
                        target_photo_bytes_io.name = "target_profile.jpg" # Give it a name
                except Exception as e_download_target:
                    logging.warning(f"Copy Profile (Target): Could not download target photo for user {target_id}: {e_download_target}")

            # --- Apply Target Profile ---
            await message.edit_text("⏳ در حال اعمال پروفایل هدف...")
            
            # Delete existing photos first
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
                     
            # Update name and bio *after* photo operations
            await client.update_profile(
                first_name=(target_user.first_name or '')[:64], # Apply limits
                last_name=(target_user.last_name or '')[:64],
                bio=target_bio[:70]
            )

            COPY_MODE_STATUS[user_id] = True
            await message.edit_text("✅ پروفایل کاربر کپی شد (نام، نام خانوادگی، بیو، عکس).")

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception as e:
        logging.error(f"Copy Profile Controller: Error for user {user_id} processing command '{command}': {e}", exc_info=True)
        try:
            error_text = f"⚠️ خطایی در عملیات کپی پروفایل رخ داد: {type(e).__name__}"
            await message.edit_text(error_text)
        except Exception:
            pass


# NEW: Controller for SetName (from bot.txt)
async def set_name_controller(client, message):
    """Sets profile name based on replied text."""
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.text:
        try:
            new_name = message.reply_to_message.text[:64] # Apply 64 char limit
            await client.update_profile(first_name=new_name)
            await message.edit_text(f"✅ نام با موفقیت به `{new_name}` تغییر یافت.")
            
            # Trigger clock update immediately
            asyncio.create_task(update_profile_clock(client, user_id))
            
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception as e:
            logging.error(f"SetName Controller: Error for user {user_id}: {e}", exc_info=True)
            await message.edit_text(f"⚠️ خطایی در تنظیم نام رخ داد: {type(e).__name__}")
    else:
        await message.edit_text("⚠️ برای تنظیم نام، روی یک پیام متنی ریپلای کنید.")


# NEW: Controller for SetBio (from bot.txt)
async def set_bio_controller(client, message):
    """Sets profile bio based on replied text."""
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.text:
        try:
            new_bio = message.reply_to_message.text[:70] # Apply 70 char limit
            await client.update_profile(bio=new_bio)
            await message.edit_text(f"✅ بیو با موفقیت به `{new_bio}` تغییر یافت.")
            
            # Disable auto bio features if bio is set manually
            if TIME_BIO_STATUS.get(user_id, False) or TIME_DATE_STATUS.get(user_id, False):
                TIME_BIO_STATUS[user_id] = False
                TIME_DATE_STATUS[user_id] = False
                await message.reply_text("ℹ️ `بیو ساعت` و `تاریخ` خودکار غیرفعال شدند.")
                
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception as e:
            logging.error(f"SetBio Controller: Error for user {user_id}: {e}", exc_info=True)
            await message.edit_text(f"⚠️ خطایی در تنظیم بیو رخ داد: {type(e).__name__}")
    else:
        await message.edit_text("⚠️ برای تنظیم بیو، روی یک پیام متنی ریپلای کنید.")


# NEW: Controller for SetProfile (from bot.txt)
async def set_profile_controller(client, message):
    """Sets profile photo/video based on replied media."""
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
            try: os.remove(local_path)
            except Exception: pass


async def set_enemy_controller(client, message):
    """Adds a user to the enemy list via reply."""
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        
        # Prevent adding self
        if target_id == user_id:
            await message.edit_text("⚠️ شما نمی‌توانید خودتان را به لیست دشمن اضافه کنید.")
            return
            
        enemies = ENEMY_LIST.setdefault(user_id, set())
        if target_id not in enemies:
             enemies.add(target_id)
             await message.edit_text(f"✅ کاربر با آیدی `{target_id}` به لیست دشمن اضافه شد.")
        else:
            await message.edit_text(f"ℹ️ کاربر با آیدی `{target_id}` از قبل در لیست دشمن بود.")
    else:
        await message.edit_text("⚠️ برای افزودن به لیست دشمن، روی پیام کاربر مورد نظر ریپلای کنید.")


async def delete_enemy_controller(client, message):
    """Removes a user from the enemy list via reply."""
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        enemies = ENEMY_LIST.get(user_id) # No setdefault needed here
        if enemies and target_id in enemies:
            enemies.remove(target_id)
            await message.edit_text(f"✅ کاربر با آیدی `{target_id}` از لیست دشمن حذف شد.")
        else:
            await message.edit_text(f"ℹ️ کاربر با آیدی `{target_id}` در لیست دشمن یافت نشد.")
    else:
        await message.edit_text("⚠️ برای حذف از لیست دشمن، روی پیام کاربر مورد نظر ریپلای کنید.")


async def clear_enemy_list_controller(client, message):
    """Clears all users from the enemy list."""
    user_id = client.me.id
    if ENEMY_LIST.get(user_id): # Check if the list exists and is not empty
        ENEMY_LIST[user_id] = set()
        await message.edit_text("✅ لیست دشمن با موفقیت پاکسازی شد.")
    else:
        await message.edit_text("ℹ️ لیست دشمن از قبل خالی بود.")


async def list_enemies_controller(client, message):
    """Lists all users in the enemy list."""
    user_id = client.me.id
    enemies = ENEMY_LIST.get(user_id, set())
    if not enemies:
        await message.edit_text("ℹ️ لیست دشمن خالی است.")
        return

    list_items = []
    # Fetch user info in chunks for efficiency
    enemy_ids = list(enemies)
    chunk_size = 100
    for i in range(0, len(enemy_ids), chunk_size):
        chunk = enemy_ids[i:i+chunk_size]
        try:
            users = await client.get_users(chunk)
            for user in users:
                display_name = f"{user.first_name}" + (f" {user.last_name}" if user.last_name else "")
                list_items.append(f"- {display_name} (`{user.id}`)")
        except Exception as e:
            logging.warning(f"List Enemies: Could not fetch info for chunk: {e}")
            # Add remaining as IDs
            for user_id_in_chunk in chunk:
                 # Avoid adding if already added
                 if not any(f"`{user_id_in_chunk}`" in item for item in list_items):
                     list_items.append(f"- User ID: `{user_id_in_chunk}` (اطلاعات قابل دریافت نیست)")

    list_text = "**📋 لیست دشمنان:**\n" + "\n".join(list_items)
    # Handle potential message too long error
    if len(list_text) > 4096:
        list_text = list_text[:4090] + "\n[...]" # Truncate if too long
    await message.edit_text(list_text)


async def list_enemy_replies_controller(client, message):
    """Lists all custom replies for the enemy list."""
    user_id = client.me.id
    # Use the replacement texts
    replies = REPLACEMENT_TEXTS
    list_text = "**📋 لیست متن‌های دشمن (جایگزین شده):**\n" + "\n".join([f"{i+1}. `{reply}`" for i, reply in enumerate(replies)])
    if len(list_text) > 4096:
        list_text = list_text[:4090] + "\n[...]"
    await message.edit_text(list_text)


async def delete_enemy_reply_controller(client, message):
    """Deletes replies from the enemy list (command is now symbolic)."""
    await message.edit_text("ℹ️ متن‌های دشمن به صورت خودکار جایگزین شده‌اند و قابل حذف یا ویرایش نیستند.")


async def set_enemy_reply_controller(client, message):
    """Sets replies for the enemy list (command is now symbolic)."""
    await message.edit_text("ℹ️ متن‌های دشمن به صورت خودکار جایگزین شده‌اند و قابل حذف یا ویرایش نیستند.")


async def set_friend_controller(client, message):
    """Adds a user to the friend list via reply."""
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        
        # Prevent adding self
        if target_id == user_id:
            await message.edit_text("⚠️ شما نمی‌توانید خودتان را به لیست دوست اضافه کنید.")
            return
            
        friends = FRIEND_LIST.setdefault(user_id, set())
        if target_id not in friends:
            friends.add(target_id)
            await message.edit_text(f"✅ کاربر با آیدی `{target_id}` به لیست دوست اضافه شد.")
        else:
            await message.edit_text(f"ℹ️ کاربر با آیدی `{target_id}` از قبل در لیست دوست بود.")
    else:
        await message.edit_text("⚠️ برای افزودن به لیست دوست، روی پیام کاربر مورد نظر ریپلای کنید.")


async def delete_friend_controller(client, message):
    """Removes a user from the friend list via reply."""
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        friends = FRIEND_LIST.get(user_id) # No setdefault needed here
        if friends and target_id in friends:
            friends.remove(target_id)
            await message.edit_text(f"✅ کاربر با آیدی `{target_id}` از لیست دوست حذف شد.")
        else:
            await message.edit_text(f"ℹ️ کاربر با آیدی `{target_id}` در لیست دوست یافت نشد.")
    else:
        await message.edit_text("⚠️ برای حذف از لیست دوست، روی پیام کاربر مورد نظر ریپلای کنید.")


async def clear_friend_list_controller(client, message):
    """Clears all users from the friend list."""
    user_id = client.me.id
    if FRIEND_LIST.get(user_id): # Check if the list exists and is not empty
        FRIEND_LIST[user_id] = set()
        await message.edit_text("✅ لیست دوست با موفقیت پاکسازی شد.")
    else:
        await message.edit_text("ℹ️ لیست دوست از قبل خالی بود.")


async def list_friends_controller(client, message):
    """Lists all users in the friend list."""
    user_id = client.me.id
    friends = FRIEND_LIST.get(user_id, set())
    if not friends:
        await message.edit_text("ℹ️ لیست دوست خالی است.")
        return

    list_items = []
    # Fetch user info in chunks for efficiency
    friend_ids = list(friends)
    chunk_size = 100
    for i in range(0, len(friend_ids), chunk_size):
        chunk = friend_ids[i:i+chunk_size]
        try:
            users = await client.get_users(chunk)
            for user in users:
                display_name = f"{user.first_name}" + (f" {user.last_name}" if user.last_name else "")
                list_items.append(f"- {display_name} (`{user.id}`)")
        except Exception as e:
            logging.warning(f"List Friends: Could not fetch info for chunk: {e}")
            # Add remaining as IDs
            for user_id_in_chunk in chunk:
                 if not any(f"`{user_id_in_chunk}`" in item for item in list_items):
                     list_items.append(f"- User ID: `{user_id_in_chunk}` (اطلاعات قابل دریافت نیست)")

    list_text = "**🫂 لیست دوستان:**\n" + "\n".join(list_items)
    if len(list_text) > 4096:
        list_text = list_text[:4090] + "\n[...]"
    await message.edit_text(list_text)


async def list_friend_replies_controller(client, message):
    """Lists all custom replies for the friend list."""
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
    """Deletes a reply from the friend list by 1-based index or all."""
    user_id = client.me.id
    match = re.match(r"^(حذف متن دوست|delnotef)(?: (\d+))?$", message.text, re.IGNORECASE)
    if match:
        index_str = match.group(2)
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
    """Adds a new reply to the friend list."""
    user_id = client.me.id
    match = re.match(r"^(تنظیم متن دوست|addnotef) (.*)", message.text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(2).strip()
        if text:
            if user_id not in FRIEND_REPLIES:
                FRIEND_REPLIES[user_id] = []
            FRIEND_REPLIES[user_id].append(text)
            await message.edit_text(f"✅ متن جدید به لیست پاسخ دوست اضافه شد (مورد {len(FRIEND_REPLIES[user_id])}).")
        else:
            await message.edit_text("⚠️ متن پاسخ نمی‌تواند خالی باشد.")
async def block_unblock_controller(client, message):
    """Blocks or unblocks a user based on reply."""
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
    """Mutes or unmutes a user in the current chat."""
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
            chat_info = f"در چت \"{chat.title}\" (`{chat_id}`)" if chat.title else f"در چت `{chat_id}`"
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
    """Sets or removes auto-reaction for a specific user."""
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
            else:
                await message.edit_text(f"ℹ️ واکنشی برای {target_info} تنظیم نشده بود.")
        else:
            match = re.match(r"^ریاکشن (.*)", command)
            if match:
                emoji = match.group(1).strip()
                if emoji:
                    # Send a test reaction to see if it's valid BEFORE saving
                    try:
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
                await message.edit_text("⚠️ فرمت دستور نامعتبر. مثال: `ریاکشن 👍`")

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
    """Saves the replied message to Saved Messages."""
    user_id = client.me.id
    if message.reply_to_message:
        try:
            await message.reply_to_message.forward("me")
            await message.edit_text("✅ پیام با موفقیت در Saved Messages شما ذخیره شد.")
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try:
                await message.edit_text(f"⏳ Flood wait ({e.value}s).")
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
    """Repeats the replied message 'count' times with optional 'interval'."""
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
            if count > 100: # Limit
                 await message.edit_text("⚠️ حداکثر تعداد تکرار مجاز 100 بار است.")
                 return
            if count * interval > 600: # 10 min limit
                 await message.edit_text("⚠️ مجموع زمان اجرای دستور تکرار بیش از حد طولانی است (حداکثر ۱۰ دقیقه).")
                 return

            replied_msg = message.reply_to_message
            chat_id = message.chat.id
            await message.delete() # Delete the command message

            sent_count = 0
            for i in range(count):
                try:
                    await replied_msg.copy(chat_id)
                    sent_count += 1
                    if interval > 0 and i < count - 1:
                        await asyncio.sleep(interval)
                except FloodWait as e_flood:
                    logging.warning(f"Repeat Msg: Flood wait after sending {sent_count}/{count} for user {user_id}. Sleeping {e_flood.value}s.")
                    await asyncio.sleep(e_flood.value + 2)
                except Exception as e_copy:
                    logging.error(f"Repeat Msg: Error copying message on iteration {i+1} for user {user_id}: {e_copy}")
                    try:
                         await client.send_message(chat_id, f"⚠️ خطایی در تکرار پیام رخ داد (تکرار {i+1}/{count}). متوقف شد.")
                    except Exception: pass
                    break # Stop repeating on error
            
            # Send completion message
            if sent_count > 5: # Only send confirmation for larger repeats
                try:
                    msg = await client.send_message(chat_id, f"✅ تکرار {sent_count} پیام کامل شد.")
                    await asyncio.sleep(5)
                    await msg.delete()
                except Exception: pass

        except ValueError:
            await message.edit_text("⚠️ فرمت تعداد یا زمان نامعتبر است.")
        except MessageIdInvalid:
             logging.warning(f"Repeat Msg: Command message {message.id} already deleted.")
        except Exception as e:
            logging.error(f"Repeat Msg Controller: General error for user {user_id}: {e}", exc_info=True)
    else:
        try:
             await message.edit_text("⚠️ فرمت دستور نامعتبر. مثال: `تکرار 5` یا `تکرار 3 10`")
        except Exception: pass

async def delete_messages_controller(client, message):
    """Deletes 'count' of user's own messages, or 'all'."""
    user_id = client.me.id
    command = message.text.strip()
    
    count = 0
    if command == "حذف همه":
        count = 1000  # Set a high number for 'all'
    else:
        match = re.match(r"^حذف(?: (\d+))?$", command)
        if match:
            count_str = match.group(1)
            count = int(count_str) if count_str else 5 # Default 5
        else:
            await message.edit_text("⚠️ فرمت دستور نامعتبر. مثال: `حذف`، `حذف 10` یا `حذف همه`")
            return

    if count < 1:
        await message.edit_text("⚠️ تعداد باید حداقل 1 باشد.")
        return
    if count > 1000:
        count = 1000 # Max limit

    chat_id = message.chat.id
    message_ids_to_delete = []
    
    try:
        # Add the command message itself to the delete list
        message_ids_to_delete.append(message.id)
        
        user_messages_found = 0
        limit = count * 5 # Search more messages to find the count
        if limit < 100: limit = 100
        
        async for msg in client.get_chat_history(chat_id, limit=limit):
            if msg.id == message.id:
                continue
                
            if msg.from_user and msg.from_user.id == user_id:
                message_ids_to_delete.append(msg.id)
                user_messages_found += 1
                
                if user_messages_found >= count:
                    break # Found enough messages
        
        if len(message_ids_to_delete) > 0:
            deleted_count_total = 0
            for i in range(0, len(message_ids_to_delete), 100): # Delete in batches of 100
                batch = message_ids_to_delete[i:i+100]
                try:
                    await client.delete_messages(chat_id, batch)
                    deleted_count_total += len(batch)
                    await asyncio.sleep(1) # Delay between batches
                except FloodWait as e:
                    logging.warning(f"Delete Messages: Flood wait, sleeping {e.value}s")
                    await asyncio.sleep(e.value + 1)
                except MessageIdInvalid:
                    logging.warning("Delete Messages: Some messages already deleted.")
                    pass 
            
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
    """Handles 'تاس' and 'بولینگ' commands."""
    user_id = client.me.id
    command = message.text.strip().lower()
    chat_id = message.chat.id

    try:
        if command == "تاس":
            target_value = 6
            max_attempts = 20
            attempts = 0
            await message.delete()
            
            while attempts < max_attempts:
                result = await client.send_dice(chat_id, emoji="🎲")
                attempts += 1
                if hasattr(result, 'dice') and result.dice.value == target_value:
                    break
                await asyncio.sleep(1.5)
            
        elif command.startswith("تاس "):
            match = re.match(r"^تاس (\d+)$", command)
            if match:
                try:
                    target_value = int(match.group(1))
                    if 1 <= target_value <= 6:
                        max_attempts = 20
                        attempts = 0
                        await message.delete()
                        
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
            target_value = 6 # Strike value for 🎳
            max_attempts = 10
            attempts = 0
            await message.delete()
            
            while attempts < max_attempts:
                result = await client.send_dice(chat_id, emoji="🎳")
                attempts += 1
                if hasattr(result, 'dice') and result.dice.value == target_value:
                    break
                await asyncio.sleep(2)
                
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
    """Handles 'فونت', 'فونت [عدد]', and date font commands."""
    user_id = client.me.id
    command = message.text.strip()
    try:
        if command == "فونت":
            font_list_parts = []
            current_part = "📜 **لیست فونت‌های موجود برای ساعت:**\n"
            for i, key in enumerate(FONT_KEYS_ORDER):
                 line = f"{i+1}. {FONT_DISPLAY_NAMES.get(key, key)}: {stylize_time('12:34', key)}\n"
                 if len(current_part) + len(line) > 4090: # Leave margin
                     font_list_parts.append(current_part)
                     current_part = line
                 else:
                     current_part += line
            font_list_parts.append(current_part) # Add the last part

            for i, part in enumerate(font_list_parts):
                 text_to_send = part
                 if i == len(font_list_parts) - 1: # Add usage instruction
                     text_to_send += "\nبرای انتخاب فونت: `فونت [عدد]`"
                 if i == 0:
                     await message.edit_text(text_to_send)
                 else:
                     await client.send_message(message.chat.id, text_to_send)
                     await asyncio.sleep(0.5)

        elif command == "فونت تاریخ 1":
            TIME_DATE_FORMAT[user_id] = 'gregorian'
            await message.edit_text("✅ فرمت تاریخ بیو به **میلادی** (کوچک) تغییر یافت.")
            asyncio.create_task(update_profile_bio(client, user_id))

        elif command == "فونت تاریخ 2":
            TIME_DATE_FORMAT[user_id] = 'jalali'
            await message.edit_text("✅ فرمت تاریخ بیو به **شمسی (جلالی)** (کوچک) تغییر یافت.")
            asyncio.create_task(update_profile_bio(client, user_id))

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
                                    base_name_match = re.match(r"^(.*?)\s*[" + re.escape(ALL_CLOCK_CHARS) + r":\s]*$", current_name)
                                    base_name = base_name_match.group(1).strip() if base_name_match else current_name.strip()
                                    if not base_name: base_name = me.username or f"User_{user_id}"

                                    tehran_time = datetime.now(TEHRAN_TIMEZONE)
                                    current_time_str = tehran_time.strftime("%H:%M")
                                    stylized_time = stylize_time(current_time_str, selected)
                                    new_name = f"{base_name} {stylized_time}"
                                    await client.update_profile(first_name=new_name[:64])
                                except FloodWait as e_update:
                                     logging.warning(f"Font Controller: Flood wait updating profile for user {user_id}: {e_update.value}s")
                                     await asyncio.sleep(e_update.value + 1)
                                except Exception as e_update:
                                     logging.error(f"Font Controller: Failed to update profile name immediately for user {user_id}: {e_update}")
                        else:
                            await message.edit_text(f"ℹ️ فونت **{FONT_DISPLAY_NAMES.get(selected, selected)}** از قبل انتخاب شده بود.")
                    else:
                        await message.edit_text(f"⚠️ شماره فونت نامعتبر. لطفاً عددی بین 1 تا {len(FONT_KEYS_ORDER)} وارد کنید.")
                except ValueError:
                    await message.edit_text("⚠️ شماره وارد شده نامعتبر است.")

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
    """Handles 'ساعت روشن' and 'ساعت خاموش' commands."""
    user_id = client.me.id
    command = message.text.strip()
    new_name = None
    feedback_msg = None

    try:
        me = await client.get_me()
        current_name = me.first_name or ""
        # Use more robust regex to find base name
        base_name_match = re.match(r"^(.*?)\s*[" + re.escape(ALL_CLOCK_CHARS) + r":\s]*$", current_name)
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
                new_name = f"{base_name} {stylized_time}"[:64] # Apply limit here
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

# --- NEW Controllers (from bot.txt) ---

async def text_to_voice_controller(client, message):
    """Converts text to speech using an external API."""
    user_id = client.me.id
    match = re.match(r"^ویس (.*)", message.text, re.DOTALL)
    if not match:
        await message.edit_text("⚠️ فرمت نامعتبر. مثال: `ویس سلام خوبی`")
        return
        
    text = match.group(1).strip()
    if not text:
        await message.edit_text("⚠️ متن برای تبدیل به ویس ارائه نشد.")
        return

    url = f"https://api.irateam.ir/Text-To-Speech/tts.php?text={quote(text)}&Character=DilaraNeural"
    
    try:
        await message.edit_text("⏳ در حال تبدیل متن به ویس...")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    try:
                        # The API returns the audio file directly
                        audio_content = await response.read()
                        if audio_content:
                            voice_io = BytesIO(audio_content)
                            voice_io.name = "voice.ogg"
                            await client.send_voice(message.chat.id, voice=voice_io, reply_to_message_id=message.id)
                            await message.delete() # Delete the command message
                        else:
                            raise ValueError("API returned empty response")
                    except Exception as e_json:
                        logging.error(f"Text2Voice: Error processing API response: {e_json}")
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
    """Downloads a YouTube video and sends it."""
    user_id = client.me.id
    match = re.match(r"^یوتوب (.*)", message.text, re.IGNORECASE)
    if not match:
        await message.edit_text("⚠️ فرمت نامعتبر. مثال: `یوتوب https://...`")
        return

    video_url = match.group(1).strip()
    local_path = None
    
    try:
        await message.edit_text("⏳ در حال پردازش لینک یوتیوب...")
        yt = YouTube(video_url)
        
        video_stream = yt.streams.filter(progressive=True, file_extension='mp4').get_highest_resolution()

        if not video_stream:
            await message.edit_text("⚠️ ویدیویی با فرمت mp4 (progressive) یافت نشد.")
            return

        # Sanitize filename
        downloaded_file_name = video_stream.default_filename
        normalized_file_name = unicodedata.normalize('NFKD', downloaded_file_name).encode('ascii', 'ignore').decode('ascii')
        normalized_file_name = re.sub(r'[^\w\s.-]', '', normalized_file_name).strip()
        if not normalized_file_name: normalized_file_name = f"youtube_video_{yt.video_id}.mp4"

        download_path = "downloads"
        os.makedirs(download_path, exist_ok=True)
        local_path = os.path.join(download_path, normalized_file_name)

        await message.edit_text("⏳ در حال دانلود ویدیو... (این ممکن است طول بکشد)")
        # Pytube's download is blocking, consider running in executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, video_stream.download, download_path, normalized_file_name)

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
            try: os.remove(local_path)
            except Exception: pass

async def part_text_controller(client, message):
    """Animates text character by character."""
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
        for char in text_to_part:
            current_text += char
            # Avoid editing too fast or with same text
            if char != " ":
                await message.edit_text(current_text)
                await asyncio.sleep(0.2)
        
        # Final edit to ensure text is complete
        await message.edit_text(current_text)
        
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass # Expected
    except Exception as e:
        logging.error(f"Part Text: Error for user {user_id}: {e}", exc_info=True)
        # Don't edit message on error
        
async def ping_controller(client, message):
    """Checks bot latency."""
    start_time = time.time()
    try:
        await message.edit_text("...pong")
        end_time = time.time()
        ping_time = round((end_time - start_time) * 1000, 2)
        await message.edit_text(f"🖤 **Pong!**\n`{ping_time} ms`")
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception:
        pass # Ignore errors

# --- Animation/Game Controllers (from bot.txt, made async) ---

async def square_controller(client, message):
    """Square animation."""
    try:
        frames = [
            "◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◼️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◼️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◼️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◼️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◼️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◼️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◼️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◼️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◼️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◼️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◼️◼️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◼️◼️",
"◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◼️",
            "◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️\n◻️◻️◻️◻️◻️"
        ]
        for frame in frames:
            await message.edit_text(frame)
            await asyncio.sleep(0.1)
        await message.edit_text("✅ مربع تمام شد.")
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception:
        pass # Ignore errors in animations

async def heart_controller(client, message):
    """Heart animation."""
    hearts = ["❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤎", "❤️‍🔥", "❤️‍🩹", "❣️", "💓", "💗"]
    try:
        for _ in range(2): # Loop twice
            for heart in hearts:
                await message.edit_text(heart)
                await asyncio.sleep(0.3)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception:
        pass

async def big_heart_controller(client, message):
    """Big moon heart animation."""
    heart_parts = [
        "🌑🌑🌑🌑🌑🌓🌕🌕🌕🌕🌕‌",
        "🌑🌑🌑🌑🌑🌓🌕🌕🌕🌕🌕\n🌑🌒🌕🌕🌘🌓🌖🌑🌑🌔🌕",
        "🌑🌑🌑🌑🌑🌓🌕🌕🌕🌕🌕\n🌑🌒🌕🌕🌘🌓🌖🌑🌑🌔🌕\n🌑🌔🌕🌕🌕🌓🌑🌑🌑🌒🌕",
        "🌑🌑🌑🌑🌑🌓🌕🌕🌕🌕🌕\n🌑🌒🌕🌕🌘🌓🌖🌑🌑🌔🌕\n🌑🌔🌕🌕🌕🌓🌑🌑🌑🌒🌕\n🌑🌕🌕🌕🌕🌗🌑🌑🌑🌑🌕",
        "🌑🌑🌑🌑🌑🌓🌕🌕🌕🌕🌕\n🌑🌒🌕🌕🌘🌓🌖🌑🌑🌔🌕\n🌑🌔🌕🌕🌕🌓🌑🌑🌑🌒🌕\n🌑🌕🌕🌕🌕🌗🌑🌑🌑🌑🌕\n🌑🌔🌕🌕🌕🌗🌑🌑🌑🌒🌕‌",
        "🌑🌑🌑🌑🌑🌓🌕🌕🌕🌕🌕\n🌑🌒🌕🌕🌘🌓🌖🌑🌑🌔🌕\n🌑🌔🌕🌕🌕🌓🌑🌑🌑🌒🌕\n🌑🌕🌕🌕🌕🌗🌑🌑🌑🌑🌕\n🌑🌔🌕🌕🌕🌗🌑🌑🌑🌒🌕‌\n🌑🌒🌕🌕🌕🌗🌑🌑🌑🌔🌕",
        "🌑🌑🌑🌑🌑🌓🌕🌕🌕🌕🌕\n🌑🌒🌕🌕🌘🌓🌖🌑🌑🌔🌕\n🌑🌔🌕🌕🌕🌓🌑🌑🌑🌒🌕\n🌑🌕🌕🌕🌕🌗🌑🌑🌑🌑🌕\n🌑🌔🌕🌕🌕🌗🌑🌑🌑🌒🌕‌\n🌑🌒🌕🌕🌕🌗🌑🌑🌑🌔🌕\n🌑🌑🌒🌕🌕🌗🌑🌑🌔🌕🌕",
        "🌑🌑🌑🌑🌑🌓🌕🌕🌕🌕🌕\n🌑🌒🌕🌕🌘🌓🌖🌑🌑🌔🌕\n🌑🌔🌕🌕🌕🌓🌑🌑🌑🌒🌕\n🌑🌕🌕🌕🌕🌗🌑🌑🌑🌑🌕\n🌑🌔🌕🌕🌕🌗🌑🌑🌑🌒🌕‌\n🌑🌒🌕🌕🌕🌗🌑🌑🌑🌔🌕\n🌑🌑🌒🌕🌕🌗🌑🌑🌔🌕🌕\n🌑🌑🌑🌒🌕🌗🌑🌔🌕🌕🌕",
        "🌑🌑🌑🌑🌑🌓🌕🌕🌕🌕🌕\n🌑🌒🌕🌕🌘🌓🌖🌑🌑🌔🌕\n🌑🌔🌕🌕🌕🌓🌑🌑🌑🌒🌕\n🌑🌕🌕🌕🌕🌗🌑🌑🌑🌑🌕\n🌑🌔🌕🌕🌕🌗🌑🌑🌑🌒🌕‌\n🌑🌒🌕🌕🌕🌗🌑🌑🌑🌔🌕\n🌑🌑🌒🌕🌕🌗🌑🌑🌔🌕🌕\n🌑🌑🌑🌒🌕🌗🌑🌔🌕🌕🌕\n🌑🌑🌑🌑🌒🌗🌔🌕🌕🌕🌕",
        "🌑🌑🌑🌑🌑🌓🌕🌕🌕🌕🌕\n🌑🌒🌕🌕🌘🌓🌖🌑🌑🌔🌕\n🌑🌔🌕🌕🌕🌓🌑🌑🌑🌒🌕\n🌑🌕🌕🌕🌕🌗🌑🌑🌑🌑🌕\n🌑🌔🌕🌕🌕🌗🌑🌑🌑🌒🌕‌\n🌑🌒🌕🌕🌕🌗🌑🌑🌑🌔🌕\n🌑🌑🌒🌕🌕🌗🌑🌑🌔🌕🌕\n🌑🌑🌑🌒🌕🌗🌑🌔🌕🌕🌕\n🌑🌑🌑🌑🌒🌗🌔🌕🌕🌕🌕\n🌑🌑🌑🌑🌑🌓🌕🌕🌕🌕🌕",
        "❤️"
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
    async def help_controller(client, message):
    """Sends the complete help text."""
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
• `پارت [متن]`: ارسال انیمیشنی متن مورد نظر.

**🔹 ساعت و پروفایل 🔹**
• `ساعت روشن` / `خاموش`: نمایش یا حذف ساعت از **نام** پروفایل شما.
• `بیو ساعت روشن` / `خاموش`: نمایش یا حذف ساعت از **بیو** پروفایل شما.
• `تاریخ روشن` / `خاموش`: نمایش یا حذف تاریخ از **بیو** (در کنار ساعت).
• `فونت`: نمایش لیست فونت‌های موجود برای ساعت.
• `فونت [عدد]`: انتخاب فونت جدید برای نمایش ساعت (در نام و بیو).
• `فونت تاریخ 1`: تنظیم فرمت تاریخ بیو به **میلادی** (کوچک).
• `فونت تاریخ 2`: تنظیم فرمت تاریخ بیو به **شمسی (جلالی)** (کوچک).
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
• `تکرار [عدد] [ثانیه]` (ریپلای): تکرار پیام X بار با فاصله Y ثانیه (فاصله اختیاری است).
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
• `تنظیم متن دشمن [متن]`: (غیرفعال - متن‌ها جایگزین شده‌اند).
• `لیست متن دشمن`: نمایش لیست متن‌های جایگزین شده.
• `حذف متن دشمن [عدد]`: (غیرفعال).

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
• `ربات` / `پینگ`: بررسی آنلاین بودن ربات و نمایش سرعت.
• `id`: (در گروه یا با ریپلای) نمایش شناسه چت، کاربر و پیام.
• `info`: (با ریپلای) نمایش اطلاعات کامل کاربر.
• `ویس [متن]`: تبدیل متن فارسی به ویس.
• `یوتوب [LINK]`: دانلود ویدیو از لینک یوتیوب.
• `دیکشنری [کلمه]` / `ud [term]`: جستجو در Urban Dictionary.
• `حساب [عبارت]` / `calc [exp]`: ماشین حساب.
• `کیو آر [متن]` / `qr [text]`: ساخت QR Code از متن.
• `جیسون` (ریپلای): نمایش مرتب JSON.
• `این کیه [id/user]` / `whois [id/user]`: دریافت اطلاعات کاربر.
• `لیست بلاک` / `blocklist`: نمایش کاربران بلاک شده (تا 100).
• `هواشناسی [شهر]`: نمایش اطلاعات آب و هوا.
• `تاس`: ارسال تاس شانسی (تا 6).
• `تاس [عدد ۱-۶]`: ارسال تاس تا رسیدن به عدد مورد نظر.
• `بولینگ`: ارسال بولینگ شانسی (تا استرایک).
• `مربع` | `قلب` | `قلب بزرگ` | `بکیرم` | `مکعب` | `لودینگ`

**🔹 امنیت و مدیریت 🔹**
• `afk [دلیل]` (اختیاری): فعال کردن حالت AFK.
• `afk خاموش`: غیرفعال کردن حالت AFK.
• `note [اسم] [متن]`: ذخیره یک یادداشت. (یا ریپلای `note [اسم]`)
• `note [اسم]`: فراخوانی یادداشت.
• `notes`: نمایش لیست همه یادداشت‌ها.
• `delnote [اسم]`: حذف یادداشت.
• `purge`: (با ریپلای) پاکسازی پیام‌های کاربر در چت (تا 100 پیام).
• `webshot [url]`: اسکرین‌شات از سایت.
• `پیوی قفل` / `باز`: فعال/غیرفعال کردن حذف خودکار تمام پیام‌های دریافتی در PV.
• `منشی روشن` / `خاموش`: فعال/غیرفعال کردن پاسخ خودکار در PV.
• `منشی متن [متن دلخواه]`: تنظیم متن سفارشی برای منشی.
• `منشی متن` (بدون متن): بازگرداندن متن منشی به پیش‌فرض.
• `انتی لوگین روشن` / `خاموش`: خروج خودکار نشست‌های (sessions) جدید و غیرفعال.

**🔹 ابزار گروه (نیازمند ادمین) 🔹**
• `تگ همه` / `تگ همگانی`: منشن کردن تمام اعضای گروه (با تاخیر).
• `جستجو [متن]`: جستجوی کاربر بر اساس نام/یوزرنیم در گروه.
• `پین` (ریپلای): پین کردن پیام ریپلای شده.
• `آنپین` (ریپلای): آنپین کردن پیام ریپلای شده.
• `ادمین` (ریپلای): ادمین کردن کاربر.
• `عزل` (ریپلای): عزل کردن ادمین.
• `ترک`: خروج ربات از گروه یا کانال.
"""
    try:
        await message.edit_text(help_text_formatted, disable_web_page_preview=True)
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception as e:
        logging.error(f"Help Controller: Error editing help message: {e}", exc_info=True)


async def translate_controller(client, message):
    """Translates a replied message to Persian."""
    user_id = client.me.id
    if (message.reply_to_message and
        hasattr(message.reply_to_message, 'text') and message.reply_to_message.text and
        hasattr(message.reply_to_message, 'from_user') and message.reply_to_message.from_user):
        
        # Avoid translating own messages
        if message.reply_to_message.from_user.is_self:
             try:
                 await message.edit_text("ℹ️ برای ترجمه، روی پیام کاربر دیگر ریپلای کنید.")
             except Exception: pass
             return

        text_to_translate = message.reply_to_message.text
        
        if len(text_to_translate) > 1000:
            try:
                await message.edit_text("⚠️ متن برای ترجمه بیش از حد طولانی است (حداکثر 1000 کاراکتر).")
            except Exception: pass
            return

        try:
            await message.edit_text("⏳ در حال ترجمه...")
            translated = await translate_text(text_to_translate, "fa") # Target language Persian
            
            if translated and translated != text_to_translate:
                await message.edit_text(translated)
            else:
                await message.edit_text("ℹ️ ترجمه انجام نشد یا متن اصلی و ترجمه یکسان بودند.")
                
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception as e:
            logging.error(f"Translate Controller: Error translating text for user {user_id}: {e}", exc_info=True)
            try:
                await message.edit_text("⚠️ خطایی در سرویس ترجمه رخ داد.")
            except Exception: pass
    else:
        try:
            await message.edit_text("⚠️ برای ترجمه، روی یک پیام متنی ریپلای کنید.")
        except MessageNotModified:
            pass
        except Exception as e_edit_warn:
             logging.warning(f"Translate: Failed to edit warning message: {e_edit_warn}")


# UPDATED: toggle_controller to include all new features
async def toggle_controller(client, message):
    """Handles various on/off toggle commands."""
    user_id = client.me.id
    command = message.text.strip()
    feature = ""
    new_status = False
    status_changed = False
    feedback_msg = None

    try:
        if command.endswith("روشن"):
            feature = command[:-5].strip()
            new_status = True
        elif command.endswith("خاموش"):
            feature = command[:-6].strip()
            new_status = False
        
        # Find the corresponding status dict
        status_map = {
            "بولد": BOLD_MODE_STATUS,
            "سین": AUTO_SEEN_STATUS,
            "منشی": SECRETARY_MODE_STATUS,
            "انتی لوگین": ANTI_LOGIN_STATUS,
            "تایپ": TYPING_MODE_STATUS,
            "بازی": PLAYING_MODE_STATUS,
            "ضبط ویس": RECORD_VOICE_STATUS,
            "عکس": UPLOAD_PHOTO_STATUS,
            "گیف": WATCH_GIF_STATUS,
            "دشمن": ENEMY_ACTIVE,
            "دوست": FRIEND_ACTIVE,
            "بیو ساعت": TIME_BIO_STATUS,
            "ایتالیک": ITALIC_MODE_STATUS,
            "زیرخط": UNDERLINE_MODE_STATUS,
            "لینک": LINK_MODE_STATUS,
            "ضبط ویدیو": RECORD_VIDEO_STATUS,
            "استیکر": CHOOSE_STICKER_STATUS,
            "آپلود ویدیو": UPLOAD_VIDEO_STATUS,
            "آپلود فایل": UPLOAD_DOCUMENT_STATUS,
            "آپلود صدا": UPLOAD_AUDIO_STATUS,
            "صحبت": SPEAKING_STATUS,
            "تاریخ": TIME_DATE_STATUS, # <--- NEW
        }

        if feature in status_map:
            status_dict = status_map[feature]
            current_status = status_dict.get(user_id, False)
            
            if current_status != new_status:
                status_dict[user_id] = new_status
                status_changed = True
                
                # Special actions on toggle
                if feature == "منشی" and not new_status:
                    USERS_REPLIED_IN_SECRETARY[user_id] = set() # Clear replied list when turning off
                
                # Handle mutual exclusivity for typing/playing/etc.
                if new_status and feature in ["تایپ", "بازی", "ضبط ویس", "عکس", "گیف", "ضبط ویدیو", "استیکر", "آپلود ویدیو", "آپلود فایل", "آپلود صدا", "صحبت"]:
                    for f_name, s_dict in status_map.items():
                        if f_name != feature and f_name in ["تایپ", "بازی", "ضبط ویس", "عکس", "گیف", "ضبط ویدیو", "استیکر", "آپلود ویدیو", "آپلود فایل", "آپلود صدا", "صحبت"]:
                            s_dict[user_id] = False # Turn off other actions
                
                status_text = "فعال" if new_status else "غیرفعال"
                feedback_msg = f"✅ **{feature} {status_text} شد.**"
            else:
                status_text = "فعال" if new_status else "غیرفعال"
                feedback_msg = f"ℹ️ {feature} از قبل {status_text} بود."
        else:
            feedback_msg = "⚠️ دستور نامشخص." # Should not happen if regex matches

        if feedback_msg:
            await message.edit_text(feedback_msg)
            
        # Trigger immediate bio update if bio clock/date changed
        if feature in ["بیو ساعت", "تاریخ"]:
            asyncio.create_task(update_profile_bio(client, user_id))

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
    """Handles language setting for auto-translate."""
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
            # Match "ترجمه [code]"
            match = re.match(r"ترجمه ([a-z]{2}(?:-[a-z]{2})?)", command)
            if match:
                lang = match.group(1)
                if current_lang != lang:
                    AUTO_TRANSLATE_TARGET[user_id] = lang
                    feedback_msg = f"✅ ترجمه خودکار به زبان {lang} فعال شد."
                else:
                    feedback_msg = f"ℹ️ ترجمه خودکار به زبان {lang} از قبل فعال بود."
            else:
                 feedback_msg = "⚠️ فرمت دستور نامعتبر. مثال: `ترجمه en`"

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
    """Sets or resets the secretary auto-reply message."""
    user_id = client.me.id
    match = re.match(r"^منشی متن(?: |$)(.*)", message.text, re.DOTALL | re.IGNORECASE) # Added ignorecase
    text = match.group(1).strip() if match else None # Use None to distinguish no match from empty text

    try:
        if text is not None: # Command was matched
            if text: # User provided custom text
                if CUSTOM_SECRETARY_MESSAGES.get(user_id) != text:
                    CUSTOM_SECRETARY_MESSAGES[user_id] = text
                    await message.edit_text(f"✅ متن سفارشی منشی تنظیم شد:\n\n{text[:100]}...") # Show preview
                else:
                    await message.edit_text("ℹ️ متن سفارشی منشی بدون تغییر باقی ماند (متن جدید مشابه قبلی است).")
            else: # User sent "منشی متن" without text to reset
                if user_id in CUSTOM_SECRETARY_MESSAGES:
                    CUSTOM_SECRETARY_MESSAGES.pop(user_id) # Remove custom text to use default
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
    """Toggles PV lock mode."""
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
    """Copies target user's profile info or restores original."""
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
                try:
                    photo_bytes_io = BytesIO(original_photo_data)
                    photo_bytes_io.name = "original_profile.jpg" # Give it a name
                    await client.set_profile_photo(photo=photo_bytes_io)
                except Exception as e_set_photo:
                     logging.warning(f"Copy Profile (Revert): Could not set original photo for user {user_id}: {e_set_photo}")

            COPY_MODE_STATUS[user_id] = False # Set status after successful operations
            await message.edit_text("✅ پروفایل با موفقیت به حالت اصلی بازگردانده شد.")
            
            # Trigger immediate bio/clock update after reverting
            # This task runs in the background, we don't need to await it
            asyncio.create_task(update_profile_bio(client, user_id))
            asyncio.create_task(update_profile_clock(client, user_id))
            return

        # Logic for "کپی روشن"
        elif command == "کپی روشن":
            target_user = message.reply_to_message.from_user
            target_id = target_user.id
            
            # --- Backup Current Profile ---
            await message.edit_text("⏳ در حال ذخیره پروفایل فعلی...")
            me = await client.get_me()
            me_photo_bytes = None
            me_bio = ""
            try:
                me_full = await client.get_chat("me") # get_chat is often more reliable for bio
                me_bio = me_full.bio or ''
            except Exception as e_get_bio:
                 logging.warning(f"Copy Profile (Backup): Could not get own bio for user {user_id}: {e_get_bio}")

            if me.photo:
                try:
                    me_photo_stream = await client.download_media(me.photo.big_file_id, in_memory=True)
                    if isinstance(me_photo_stream, BytesIO):
                         me_photo_bytes = me_photo_stream.getvalue()
                except Exception as e_download_me:
                     logging.warning(f"Copy Profile (Backup): Could not download own photo for user {user_id}: {e_download_me}")

            ORIGINAL_PROFILE_DATA[user_id] = {
                'first_name': me.first_name or '',
                'last_name': me.last_name or '',
                'bio': me_bio,
                'photo': me_photo_bytes # Store bytes or None
            }

            # --- Get Target Profile Info ---
            await message.edit_text("⏳ در حال دریافت اطلاعات پروفایل هدف...")
            target_photo_bytes_io = None # We need BytesIO for set_profile_photo
            target_bio = ""
            try:
                 target_chat = await client.get_chat(target_id) # get_chat for bio
                 target_bio = target_chat.bio or ''
            except Exception as e_get_target_bio:
                 logging.warning(f"Copy Profile (Target): Could not get target bio for user {target_id}: {e_get_target_bio}")

            if target_user.photo:
                try:
                    target_photo_stream = await client.download_media(target_user.photo.big_file_id, in_memory=True)
                    if isinstance(target_photo_stream, BytesIO):
                        target_photo_bytes_io = target_photo_stream
                        target_photo_bytes_io.name = "target_profile.jpg" # Give it a name
                except Exception as e_download_target:
                    logging.warning(f"Copy Profile (Target): Could not download target photo for user {target_id}: {e_download_target}")

            # --- Apply Target Profile ---
            await message.edit_text("⏳ در حال اعمال پروفایل هدف...")
            
            # Delete existing photos first
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
                     
            # Update name and bio *after* photo operations
            await client.update_profile(
                first_name=(target_user.first_name or '')[:64], # Apply limits
                last_name=(target_user.last_name or '')[:64],
                bio=target_bio[:70]
            )

            COPY_MODE_STATUS[user_id] = True
            await message.edit_text("✅ پروفایل کاربر کپی شد (نام، نام خانوادگی، بیو، عکس).")

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except MessageNotModified:
        pass
    except Exception as e:
        logging.error(f"Copy Profile Controller: Error for user {user_id} processing command '{command}': {e}", exc_info=True)
        try:
            error_text = f"⚠️ خطایی در عملیات کپی پروفایل رخ داد: {type(e).__name__}"
            await message.edit_text(error_text)
        except Exception:
            pass


# NEW: Controller for SetName (from bot.txt)
async def set_name_controller(client, message):
    """Sets profile name based on replied text."""
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.text:
        try:
            new_name = message.reply_to_message.text[:64] # Apply 64 char limit
            await client.update_profile(first_name=new_name)
            await message.edit_text(f"✅ نام با موفقیت به `{new_name}` تغییر یافت.")
            
            # Trigger clock update immediately
            asyncio.create_task(update_profile_clock(client, user_id))
            
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception as e:
            logging.error(f"SetName Controller: Error for user {user_id}: {e}", exc_info=True)
            await message.edit_text(f"⚠️ خطایی در تنظیم نام رخ داد: {type(e).__name__}")
    else:
        await message.edit_text("⚠️ برای تنظیم نام، روی یک پیام متنی ریپلای کنید.")


# NEW: Controller for SetBio (from bot.txt)
async def set_bio_controller(client, message):
    """Sets profile bio based on replied text."""
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.text:
        try:
            new_bio = message.reply_to_message.text[:70] # Apply 70 char limit
            await client.update_profile(bio=new_bio)
            await message.edit_text(f"✅ بیو با موفقیت به `{new_bio}` تغییر یافت.")
            
            # Disable auto bio features if bio is set manually
            if TIME_BIO_STATUS.get(user_id, False) or TIME_DATE_STATUS.get(user_id, False):
                TIME_BIO_STATUS[user_id] = False
                TIME_DATE_STATUS[user_id] = False
                await message.reply_text("ℹ️ `بیو ساعت` و `تاریخ` خودکار غیرفعال شدند.")
                
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
        except Exception as e:
            logging.error(f"SetBio Controller: Error for user {user_id}: {e}", exc_info=True)
            await message.edit_text(f"⚠️ خطایی در تنظیم بیو رخ داد: {type(e).__name__}")
    else:
        await message.edit_text("⚠️ برای تنظیم بیو، روی یک پیام متنی ریپلای کنید.")


# NEW: Controller for SetProfile (from bot.txt)
async def set_profile_controller(client, message):
    """Sets profile photo/video based on replied media."""
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
            try: os.remove(local_path)
            except Exception: pass


async def set_enemy_controller(client, message):
    """Adds a user to the enemy list via reply."""
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        
        # Prevent adding self
        if target_id == user_id:
            await message.edit_text("⚠️ شما نمی‌توانید خودتان را به لیست دشمن اضافه کنید.")
            return
            
        enemies = ENEMY_LIST.setdefault(user_id, set())
        if target_id not in enemies:
             enemies.add(target_id)
             await message.edit_text(f"✅ کاربر با آیدی `{target_id}` به لیست دشمن اضافه شد.")
        else:
            await message.edit_text(f"ℹ️ کاربر با آیدی `{target_id}` از قبل در لیست دشمن بود.")
    else:
        await message.edit_text("⚠️ برای افزودن به لیست دشمن، روی پیام کاربر مورد نظر ریپلای کنید.")


async def delete_enemy_controller(client, message):
    """Removes a user from the enemy list via reply."""
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        enemies = ENEMY_LIST.get(user_id) # No setdefault needed here
        if enemies and target_id in enemies:
            enemies.remove(target_id)
            await message.edit_text(f"✅ کاربر با آیدی `{target_id}` از لیست دشمن حذف شد.")
        else:
            await message.edit_text(f"ℹ️ کاربر با آیدی `{target_id}` در لیست دشمن یافت نشد.")
    else:
        await message.edit_text("⚠️ برای حذف از لیست دشمن، روی پیام کاربر مورد نظر ریپلای کنید.")


async def clear_enemy_list_controller(client, message):
    """Clears all users from the enemy list."""
    user_id = client.me.id
    if ENEMY_LIST.get(user_id): # Check if the list exists and is not empty
        ENEMY_LIST[user_id] = set()
        await message.edit_text("✅ لیست دشمن با موفقیت پاکسازی شد.")
    else:
        await message.edit_text("ℹ️ لیست دشمن از قبل خالی بود.")


async def list_enemies_controller(client, message):
    """Lists all users in the enemy list."""
    user_id = client.me.id
    enemies = ENEMY_LIST.get(user_id, set())
    if not enemies:
        await message.edit_text("ℹ️ لیست دشمن خالی است.")
        return

    list_items = []
    # Fetch user info in chunks for efficiency
    enemy_ids = list(enemies)
    chunk_size = 100
    for i in range(0, len(enemy_ids), chunk_size):
        chunk = enemy_ids[i:i+chunk_size]
        try:
            users = await client.get_users(chunk)
            for user in users:
                display_name = f"{user.first_name}" + (f" {user.last_name}" if user.last_name else "")
                list_items.append(f"- {display_name} (`{user.id}`)")
        except Exception as e:
            logging.warning(f"List Enemies: Could not fetch info for chunk: {e}")
            # Add remaining as IDs
            for user_id_in_chunk in chunk:
                 # Avoid adding if already added
                 if not any(f"`{user_id_in_chunk}`" in item for item in list_items):
                     list_items.append(f"- User ID: `{user_id_in_chunk}` (اطلاعات قابل دریافت نیست)")

    list_text = "**📋 لیست دشمنان:**\n" + "\n".join(list_items)
    # Handle potential message too long error
    if len(list_text) > 4096:
        list_text = list_text[:4090] + "\n[...]" # Truncate if too long
    await message.edit_text(list_text)


async def list_enemy_replies_controller(client, message):
    """Lists all custom replies for the enemy list."""
    user_id = client.me.id
    # Use the replacement texts
    replies = REPLACEMENT_TEXTS
    list_text = "**📋 لیست متن‌های دشمن (جایگزین شده):**\n" + "\n".join([f"{i+1}. `{reply}`" for i, reply in enumerate(replies)])
    if len(list_text) > 4096:
        list_text = list_text[:4090] + "\n[...]"
    await message.edit_text(list_text)


async def delete_enemy_reply_controller(client, message):
    """Deletes replies from the enemy list (command is now symbolic)."""
    await message.edit_text("ℹ️ متن‌های دشمن به صورت خودکار جایگزین شده‌اند و قابل حذف یا ویرایش نیستند.")


async def set_enemy_reply_controller(client, message):
    """Sets replies for the enemy list (command is now symbolic)."""
    await message.edit_text("ℹ️ متن‌های دشمن به صورت خودکار جایگزین شده‌اند و قابل حذف یا ویرایش نیستند.")


async def set_friend_controller(client, message):
    """Adds a user to the friend list via reply."""
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        
        # Prevent adding self
        if target_id == user_id:
            await message.edit_text("⚠️ شما نمی‌توانید خودتان را به لیست دوست اضافه کنید.")
            return
            
        friends = FRIEND_LIST.setdefault(user_id, set())
        if target_id not in friends:
            friends.add(target_id)
            await message.edit_text(f"✅ کاربر با آیدی `{target_id}` به لیست دوست اضافه شد.")
        else:
            await message.edit_text(f"ℹ️ کاربر با آیدی `{target_id}` از قبل در لیست دوست بود.")
    else:
        await message.edit_text("⚠️ برای افزودن به لیست دوست، روی پیام کاربر مورد نظر ریپلای کنید.")


async def delete_friend_controller(client, message):
    """Removes a user from the friend list via reply."""
    user_id = client.me.id
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        friends = FRIEND_LIST.get(user_id) # No setdefault needed here
        if friends and target_id in friends:
            friends.remove(target_id)
            await message.edit_text(f"✅ کاربر با آیدی `{target_id}` از لیست دوست حذف شد.")
        else:
            await message.edit_text(f"ℹ️ کاربر با آیدی `{target_id}` در لیست دوست یافت نشد.")
    else:
        await message.edit_text("⚠️ برای حذف از لیست دوست، روی پیام کاربر مورد نظر ریپلای کنید.")


async def clear_friend_list_controller(client, message):
    """Clears all users from the friend list."""
    user_id = client.me.id
    if FRIEND_LIST.get(user_id): # Check if the list exists and is not empty
        FRIEND_LIST[user_id] = set()
        await message.edit_text("✅ لیست دوست با موفقیت پاکسازی شد.")
    else:
        await message.edit_text("ℹ️ لیست دوست از قبل خالی بود.")


async def list_friends_controller(client, message):
    """Lists all users in the friend list."""
    user_id = client.me.id
    friends = FRIEND_LIST.get(user_id, set())
    if not friends:
        await message.edit_text("ℹ️ لیست دوست خالی است.")
        return

    list_items = []
    # Fetch user info in chunks for efficiency
    friend_ids = list(friends)
    chunk_size = 100
    for i in range(0, len(friend_ids), chunk_size):
        chunk = friend_ids[i:i+chunk_size]
        try:
            users = await client.get_users(chunk)
            for user in users:
                display_name = f"{user.first_name}" + (f" {user.last_name}" if user.last_name else "")
                list_items.append(f"- {display_name} (`{user.id}`)")
        except Exception as e:
            logging.warning(f"List Friends: Could not fetch info for chunk: {e}")
            # Add remaining as IDs
            for user_id_in_chunk in chunk:
                 if not any(f"`{user_id_in_chunk}`" in item for item in list_items):
                     list_items.append(f"- User ID: `{user_id_in_chunk}` (اطلاعات قابل دریافت نیست)")

    list_text = "**🫂 لیست دوستان:**\n" + "\n".join(list_items)
    if len(list_text) > 4096:
        list_text = list_text[:4090] + "\n[...]"
    await message.edit_text(list_text)


async def list_friend_replies_controller(client, message):
    """Lists all custom replies for the friend list."""
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
    """Deletes a reply from the friend list by 1-based index or all."""
    user_id = client.me.id
    match = re.match(r"^(حذف متن دوست|delnotef)(?: (\d+))?$", message.text, re.IGNORECASE)
    if match:
        index_str = match.group(2)
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
    """Adds a new reply to the friend list."""
    user_id = client.me.id
    match = re.match(r"^(تنظیم متن دوست|addnotef) (.*)", message.text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(2).strip()
        if text:
            if user_id not in FRIEND_REPLIES:
                FRIEND_REPLIES[user_id] = []
            FRIEND_REPLIES[user_id].append(text)
            await message.edit_text(f"✅ متن جدید به لیست پاسخ دوست اضافه شد (مورد {len(FRIEND_REPLIES[user_id])}).")
        else:
            await message.edit_text("⚠️ متن پاسخ نمی‌تواند خالی باشد.")
        async def bakiram_controller(client, message):
    """'Boh' animation."""
    bk_parts = [
        "\n😂😂😂          😂         😂\n😂         😂      😂       😂\n😂           😂    😂     😂\n😂        😂       😂   😂\n😂😂😂          😂😂\n😂         😂      😂   😂\n😂           😂    😂      😂\n😂           😂    😂        😂\n😂        😂       😂          😂\n😂😂😂          😂            😂\n",
        "\n🤤🤤🤤          🤤         🤤\n🤤         🤤      🤤       🤤\n🤤           🤤    🤤     🤤\n🤤        🤤       🤤   🤤\n🤤🤤🤤          🤤🤤\n🤤         🤤      🤤   😂\n🤤           🤤    🤤      🤤\n🤤           🤤    🤤        🤤\n🤤        🤤       🤤          🤤\n🤤🤤🤤          🤤            🤤\n",
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
    """Cube animation."""
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
    """Loading animation."""
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

# --- NEW Utility Controllers ---

async def id_controller(client, message):
    """Gets ID information for chat, user, and replied message."""
    user_id = client.me.id
    chat_id = message.chat.id
    text = f"**Chat ID:** `{chat_id}`\n"
    
    target_user = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user
        text += f"**User ID (Replied):** `{target_user.id}`\n"
        text += f"**Message ID (Replied):** `{message.reply_to_message.id}`\n"
    else:
        target_user = message.from_user
        text += f"**User ID (Sender):** `{target_user.id}`\n"
        
    try:
        await message.edit_text(text)
    except Exception:
        pass # Ignore errors

async def info_controller(client, message):
    """Gets detailed information about the replied user."""
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.edit_text("⚠️ برای دریافت اطلاعات، روی پیام کاربر ریپلای کنید.")
        return

    try:
        await message.edit_text("⏳ در حال دریافت اطلاعات...")
        target_user = message.reply_to_message.from_user
        user_id = target_user.id
        
        # Get full user details
        try:
            full_user = await client.get_users(user_id)
        except Exception as e:
            await message.edit_text(f"⚠️ **خطا در دریافت اطلاعات کاربر:**\n`{e}`")
            return

        # Get bio and photo count
        bio = "N/A"
        photo_count = 0
        try:
            chat = await client.get_chat(user_id)
            bio = chat.bio or "N/A"
            photo_count = await client.get_chat_photos_count(user_id)
        except Exception:
            pass # Ignore if bio/photos are inaccessible

        info_text = f"**اطلاعات کاربر:**\n\n"
        info_text += f"**ID:** `{full_user.id}`\n"
        info_text += f"**First Name:** `{full_user.first_name or 'N/A'}`\n"
        info_text += f"**Last Name:** `{full_user.last_name or 'N/A'}`\n"
        info_text += f"**Username:** @{full_user.username or 'N/A'}\n"
        info_text += f"**Is Bot:** {'✅' if full_user.is_bot else '❌'}\n"
        info_text += f"**Is Contact:** {'✅' if full_user.is_contact else '❌'}\n"
        info_text += f"**Status:** `{full_user.status or 'N/A'}`\n"
        info_text += f"**Language Code:** `{full_user.language_code or 'N/A'}`\n"
        info_text += f"**Profile Photos:** `{photo_count}`\n"
        info_text += f"**Bio:** \n`{bio}`\n"

        await message.edit_text(info_text, disable_web_page_preview=True)

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"Info Controller: Error: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در دریافت اطلاعات رخ داد: {type(e).__name__}")

async def afk_controller(client, message):
    """Handles AFK on and off commands."""
    user_id = client.me.id
    text = message.text.strip()
    
    try:
        if text.lower() == "afk خاموش":
            if AFK_STATUS.pop(user_id, None):
                await message.edit_text("**✅ شما از حالت `AFK` خارج شدید.**")
            else:
                await message.edit_text("ℹ️ شما در حالت `AFK` نبودید.")
        else:
            reason = re.sub(r"^(afk|AFK) ?", "", text).strip()
            since = datetime.now(TEHRAN_TIMEZONE).strftime("%Y-%m-%d %H:%M")
            AFK_STATUS[user_id] = {"reason": reason, "since": since}
            
            reply_text = f"**✅ شما در حالت `AFK` قرار گرفتید.**"
            if reason:
                reply_text += f"\n**دلیل:** {reason}"
            await message.edit_text(reply_text)
            
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"AFK Controller: Error: {e}", exc_info=True)
        await message.edit_text("⚠️ خطایی در تنظیم `AFK` رخ داد.")

async def webshot_controller(client, message):
    """Takes a screenshot of a website."""
    match = re.match(r"^webshot (.+)", message.text, re.IGNORECASE)
    if not match:
        await message.edit_text("⚠️ فرمت نامعتبر. مثال: `webshot https://google.com`")
        return
        
    url = match.group(1).strip()
    if not url.startswith("http"):
        url = f"http://{url}"

    try:
        await message.edit_text("⏳ در حال گرفتن اسکرین‌شات...")
        # Use an external API for screenshot
        api_url = f"https://api.irateam.ir/WebShot/?url={quote(url)}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        if data.get("success") and data.get("results"):
                            image_url = data["results"]
                            # Download the image from the URL
                            async with session.get(image_url) as img_response:
                                if img_response.status == 200:
                                    image_bytes = await img_response.read()
                                    photo_io = BytesIO(image_bytes)
                                    photo_io.name = "webshot.png"
                                    await client.send_photo(message.chat.id, photo=photo_io, caption=f"**Webshot for:**\n`{url}`", reply_to_message_id=message.id)
                                    await message.delete()
                                else:
                                    raise ValueError(f"Failed to download image from API (Status: {img_response.status})")
                        else:
                            raise ValueError(f"API Error: {data.get('message', 'Unknown error')}")
                    except Exception as e_api:
                        logging.error(f"Webshot: Error processing API response: {e_api}")
                        await message.edit_text(f"⚠️ خطایی در پردازش پاسخ API رخ داد: {e_api}")
                else:
                    await message.edit_text(f"⚠️ سرویس اسکرین‌شات در دسترس نیست (Status: {response.status}).")

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"Webshot Controller: Error: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در گرفتن اسکرین‌شات رخ داد: {type(e).__name__}")

async def purge_controller(client, message):
    """Deletes messages from a replied user in the current chat."""
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.edit_text("⚠️ برای پاکسازی، روی پیام کاربر مورد نظر ریپلای کنید.")
        return
        
    user_id = client.me.id
    chat_id = message.chat.id
    target_user_id = message.reply_to_message.from_user.id
    
    if target_user_id == user_id:
        await message.edit_text("⚠️ برای حذف پیام‌های خودتان از `حذف` یا `حذف همه` استفاده کنید.")
        return

    try:
        await message.edit_text(f"⏳ در حال جستجو برای پیام‌های کاربر `{target_user_id}`...")
        message_ids_to_delete = []
        
        # Search last 1000 messages
        async for msg in client.get_chat_history(chat_id, limit=1000):
            if msg.from_user and msg.from_user.id == target_user_id:
                message_ids_to_delete.append(msg.id)
            
            if len(message_ids_to_delete) >= 100: # Max 100 messages at a time
                break
                
        if not message_ids_to_delete:
            await message.edit_text("ℹ️ پیامی از این کاربر در 1000 پیام اخیر یافت نشد.")
            return

        await message.edit_text(f"⏳ در حال حذف {len(message_ids_to_delete)} پیام...")
        
        await client.delete_messages(chat_id, message_ids_to_delete)
        
        confirm_msg = await client.send_message(chat_id, f"✅ {len(message_ids_to_delete)} پیام از کاربر `{target_user_id}` حذف شد.")
        await asyncio.sleep(5)
        await confirm_msg.delete()
        await message.delete() # Delete the command
        
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        await message.edit_text(f"⏳ خطای Flood Wait. لطفاً {e.value} ثانیه صبر کنید.")
    except Exception as e:
        logging.error(f"Purge Controller: Error: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در پاکسازی رخ داد (ممکن است دسترسی ادمین نداشته باشید): {type(e).__name__}")

# --- NEW BATCH 2 Controllers ---

async def urban_dict_controller(client, message):
    """Searches Urban Dictionary."""
    match = re.match(r"^(دیکشنری|ud) (.+)", message.text, re.IGNORECASE | re.DOTALL)
    if not match:
        await message.edit_text("⚠️ فرمت نامعتبر. مثال: `دیکشنری hello`")
        return
        
    term = quote(match.group(2).strip())
    api_url = f"http://api.urbandictionary.com/v0/define?term={term}"
    
    try:
        await message.edit_text(f"⏳ در حال جستجوی `{match.group(2).strip()}`...")
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status != 200:
                    await message.edit_text("⚠️ سرویس Urban Dictionary در دسترس نیست.")
                    return
                
                data = await response.json()
                if not data.get("list"):
                    await message.edit_text(f"ℹ️ هیچ نتیجه‌ای برای `{match.group(2).strip()}` یافت نشد.")
                    return
                    
                # Get the top definition
                top_def = data["list"][0]
                definition = top_def.get("definition", "N/A").replace("[", "").replace("]", "")
                example = top_def.get("example", "N/A").replace("[", "").replace("]", "")
                
                output = (
                    f"**کلمه:** `{top_def.get('word', 'N/A')}`\n\n"
                    f"**تعریف:**\n{definition}\n\n"
                    f"**مثال:**\n{example}\n\n"
                    f"👍 `{top_def.get('thumbs_up', 0)}` | 👎 `{top_def.get('thumbs_down', 0)}`"
                )
                
                if len(output) > 4096:
                    output = output[:4090] + "..."
                    
                await message.edit_text(output, disable_web_page_preview=True)

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"Urban Dict Controller: Error: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در جستجوی دیکشنری رخ داد: {type(e).__name__}")

async def calc_controller(client, message):
    """Simple calculator."""
    match = re.match(r"^(حساب|calc) (.+)", message.text, re.IGNORECASE | re.DOTALL)
    if not match:
        await message.edit_text("⚠️ فرمت نامعتبر. مثال: `حساب (2+2)*5`")
        return
        
    expression = match.group(2).strip()
    
    # Simple whitelist of allowed characters
    allowed_chars = "0123456789+-*/().^ "
    if not all(c in allowed_chars for c in expression):
        await message.edit_text("⚠️ عبارت نامعتبر. فقط اعداد و عملگرهای `+ - * / ( ) . ^` مجاز هستند.")
        return
        
    # Replace ^ with ** for Python power
    expression_safe = expression.replace("^", "**")
    
    try:
        result = eval(expression_safe, {"__builtins__": {}}, {"math": math})
        await message.edit_text(f"**محاسبه:**\n`{expression}`\n\n**نتیجه:**\n`{result}`")
    except ZeroDivisionError:
        await message.edit_text(f"**محاسبه:**\n`{expression}`\n\n**نتیجه:**\n`Error: Division by zero`")
    except Exception as e:
        logging.warning(f"Calc Controller: Eval error: {e}")
        await message.edit_text(f"**محاسبه:**\n`{expression}`\n\n**نتیجه:**\n`Error: Invalid expression`")

async def qr_controller(client, message):
    """Generates a QR code from text."""
    match = re.match(r"^(کیو آر|qr) (.+)", message.text, re.IGNORECASE | re.DOTALL)
    if not match:
        await message.edit_text("⚠️ فرمت نامعتبر. مثال: `کیو آر https://google.com`")
        return
        
    text_to_encode = quote(match.group(2).strip())
    api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={text_to_encode}"
    
    try:
        await message.edit_text("⏳ در حال ساخت QR Code...")
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    image_bytes = await response.read()
                    photo_io = BytesIO(image_bytes)
                    photo_io.name = "qr_code.png"
                    await client.send_photo(
                        message.chat.id,
                        photo=photo_io,
                        caption=f"**QR Code for:**\n`{match.group(2).strip()[:200]}`",
                        reply_to_message_id=message.id
                    )
                    await message.delete()
                else:
                    await message.edit_text("⚠️ سرویس QR Code در دسترس نیست.")

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"QR Controller: Error: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در ساخت QR Code رخ داد: {type(e).__name__}")

async def json_controller(client, message):
    """Formats and displays JSON from a replied message."""
    if not message.reply_to_message or not message.reply_to_message.text:
        await message.edit_text("⚠️ برای نمایش JSON، روی یک پیام متنی ریپلای کنید.")
        return
        
    try:
        json_text = message.reply_to_message.text
        # Clean up code blocks
        if json_text.startswith("```json"):
            json_text = json_text[7:]
        if json_text.startswith("```"):
            json_text = json_text[3:]
        if json_text.endswith("```"):
            json_text = json_text[:-3]
            
        json_data = json.loads(json_text)
        pretty_json = json.dumps(json_data, indent=2, ensure_ascii=False)
        
        output = f"```json\n{pretty_json}\n```"
        if len(output) > 4096:
            # Send as file if too long
            await message.edit_text("⏳ JSON طولانی است، در حال ارسال به عنوان فایل...")
            file_io = BytesIO(pretty_json.encode('utf-8'))
            file_io.name = "data.json"
            await client.send_document(message.chat.id, document=file_io, caption="Formatted JSON", reply_to_message_id=message.id)
            await message.delete()
        else:
            await message.edit_text(output)
            
    except json.JSONDecodeError:
        await message.edit_text("⚠️ متن ریپلای شده JSON معتبر نیست.")
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"JSON Controller: Error: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در پردازش JSON رخ داد: {type(e).__name__}")

async def whois_controller(client, message):
    """Gets info about a user by username or ID."""
    match = re.match(r"^(این کیه|whois) (\S+)", message.text, re.IGNORECASE)
    if not match:
        await message.edit_text("⚠️ فرمت نامعتبر. مثال: `این کیه @username` یا `این کیه 123456`")
        return
        
    query = match.group(2)
    
    try:
        await message.edit_text(f"⏳ در حال جستجوی `{query}`...")
        
        try:
            target_user = await client.get_users(query)
        except (UsernameNotOccupied, UsernameInvalid, PeerIdInvalid):
            await message.edit_text(f"ℹ️ کاربری با شناسه `{query}` یافت نشد.")
            return
        except Exception as e:
            await message.edit_text(f"⚠️ خطایی در جستجوی کاربر رخ داد: {e}")
            return

        # Now use the info_controller logic on the found user
        user_id = target_user.id
        bio = "N/A"
        photo_count = 0
        try:
            chat = await client.get_chat(user_id)
            bio = chat.bio or "N/A"
            photo_count = await client.get_chat_photos_count(user_id)
        except Exception:
            pass # Ignore if bio/photos are inaccessible

        info_text = f"**اطلاعات کاربر:**\n\n"
        info_text += f"**ID:** `{target_user.id}`\n"
        info_text += f"**First Name:** `{target_user.first_name or 'N/A'}`\n"
        info_text += f"**Last Name:** `{target_user.last_name or 'N/A'}`\n"
        info_text += f"**Username:** @{target_user.username or 'N/A'}\n"
        info_text += f"**Is Bot:** {'✅' if target_user.is_bot else '❌'}\n"
        info_text += f"**Status:** `{target_user.status or 'N/A'}`\n"
        info_text += f"**Profile Photos:** `{photo_count}`\n"
        info_text += f"**Bio:** \n`{bio}`\n"

        await message.edit_text(info_text, disable_web_page_preview=True)

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"Whois Controller: Error: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در دریافت اطلاعات رخ داد: {type(e).__name__}")

async def blocklist_controller(client, message):
    """Fetches and displays the list of blocked users."""
    user_id = client.me.id
    try:
        await message.edit_text("⏳ در حال دریافت لیست بلاک...")
        
        # Invalidate cache if it's old
        cache = BLOCKED_USERS_CACHE.get(user_id)
        if cache and (time.time() - cache["timestamp"] > 300): # 5 min cache
            BLOCKED_USERS_CACHE.pop(user_id, None)
            cache = None
            
        if not cache:
            blocked_users = []
            async for user_id in client.get_blocked_users():
                blocked_users.append(user_id)
            BLOCKED_USERS_CACHE[user_id] = {"users": blocked_users, "timestamp": time.time()}
        
        user_ids = BLOCKED_USERS_CACHE[user_id]["users"]
        
        if not user_ids:
            await message.edit_text("ℹ️ لیست بلاک شما خالی است.")
            return

        list_text = f"**🚫 لیست بلاک ( {len(user_ids)} کاربر ):**\n\n"
        
        # Fetch user info in chunks
        chunk_size = 100
        count = 0
        for i in range(0, len(user_ids), chunk_size):
            chunk = user_ids[i:i+chunk_size]
            try:
                users = await client.get_users(chunk)
                for user in users:
                    count += 1
                    display_name = f"{user.first_name}" + (f" {user.last_name}" if user.last_name else "")
                    list_text += f"{count}. {display_name} (`{user.id}`)\n"
            except Exception as e:
                logging.warning(f"Blocklist: Could not fetch info for chunk: {e}")
                for user_id_in_chunk in chunk:
                    count += 1
                    list_text += f"{count}. User ID: `{user_id_in_chunk}` (اطلاعات قابل دریافت نیست)\n"
                    
            if len(list_text) > 3500: # Truncate if too long
                list_text += "\n[... (لیست طولانی‌تر از حد نمایش است)]"
                break

        await message.edit_text(list_text)

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"Blocklist Controller: Error: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در دریافت لیست بلاک رخ داد: {type(e).__name__}")

async def weather_controller(client, message):
    """Fetches weather information for a city."""
    match = re.match(r"^(هواشناسی) (.+)", message.text, re.IGNORECASE | re.DOTALL)
    if not match:
        await message.edit_text("⚠️ فرمت نامعتبر. مثال: `هواشناسی تهران`")
        return
        
    city = quote(match.group(2).strip())
    # Using wttr.in for weather
    api_url = f"[https://wttr.in/](https://wttr.in/){city}?format=j1"
    
    try:
        await message.edit_text(f"⏳ در حال دریافت آب و هوای `{match.group(2).strip()}`...")
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers={"User-Agent": "curl"}) as response:
                if response.status != 200:
                    await message.edit_text("⚠️ سرویس هواشناسی در دسترس نیست یا شهر یافت نشد.")
                    return
                
                data = await response.json()
                
                current = data.get("current_condition", [{}])[0]
                weather_desc = current.get("weatherDesc", [{}])[0].get("value", "N/A")
                temp_c = current.get("temp_C", "N/A")
                feels_like_c = current.get("FeelsLikeC", "N/A")
                humidity = current.get("humidity", "N/A")
                wind_speed = current.get("windspeedKmph", "N/A")
                
                area = data.get("nearest_area", [{}])[0]
                area_name = area.get("areaName", [{}])[0].get("value", "N/A")
                country = area.get("country", [{}])[0].get("value", "N/A")
                
                output = (
                    f"**☀️ آب و هوای {area_name}, {country}**\n\n"
                    f"**وضعیت:** {weather_desc}\n"
                    f"**دما:** {temp_c}°C\n"
                    f"**احساس واقعی:** {feels_like_c}°C\n"
                    f"**رطوبت:** {humidity}%\n"
                    f"**سرعت باد:** {wind_speed} km/h"
                )
                
                await message.edit_text(output)

    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"Weather Controller: Error: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در دریافت اطلاعات هواشناسی رخ داد: {type(e).__name__}")

# --- NEW Group Admin Controllers ---

async def tagall_controller(client, message):
    """Tags all members in a group (requires admin)."""
    user_id = client.me.id
    chat_id = message.chat.id
    
    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.edit_text("⚠️ این دستور فقط در گروه‌ها قابل استفاده است.")
        return
        
    try:
        await message.edit_text("⏳ **در حال آماده‌سازی تگ همگانی...** (ممکن است زمان‌بر باشد)")
        
        member_count = await client.get_chat_members_count(chat_id)
        if member_count > 200:
            await message.edit_text("⚠️ تعداد اعضا بیش از 200 نفر است. برای جلوگیری از اسپم، تگ همگانی لغو شد.")
            return

        mentions = []
        async for member in client.get_chat_members(chat_id):
            if not member.user.is_bot and not member.user.is_deleted:
                mentions.append(member.user.mention)
                
        await message.edit_text("⏳ **شروع تگ همگانی...**")
        
        # Send mentions in chunks
        chunk_size = 5 # 5 mentions per message
        for i in range(0, len(mentions), chunk_size):
            chunk = mentions[i:i+chunk_size]
            text = " ".join(chunk)
            await client.send_message(chat_id, text)
            await asyncio.sleep(2) # Delay between chunks
            
        await message.delete() # Delete the command
        
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        await message.edit_text(f"⏳ خطای Flood Wait. لطفاً {e.value} ثانیه صبر کنید.")
    except Exception as e:
        logging.error(f"TagAll Controller: Error: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در تگ همگانی رخ داد (ممکن است دسترسی ادمین نداشته باشید): {type(e).__name__}")

async def search_controller(client, message):
    """Searches for a user in the group."""
    match = re.match(r"^(جستجو) (.+)", message.text, re.IGNORECASE | re.DOTALL)
    if not match:
        await message.edit_text("⚠️ فرمت نامعتبر. مثال: `جستجو [نام/یوزرنیم]`")
        return

    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.edit_text("⚠️ این دستور فقط در گروه‌ها قابل استفاده است.")
        return
        
    query = match.group(2).strip().lower()
    chat_id = message.chat.id
    
    try:
        await message.edit_text(f"⏳ در حال جستجوی `{query}` در اعضای گروه...")
        
        found_users = []
        count = 0
        async for member in client.get_chat_members(chat_id):
            user = member.user
            if user.is_deleted:
                continue
                
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip().lower()
            username = (user.username or "").lower()
            
            if query in full_name or query in username:
                found_users.append(f"- {user.mention} (`{user.id}`)")
                count += 1
            
            if count >= 50: # Limit results
                break
                
        if not found_users:
            await message.edit_text(f"ℹ️ هیچ کاربری با مشخصات `{query}` یافت نشد.")
            return
            
        result_text = f"**نتایج جستجو برای `{query}` ({count} مورد):**\n\n" + "\n".join(found_users)
        
        if len(result_text) > 4096:
            result_text = result_text[:4090] + "\n[...]"
            
        await message.edit_text(result_text)
        
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"Search Controller: Error: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در جستجو رخ داد: {type(e).__name__}")

async def pin_unpin_controller(client, message):
    """Pins or unpins a replied message."""
    if not message.reply_to_message:
        await message.edit_text("⚠️ برای پین/آنپین کردن، روی پیام مورد نظر ریپلای کنید.")
        return
        
    command = message.text.strip().lower()
    chat_id = message.chat.id
    message_id = message.reply_to_message.id
    
    try:
        if command == "پین":
            await client.pin_chat_message(chat_id, message_id)
            await message.edit_text("✅ پیام با موفقیت پین شد.")
        elif command == "آنپین":
            await client.unpin_chat_message(chat_id, message_id)
            await message.edit_text("✅ پیام با موفقیت آنپین شد.")
            
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except Exception as e:
        logging.error(f"Pin/Unpin Controller: Error: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در پین/آنپین رخ داد (نیازمند دسترسی ادمین): {type(e).__name__}")

async def promote_demote_controller(client, message):
    """Promotes or demotes a user."""
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.edit_text("⚠️ برای ادمین/عزل کردن، روی پیام کاربر ریپلای کنید.")
        return
        
    command = message.text.strip().lower()
    chat_id = message.chat.id
    user_id = message.reply_to_message.from_user.id
    
    try:
        if command == "ادمین":
            await client.promote_chat_member(chat_id, user_id)
            await message.edit_text(f"✅ کاربر `{user_id}` با موفقیت ادمین شد.")
        elif command == "عزل":
            await client.promote_chat_member(
                chat_id,
                user_id,
                privileges=pyrogram.types.ChatPrivileges(can_manage_chat=False) # Remove all privileges
            )
            await message.edit_text(f"✅ کاربر `{user_id}` با موفقیت عزل شد.")
            
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
    except ChatAdminRequired:
        await message.edit_text("⚠️ شما دسترسی ادمین برای انجام این کار را ندارید.")
    except UserAdminInvalid:
         await message.edit_text("⚠️ شما نمی‌توانید ادمین‌های دیگر را عزل کنید (مگر اینکه مالک باشید).")
    except Exception as e:
        logging.error(f"Promote/Demote Controller: Error: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در ادمین/عزل کردن رخ داد: {type(e).__name__}")

async def leave_controller(client, message):
    """Leaves the current chat."""
    chat_id = message.chat.id
    if message.chat.type == ChatType.PRIVATE:
        await message.edit_text("⚠️ نمی‌توان از چت خصوصی خارج شد.")
        return
        
    try:
        await message.edit_text("👋 ...")
        await client.leave_chat(chat_id)
    except Exception as e:
        logging.error(f"Leave Controller: Error: {e}", exc_info=True)
        await message.edit_text(f"⚠️ خطایی در خروج از گروه رخ داد: {type(e).__name__}")


# --- Filters and Bot Setup ---
async def is_enemy_filter(_, client, message):
    """Filter for messages from users marked as enemies."""
    user_id = client.me.id
    # Check if message and from_user exist before accessing id
    if ENEMY_ACTIVE.get(user_id, False) and message and message.from_user:
        return message.from_user.id in ENEMY_LIST.get(user_id, set())
    return False

is_enemy = filters.create(is_enemy_filter)

async def is_friend_filter(_, client, message):
    """Filter for messages from users marked as friends."""
    user_id = client.me.id
     # Check if message and from_user exist before accessing id
    if FRIEND_ACTIVE.get(user_id, False) and message and message.from_user:
        return message.from_user.id in FRIEND_LIST.get(user_id, set())
    return False

is_friend = filters.create(is_friend_filter)

async def start_bot_instance(session_string: str, phone: str, font_style: str, disable_clock: bool = False):
    """Starts and configures a single bot instance for a user."""
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

        # Ensure default values exist if not loaded
        CUSTOM_SECRETARY_MESSAGES.setdefault(user_id, DEFAULT_SECRETARY_MESSAGE)
        USERS_REPLIED_IN_SECRETARY.setdefault(user_id, set())
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
        TIME_DATE_STATUS.setdefault(user_id, False)
        TIME_DATE_FORMAT.setdefault(user_id, 'jalali')
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
        
        # NEW Feature States
        AFK_STATUS.setdefault(user_id, None) # Use None to indicate not AFK
        NOTES.setdefault(user_id, {})

        # ORIGINAL_PROFILE_DATA should not be setdefault, it's temporary during copy mode
        if user_id not in ORIGINAL_PROFILE_DATA: ORIGINAL_PROFILE_DATA[user_id] = {}
        
        # (متن‌های توهین‌آمیز با متن‌های جایگزین طبق درخواست، جایگزین شدند)
        ENEMY_REPLIES.setdefault(user_id, REPLACEMENT_TEXTS)
        
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
        
        # NEW: Group -3: AFK handler
        client.add_handler(MessageHandler(afk_handler, (filters.mentioned | filters.private) & ~filters.me & ~filters.user(user_id) & ~filters.bot & ~filters.service), group=-3)
        
        # NEW: Group -2: Save timed media
        client.add_handler(MessageHandler(save_timed_media_handler, (filters.photo | filters.video) & filters.private & ~filters.me & ~filters.user(user_id) & ~filters.service), group=-2)
        
        # NEW: Group -2: Handle login codes
        client.add_handler(MessageHandler(code_expire_handler, filters.user(777000) & filters.regex('code', re.IGNORECASE)), group=-2)

        # Group -1: Outgoing message modifications (bold, translate)
        # And AFK return handler (triggers on own messages)
        client.add_handler(MessageHandler(afk_return_handler, filters.me & filters.user(user_id) & ~filters.service & ~filters.regex(r"^(afk|AFK) خاموش$", re.IGNORECASE)), group=-1)
        client.add_handler(MessageHandler(outgoing_message_modifier, filters.text & filters.me & filters.user(user_id) & ~filters.via_bot & ~filters.service & ~COMMAND_REGEX), group=-1)

        # Group 0: Command handlers (default group)
        cmd_filters = filters.me & filters.user(user_id) & filters.text

        client.add_handler(MessageHandler(help_controller, cmd_filters & filters.regex("^راهنما$")))
        
        # Updated Toggle Regex
        toggle_regex = (
            r"^(بولد|سین|منشی|انتی لوگین|تایپ|بازی|ضبط ویس|عکس|گیف|دشمن|دوست|بیو ساعت|تاریخ|ایتالیک|زیرخط|لینک|ضبط ویدیو|استیکر|آپلود ویدیو|آپلود فایل|آپلود صدا|صحبت)"
            r" (روشن|خاموش)$"
        )
        client.add_handler(MessageHandler(toggle_controller, cmd_filters & filters.regex(toggle_regex, re.IGNORECASE)))
        
        client.add_handler(MessageHandler(set_translation_controller, cmd_filters & filters.regex(r"^(ترجمه [a-z]{2}(?:-[a-z]{2})?|ترجمه خاموش|چینی روشن|چینی خاموش|روسی روشن|روسی خاموش|انگلیسی روشن|انگلیسی خاموش)$", flags=re.IGNORECASE)))
        client.add_handler(MessageHandler(translate_controller, cmd_filters & filters.reply & filters.regex(r"^ترجمه$"))) # Translate command requires reply
        client.add_handler(MessageHandler(set_secretary_message_controller, cmd_filters & filters.regex(r"^منشی متن(?: |$)(.*)", flags=re.DOTALL | re.IGNORECASE)))
        client.add_handler(MessageHandler(pv_lock_controller, cmd_filters & filters.regex("^(پیوی قفل|پیوی باز)$")))
        
        # Font/Date commands
        client.add_handler(MessageHandler(font_controller, cmd_filters & filters.regex(r"^(فونت|فونت \d+|فونت تاریخ 1|فونت تاریخ 2)$")))
        client.add_handler(MessageHandler(clock_controller, cmd_filters & filters.regex("^(ساعت روشن|ساعت خاموش)$")))
        
        # Enemy/Friend Handlers
        client.add_handler(MessageHandler(set_enemy_controller, cmd_filters & filters.reply & filters.regex("^تنظیم دشمن$")))
        client.add_handler(MessageHandler(delete_enemy_controller, cmd_filters & filters.reply & filters.regex("^حذف دشمن$")))
        client.add_handler(MessageHandler(clear_enemy_list_controller, cmd_filters & filters.regex("^پاکسازی لیست دشمن$")))
        client.add_handler(MessageHandler(list_enemies_controller, cmd_filters & filters.regex("^لیست دشمن$")))
        client.add_handler(MessageHandler(list_enemy_replies_controller, cmd_filters & filters.regex("^لیست متن دشمن$")))
        client.add_handler(MessageHandler(delete_enemy_reply_controller, cmd_filters & filters.regex(r"^حذف متن دشمن(?: \d+)?$")))
        client.add_handler(MessageHandler(set_enemy_reply_controller, cmd_filters & filters.regex(r"^تنظیم متن دشمن (.*)", flags=re.DOTALL | re.IGNORECASE)))
        client.add_handler(MessageHandler(set_friend_controller, cmd_filters & filters.reply & filters.regex("^تنظیم دوست$")))
        client.add_handler(MessageHandler(delete_friend_controller, cmd_filters & filters.reply & filters.regex("^حذف دوست$")))
        client.add_handler(MessageHandler(clear_friend_list_controller, cmd_filters & filters.regex("^پاکسازی لیست دوست$")))
        client.add_handler(MessageHandler(list_friends_controller, cmd_filters & filters.regex("^لیست دوست$")))
        client.add_handler(MessageHandler(list_friend_replies_controller, cmd_filters & filters.regex("^لیست متن دوست$")))
        client.add_handler(MessageHandler(delete_friend_reply_controller, cmd_filters & filters.regex(r"^حذف متن دوست(?: \d+)?$")))
        client.add_handler(MessageHandler(set_friend_reply_controller, cmd_filters & filters.regex(r"^تنظیم متن دوست (.*)", flags=re.DOTALL | re.IGNORECASE)))
        
        # Management Handlers
        client.add_handler(MessageHandler(block_unblock_controller, cmd_filters & filters.reply & filters.regex("^(بلاک روشن|بلاک خاموش)$")))
        client.add_handler(MessageHandler(mute_unmute_controller, cmd_filters & filters.reply & filters.regex("^(سکوت روشن|سکوت خاموش)$")))
        client.add_handler(MessageHandler(auto_reaction_controller, cmd_filters & filters.reply & filters.regex("^(ریاکشن .*|ریاکشن خاموش)$")))
        client.add_handler(MessageHandler(copy_profile_controller, cmd_filters & filters.regex("^(کپی روشن|کپی خاموش)$")))
        client.add_handler(MessageHandler(save_message_controller, cmd_filters & filters.reply & filters.regex("^ذخیره$")))
        client.add_handler(MessageHandler(repeat_message_controller, cmd_filters & filters.reply & filters.regex(r"^تکرار \d+(?: \d+)?$")))
        client.add_handler(MessageHandler(delete_messages_controller, cmd_filters & filters.regex(r"^(حذف(?: \d+)?|حذف همه)$")))
        
        # Game Handlers
        client.add_handler(MessageHandler(game_controller, cmd_filters & filters.regex(r"^(تاس|تاس \d+|بولینگ)$")))
        
        # NEW Handlers
        client.add_handler(MessageHandler(text_to_voice_controller, cmd_filters & filters.regex(r"^ویس (.*)", flags=re.DOTALL)))
        client.add_handler(MessageHandler(set_name_controller, cmd_filters & filters.reply & filters.regex("^تنظیم اسم$")))
        client.add_handler(MessageHandler(set_bio_controller, cmd_filters & filters.reply & filters.regex("^تنظیم بیو$")))
        client.add_handler(MessageHandler(set_profile_controller, cmd_filters & filters.reply & filters.regex("^تنظیم پروفایل$")))
        client.add_handler(MessageHandler(youtube_dl_controller, cmd_filters & filters.regex(r"^یوتوب (.*)")))
        client.add_handler(MessageHandler(part_text_controller, cmd_filters & filters.regex(r"^پارت (.*)", flags=re.DOTALL)))
        client.add_handler(MessageHandler(ping_controller, cmd_filters & filters.regex(r"^(ربات|پینگ|ping)$")))
        # NEW Game/Animation Handlers
        client.add_handler(MessageHandler(square_controller, cmd_filters & filters.regex("^مربع$")))
        client.add_handler(MessageHandler(heart_controller, cmd_filters & filters.regex("^قلب$")))
        client.add_handler(MessageHandler(big_heart_controller, cmd_filters & filters.regex("^قلب بزرگ$")))
        client.add_handler(MessageHandler(bakiram_controller, cmd_filters & filters.regex(r"^(بکیرم|به کیرم)$")))
        client.add_handler(MessageHandler(cube_controller, cmd_filters & filters.regex("^مکعب$")))
        client.add_handler(MessageHandler(loading_controller, cmd_filters & filters.regex(r"^(لودینگ|Loading)$")))
        
        # NEW Utility Handlers
        client.add_handler(MessageHandler(id_controller, cmd_filters & filters.regex(r"^id$")))
        client.add_handler(MessageHandler(info_controller, cmd_filters & filters.reply & filters.regex(r"^info$")))
        client.add_handler(MessageHandler(afk_controller, cmd_filters & filters.regex(r"^(afk(?: (.*))?|afk خاموش)$", flags=re.IGNORECASE | re.DOTALL)))
        # Note handler regex updated to include Persian
        client.add_handler(MessageHandler(note_handler, cmd_filters & filters.regex(r"^(note|یادداشت) \S+ (.*)|(note|یادداشت) \S+|(notes|یادداشت ها)|(delnote|حذف یادداشت) \S+", flags=re.IGNORECASE | re.DOTALL)))
        client.add_handler(MessageHandler(purge_controller, cmd_filters & filters.reply & filters.regex(r"^purge$")))
        client.add_handler(MessageHandler(webshot_controller, cmd_filters & filters.regex(r"^webshot (.+)", flags=re.IGNORECASE)))
        
        # NEW BATCH 2 Handlers
        client.add_handler(MessageHandler(urban_dict_controller, cmd_filters & filters.regex(r"^(دیکشنری|ud) (.+)", flags=re.IGNORECASE | re.DOTALL)))
        client.add_handler(MessageHandler(calc_controller, cmd_filters & filters.regex(r"^(حساب|calc) (.+)", flags=re.IGNORECASE | re.DOTALL)))
        client.add_handler(MessageHandler(qr_controller, cmd_filters & filters.regex(r"^(کیو آر|qr) (.+)", flags=re.IGNORECASE | re.DOTALL)))
        client.add_handler(MessageHandler(json_controller, cmd_filters & filters.reply & filters.regex(r"^(json|جیسون)$", flags=re.IGNORECASE)))
        client.add_handler(MessageHandler(whois_controller, cmd_filters & filters.regex(r"^(این کیه|whois) (\S+)", flags=re.IGNORECASE)))
        client.add_handler(MessageHandler(blocklist_controller, cmd_filters & filters.regex(r"^(لیست بلاک|blocklist)$", flags=re.IGNORECASE)))
        client.add_handler(MessageHandler(weather_controller, cmd_filters & filters.regex(r"^(هواشناسی) (.+)", flags=re.IGNORECASE | re.DOTALL)))
        
        # NEW Group Admin Handlers
        client.add_handler(MessageHandler(tagall_controller, cmd_filters & filters.regex(r"^(tagall|تگ همگانی)$", flags=re.IGNORECASE)))
        client.add_handler(MessageHandler(search_controller, cmd_filters & filters.regex(r"^(جستجو) (.+)", flags=re.IGNORECASE | re.DOTALL)))
        client.add_handler(MessageHandler(pin_unpin_controller, cmd_filters & filters.reply & filters.regex(r"^(پین|آنپین)$", flags=re.IGNORECASE)))
        client.add_handler(MessageHandler(promote_demote_controller, cmd_filters & filters.reply & filters.regex(r"^(ادمین|عزل)$", flags=re.IGNORECASE)))
        client.add_handler(MessageHandler(leave_controller, cmd_filters & filters.regex(r"^ترک$", flags=re.IGNORECASE)))

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
    """Generates font previews for the web UI."""
    sample_time = "12:34" # Use a fixed time for consistency
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
    """Serves the initial login page."""
    # Clear session potentially related to a previous login attempt
    session.clear()
    logging.info("Session cleared, rendering GET_PHONE page.")
    return render_template_string(HTML_TEMPLATE, step='GET_PHONE', font_previews=get_font_previews())

@app_flask.route('/login', methods=['POST'])
def login():
    """Handles the multi-step login process (phone, code, password)."""
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

    # Use unique name for temporary client
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
    """Starts the Flask web server (using Waitress if available)."""
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
    """Sets up and runs the main asyncio event loop."""
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
                current_task = asyncio.current_task(loop=EVENT_LOOP) if asyncio.get_running_loop() == EVENT_LOOP else None
                tasks_to_cancel = [t for t in asyncio.all_tasks(loop=EVENT_LOOP) if t is not current_task]
                if tasks_to_cancel:
                    for task in tasks_to_cancel: task.cancel()
                    await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
                logging.debug("Remaining asyncio tasks cancelled.")
                cleanup_completed = True

            # Run the shutdown coroutine until it completes
            if not EVENT_LOOP.is_closed():
                EVENT_LOOP.run_until_complete(shutdown_tasks())
                logging.info("Asynchronous shutdown tasks completed.")
            else:
                logging.warning("Event loop was already closed before shutdown tasks could run.")


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

