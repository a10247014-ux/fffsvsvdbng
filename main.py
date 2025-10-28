import asyncio
import os
import logging
import re
import aiohttp
import time
from urllib.parse import quote
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from pyrogram.enums import ChatType, ChatAction, UserStatus
from pyrogram.errors import (
    FloodWait, SessionPasswordNeeded, PhoneCodeInvalid,
    PasswordHashInvalid, PhoneNumberInvalid, PhoneCodeExpired, UserDeactivated, AuthKeyUnregistered,
    ReactionInvalid, MessageIdInvalid, MessageNotModified, PeerIdInvalid, UserNotParticipant
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
import random
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
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
    "cursive":      {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "stylized":     {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵',':':':'},
    "doublestruck": {'0':'𝟘','1':'𝟙','2':'𝟚','3':'𝟛','4':'𝟜','5':'𝟝','6':'𝟞','7':'𝟟','8':'𝟠','9':'𝟡',':':':'},
    "monospace":    {'0':'𝟶','1':'𝟷','2':'𝟸','3':'𝟹','4':'𝟺','5':'𝟻','6':'𝟼','7':'𝟽','8':'𝟾','9':'𝟿',':':':'},
    "normal":       {'0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9',':':':'},
    "circled":      {'0':'⓪','1':'①','2':'②','3':'③','4':'④','5':'⑤','6':'⑥','7':'⑦','8':'⑧','9':'⑨',':':'∶'},
    "fullwidth":    {'0':'０','1':'１','2':'２','3':'３','4':'４','5':'５','6':'６','7':'７','8':'８','9':'９',':':'：'},
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
    "bengali":      {'0':'০','1':'১','2':'২','3':'৩','4':'৪','5':'৫','6':'৬','7':'৭','8':'৮','9':'৯',':':' : '},
    "gujarati":     {'0':'૦','1':'૧','2':'૨','3':'૩','4':'૪','5':'૫','6':'૬','7':'૭','8':'૮','9':'૯',':':' : '},
    "mongolian":    {'0':'᠐','1':'᠑','2':'᠒','3':'᠓','4':'᠔','5':'᠕','6':'᠖','7':'᠗','8':'᠘','9':'᠙',':':' : '},
    "lao":          {'0':'໐','1':'໑','2':'໒','3':'໓','4':'໔','5':'໕','6':'໖','7':'໗','8':'໘','9':'໙',':':' : '},
    "fraktur":      {'0':'𝔃','1':'𝔄','2':'𝔅','3':'𝔆','4':'𝔇','5':'𝔈','6':'𝔉','7':'𝔊','8':'𝔋','9':'𝔌',':':':'},
    "bold_fraktur": {'0':'𝖀','1':'𝖁','2':'𝖂','3':'𝖃','4':'𝖄','5':'𝖅','6':'𝖆','7':'𝖇','8':'𝖈','9':'𝖉',':':':'},
    "script":       {'0':'𝟢','1':'𝟣','2':'𝟤','3':'𝟥','4':'𝟦','5':'𝟧','6':'𝟨','7':'𝟩','8':'𝟪','9':'𝟫',':':':'},
    "bold_script":  {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "squared":      {'0':'🄀','1':'🄁','2':'🄂','3':'🄃','4':'🄄','5':'🄅','6':'🄆','7':'🄇','8':'🄈','9':'🄉',':':'∶'},
    "negative_squared": {'0':'🅀','1':'🅁','2':'🅂','3':'🅃','4':'🅄','5':'🅅','6':'🅆','7':'🅇','8':'🅈','9':'🅉',':':'∶'},
    "roman":        {'0':'⓪','1':'Ⅰ','2':'Ⅱ','3':'Ⅲ','4':'Ⅳ','5':'Ⅴ','6':'Ⅵ','7':'Ⅶ','8':'Ⅷ','9':'Ⅸ',':':':'},
    "small_caps":   {'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉',':':':'},
    "oldstyle":     {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "inverted":     {'0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9',':':':'},
    "mirror":       {'0':'0','1':'1','2':'2','3':'3','4':'4','5':'5','6':'9','7':'7','8':'8','9':'6',':':':'},
    "strike":       {'0':'0̶','1':'1̶','2':'2̶','3':'3̶','4':'4̶','5':'5̶','6':'6̶','7':'7̶','8':'8̶','9':'9̶',':':':'},
    "bubble":       {'0':'⓪','1':'①','2':'②','3':'③','4':'④','5':'⑤','6':'⑥','7':'⑦','8':'⑧','9':'⑨',':':'∶'},
    "fancy1":       {'0':'０','1':'１','2':'２','3':'３','4':'４','5':'５','6':'６','7':'７','8':'８','9':'９',':':'：'},
    "fancy2":       {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵',':':':'},
    "fancy3":       {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "fancy4":       {'0':'⓿','1':'❶','2':'❷','3':'❸','4':'❹','5':'❺','6':'❻','7':'❼','8':'❽','9':'❾',':':'∶'},
    # Additional cool fonts
    "ethiopic":     {'0':'፩','1':'፪','2':'፫','3':'፬','4':'፭','5':'፮','6':'፯','7':'፰','8':'፱','9':'፲',':':' : '},  # Approximate
    "gothic":       {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},  # Bold variant
    "runic":        {'0':'ᛟ','1':'ᛁ','2':'ᛒ','3':'ᛏ','4':'ᚠ','5':'ᚢ','6':'ᛋ','7':'ᚷ','8':'ᚺ','9':'ᛉ',':':' : '},  # Approximate runic
    "math_bold":    {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "math_italic":  {'0':'𝟢','1':'𝟣','2':'𝟤','3':'𝟥','4':'𝟦','5':'𝟧','6':'𝟨','7':'𝟩','8':'𝟪','9':'𝟫',':':':'},
    "math_sans":    {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵',':':':'},
    "math_monospace": {'0':'𝟶','1':'𝟷','2':'𝟸','3':'𝟹','4':'𝟺','5':'𝟻','6':'𝟼','7':'𝟽','8':'𝟾','9':'𝟿',':':':'},
    "math_double":  {'0':'𝟘','1':'𝟙','2':'𝟚','3':'𝟛','4':'𝟜','5':'𝟝','6':'𝟞','7':'𝟟','8':'𝟠','9':'𝟡',':':':'},
    "japanese":     {'0':'零','1':'壱','2':'弐','3':'参','4':'四','5':'伍','6':'陸','7':'漆','8':'捌','9':'玖',':':' : '},  # Kanji numbers
    "emoji":        {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣',':':':'},
    "shadow":       {'0':'🅾','1':'🅰','2':'🅱','3':'🅲','4':'🅳','5':'🅴','6':'🅵','7':'G','8':'🅷','9':'🅸',':':' : '},  # Approximate shadow
}
FONT_KEYS_ORDER = list(FONT_STYLES.keys())
FONT_DISPLAY_NAMES = {
    "cursive": "کشیده", "stylized": "فانتزی", "doublestruck": "توخالی",
    "monospace": "کامپیوتری", "normal": "ساده", "circled": "دایره‌ای", "fullwidth": "پهن",
    "sans_normal": "ساده ۲", "negative_circled": "دایره‌ای معکوس",
    "parenthesized": "پرانتزی", "dot": "نقطه‌دار", "thai": "تایلندی", "devanagari": "هندی", "arabic_indic": "عربی",
    "keycap": "کیکپ", "superscript": "بالانویس", "subscript": "زیرنویس", "tibetan": "تبتی", "bengali": "بنگالی",
    "gujarati": "گجراتی", "mongolian": "مغولی", "lao": "لائوسی",
    "fraktur": "فراکتور", "bold_fraktur": "فراکتور بولد", "script": "اسکریپت", "bold_script": "اسکریپت بولد", "squared": "مربعی", "negative_squared": "مربعی معکوس", "roman": "رومی", "small_caps": "کوچک کپس", "oldstyle": "قدیمی", "inverted": "وارونه", "mirror": "آینه‌ای", "strike": "خط خورده", "bubble": "حبابی", "fancy1": "فانتزی ۱", "fancy2": "فانتزی ۲", "fancy3": "فانتزی ۳", "fancy4": "فانتزی ۴",
    "ethiopic": "اتیوپیک", "gothic": "گوتیک", "runic": "رونیک", "math_bold": "ریاضی بولد", "math_italic": "ریاضی ایتالیک", "math_sans": "ریاضی سنس", "math_monospace": "ریاضی مونوسپیس", "math_double": "ریاضی دوبل", "japanese": "ژاپنی", "emoji": "ایموجی", "shadow": "سایه‌دار",
}
ALL_CLOCK_CHARS = "".join(set(char for font in FONT_STYLES.values() for char in font.values()))
CLOCK_CHARS_REGEX_CLASS = f"[{re.escape(ALL_CLOCK_CHARS)}]"

# --- Feature Variables ---
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
BOLD_MODE_STATUS = {}
AUTO_SEEN_STATUS = {}
AUTO_REACTION_TARGETS = {}  # {user_id: {target_user_id: emoji}}
AUTO_TRANSLATE_TARGET = {}  # {user_id: lang_code}
ANTI_LOGIN_STATUS = {}
COPY_MODE_STATUS = {}
ORIGINAL_PROFILE_DATA = {}
TYPING_MODE_STATUS = {}
PLAYING_MODE_STATUS = {}
RECORD_VOICE_STATUS = {}
UPLOAD_PHOTO_STATUS = {}
WATCH_GIF_STATUS = {}
PV_LOCK_STATUS = {}

# --- Task Management ---
EVENT_LOOP = asyncio.new_event_loop()
ACTIVE_CLIENTS = {}
ACTIVE_BOTS = {}

DEFAULT_SECRETARY_MESSAGE = "سلام! منشی هستم. پیامتون رو دیدم، بعدا جواب می‌دم."

COMMAND_REGEX = r"^(تایپ روشن|تایپ خاموش|بازی روشن|بازی خاموش|ضبط ویس روشن|ضبط ویس خاموش|عکس روشن|عکس خاموش|گیف روشن|گیف خاموش|ترجمه [a-z]{2}(?:-[a-z]{2})?|ترجمه خاموش|چینی روشن|چینی خاموش|روسی روشن|روسی خاموش|انگلیسی روشن|انگلیسی خاموش|بولد روشن|بولد خاموش|سین روشن|سین خاموش|ساعت روشن|ساعت خاموش|فونت|فونت \d+|منشی روشن|منشی خاموش|منشی متن(?: |$)(.*)|انتی لوگین روشن|انتی لوگین خاموش|پیوی قفل|پیوی باز|ذخیره|تکرار \d+( \d+)?|حذف(?: \d+)?|حذف همه|دشمن روشن|دشمن خاموش|تنظیم دشمن|حذف دشمن|پاکسازی لیست دشمن|لیست دشمن|لیست متن دشمن|تنظیم متن دشمن .*|حذف متن دشمن(?: \d+)?|دوست روشن|دوست خاموش|تنظیم دوست|حذف دوست|پاکسازی لیست دوست|لیست دوست|لیست متن دوست|تنظیم متن دوست .*|حذف متن دوست(?: \d+)?|بلاک روشن|بلاک خاموش|سکوت روشن|سکوت خاموش|ریاکشن .*|ریاکشن خاموش|کپی روشن|کپی خاموش|تاس|تاس \d+|بولینگ|راهنما|ترجمه)$"

# --- Main Bot Functions ---
def stylize_time(time_str: str, style: str) -> str:
    font_map = FONT_STYLES.get(style, FONT_STYLES["stylized"])
    return ''.join(font_map.get(char, char) for char in time_str)

async def update_profile_clock(client: Client, user_id: int):
    log_message = f"Starting clock loop for user_id {user_id}..."
    logging.info(log_message)

    while user_id in ACTIVE_BOTS:
        try:
            if CLOCK_STATUS.get(user_id, True) and not COPY_MODE_STATUS.get(user_id, False):
                current_font_style = USER_FONT_CHOICES.get(user_id, 'stylized')
                me = await client.get_me()
                current_name = me.first_name or ""
                base_name = re.sub(r'\s+[' + re.escape(ALL_CLOCK_CHARS) + r':\s]+$', '', current_name).strip()
                if not base_name: base_name = me.username or f"User_{user_id}"
                tehran_time = datetime.now(TEHRAN_TIMEZONE)
                current_time_str = tehran_time.strftime("%H:%M")
                stylized_time = stylize_time(current_time_str, current_font_style)
                new_name = f"{base_name} {stylized_time}"
                if new_name != current_name:
                    await client.update_profile(first_name=new_name[:64])

            now = datetime.now(TEHRAN_TIMEZONE)
            sleep_duration = 60 - now.second + 0.1
            await asyncio.sleep(sleep_duration)

        except (UserDeactivated, AuthKeyUnregistered):
            logging.error(f"Clock Task: Session for user_id {user_id} is invalid. Stopping task.")
            break
        except FloodWait as e:
            logging.warning(f"Clock Task: Flood wait of {e.value}s for user_id {user_id}.")
            await asyncio.sleep(e.value + 5)
        except Exception as e:
            logging.error(f"An error occurred in clock task for user_id {user_id}: {e}", exc_info=True)
            await asyncio.sleep(60)

    logging.info(f"Clock task for user_id {user_id} has stopped.")

async def anti_login_task(client: Client, user_id: int):
    logging.info(f"Starting anti-login task for user_id {user_id}...")
    while user_id in ACTIVE_BOTS:
        try:
            if ANTI_LOGIN_STATUS.get(user_id, False) and functions:
                auths = await client.invoke(functions.account.GetAuthorizations())
                current_hash = None
                for auth in auths.authorizations:
                    if auth.current:
                        current_hash = auth.hash
                        break
                if current_hash:
                    sessions_terminated = 0
                    for auth in auths.authorizations:
                        if not auth.current:
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
                    #if sessions_terminated > 0:
                    #    logging.info(f"Anti-Login: Terminated {sessions_terminated} session(s) for user {user_id}.")

            await asyncio.sleep(60 * 5)

        except (UserDeactivated, AuthKeyUnregistered):
            logging.error(f"Anti-Login Task: Session for user_id {user_id} is invalid. Stopping task.")
            break
        except AttributeError:
             logging.error(f"Anti-Login Task: 'pyrogram.raw.functions' module not available for user_id {user_id}. Feature disabled.")
             ANTI_LOGIN_STATUS[user_id] = False
             await asyncio.sleep(3600)
        except Exception as e:
            logging.error(f"An error occurred in anti-login task for user_id {user_id}: {e}", exc_info=True)
            await asyncio.sleep(120)

    logging.info(f"Anti-login task for user_id {user_id} has stopped.")

async def status_action_task(client: Client, user_id: int):
    logging.info(f"Starting status action task for user_id {user_id}...")
    chat_ids_cache = []
    last_dialog_fetch_time = 0
    FETCH_INTERVAL = 300

    while user_id in ACTIVE_BOTS:
        try:
            typing_mode = TYPING_MODE_STATUS.get(user_id, False)
            playing_mode = PLAYING_MODE_STATUS.get(user_id, False)
            record_voice = RECORD_VOICE_STATUS.get(user_id, False)
            upload_photo = UPLOAD_PHOTO_STATUS.get(user_id, False)
            watch_gif = WATCH_GIF_STATUS.get(user_id, False)

            if not (typing_mode or playing_mode or record_voice or upload_photo or watch_gif):
                await asyncio.sleep(5)
                continue

            action_to_send = None
            if typing_mode:
                action_to_send = ChatAction.TYPING
            elif playing_mode:
                action_to_send = ChatAction.PLAYING
            elif record_voice:
                action_to_send = ChatAction.RECORD_AUDIO
            elif upload_photo:
                action_to_send = ChatAction.UPLOAD_PHOTO
            elif watch_gif:
                action_to_send = ChatAction.CHOOSE_STICKER

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
                     chat_ids_cache = []
                     last_dialog_fetch_time = 0
                     await asyncio.sleep(60)
                     continue

            if not chat_ids_cache:
                logging.warning(f"Status Action: No suitable chats found in cache for user_id {user_id}.")
                await asyncio.sleep(30)
                continue

            for chat_id in chat_ids_cache:
                try:
                    await client.send_chat_action(chat_id, action_to_send)
                except FloodWait as e_action:
                    logging.warning(f"Status Action: Flood wait sending action to chat {chat_id} for user {user_id}. Sleeping {e_action.value}s.")
                    await asyncio.sleep(e_action.value + 1)
                except PeerIdInvalid:
                     logging.warning(f"Status Action: PeerIdInvalid for chat {chat_id}. Removing from cache.")
                     try: chat_ids_cache.remove(chat_id)
                     except ValueError: pass
                except Exception:
                    pass

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
                        data = await response.json(content_type=None)
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

async def outgoing_message_modifier(client, message):
    user_id = client.me.id
    if not message.text or message.text.startswith("/") or message.entities or re.match(COMMAND_REGEX, message.text.strip(), re.IGNORECASE):
        return

    original_text = message.text
    modified_text = original_text
    needs_edit = False

    target_lang = AUTO_TRANSLATE_TARGET.get(user_id)
    if target_lang:
        translated = await translate_text(modified_text, target_lang)
        if translated != modified_text:
             modified_text = translated
             needs_edit = True
             original_text_before_bold = translated
        else:
             original_text_before_bold = original_text
    else:
        original_text_before_bold = original_text

    if BOLD_MODE_STATUS.get(user_id, False):
        if not modified_text.startswith(('**', '__')):
            modified_text_bolded = f"**{modified_text}**"
            if modified_text_bolded != original_text_before_bold:
                 modified_text = modified_text_bolded
                 needs_edit = True

    if needs_edit:
        try:
            await message.edit_text(modified_text, disable_web_page_preview=True)
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
        replied_users_today = USERS_REPLIED_IN_SECRETARY.setdefault(owner_user_id, set())

        if target_user_id not in replied_users_today:
            reply_message_text = CUSTOM_SECRETARY_MESSAGES.get(owner_user_id, DEFAULT_SECRETARY_MESSAGE)
            try:
                await message.reply_text(reply_message_text, quote=True)
                replied_users_today.add(target_user_id)
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


async def toggle_controller(client, message):
    user_id = client.me.id
    command = message.text.strip()
    try:
        if command.endswith("روشن"):
            feature = command[:-5].strip()
            status_changed = False
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

            if status_changed:
                await message.edit_text(f"✅ {feature} فعال شد.")
            else:
                await message.edit_text(f"ℹ️ {feature} از قبل فعال بود.")

        elif command.endswith("خاموش"):
            feature = command[:-6].strip()
            status_changed = False
            if feature == "بولد":
                 if BOLD_MODE_STATUS.get(user_id, False): BOLD_MODE_STATUS[user_id] = False; status_changed = True
            elif feature == "سین":
                 if AUTO_SEEN_STATUS.get(user_id, False): AUTO_SEEN_STATUS[user_id] = False; status_changed = True
            elif feature == "منشی":
                 if SECRETARY_MODE_STATUS.get(user_id, False):
                     SECRETARY_MODE_STATUS[user_id] = False
                     USERS_REPLIED_IN_SECRETARY[user_id] = set() # Clear replied users when turning off
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
    match = re.match(r"^منشی متن(?: |$)(.*)", message.text, re.DOTALL | re.IGNORECASE) # Added IGNORECASE
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
                    await client.set_profile_photo(photo=original_photo_data)
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
                    me_photo_bytes = await client.download_media(me.photo.big_file_id, in_memory=True) # download to memory
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
            target_photo_bytes = None
            target_bio = ""
            try:
                 target_full = await client.invoke(functions.users.GetFullUser(id=await client.resolve_peer(target_id)))
                 target_bio = target_full.full_user.about or ''
            except Exception as e_get_target_bio:
                 logging.warning(f"Copy Profile (Target): Could not get target bio for user {target_id}: {e_get_target_bio}")

            if target_user.photo:
                try:
                    target_photo_bytes = await client.download_media(target_user.photo.big_file_id, in_memory=True) # download to memory
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
            if target_photo_bytes:
                try:
                    await client.set_profile_photo(photo=target_photo_bytes)
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
            await message.edit_text("⚠️ خطایی در کپی پروفایل رخ داد.")
        except Exception:
            pass


async def font_controller(client, message):
    user_id = client.me.id
    command = message.text.strip()
    try:
        if command == "فونت":
            font_list = "\n".join([f"{i+1}. {FONT_DISPLAY_NAMES.get(key, key.capitalize())}" for i, key in enumerate(FONT_KEYS_ORDER)])
            await message.edit_text(f"فونت‌های موجود:\n{font_list}\n\nبرای انتخاب: فونت <شماره>")
        else:
            match = re.match(r"^فونت (\d+)$", command)
            if match:
                index = int(match.group(1)) - 1
                if 0 <= index < len(FONT_KEYS_ORDER):
                    selected_style = FONT_KEYS_ORDER[index]
                    USER_FONT_CHOICES[user_id] = selected_style
                    await message.edit_text(f"✅ فونت به '{FONT_DISPLAY_NAMES.get(selected_style, selected_style.capitalize())}' تغییر کرد.")
                else:
                    await message.edit_text(f"⚠️ شماره نامعتبر. بین 1 تا {len(FONT_KEYS_ORDER)} وارد کنید.")
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
        USERS_REPLIED_IN_SECRETARY.setdefault(user_id, set())
        BOLD_MODE_STATUS.setdefault(user_id, False)
        AUTO_SEEN_STATUS.setdefault(user_id, False)
        AUTO_REACTION_TARGETS.setdefault(user_id, {})
        AUTO_TRANSLATE_TARGET.setdefault(user_id, None)
        ANTI_LOGIN_STATUS.setdefault(user_id, False)
        COPY_MODE_STATUS.setdefault(user_id, False) # Should always start False
        TYPING_MODE_STATUS.setdefault(user_id, False)
        PLAYING_MODE_STATUS.setdefault(user_id, False)
        RECORD_VOICE_STATUS.setdefault(user_id, False)
        UPLOAD_PHOTO_STATUS.setdefault(user_id, False)
        WATCH_GIF_STATUS.setdefault(user_id, False)
        PV_LOCK_STATUS.setdefault(user_id, False)
        MUTED_USERS.setdefault(user_id, set())
        # ORIGINAL_PROFILE_DATA should not be setdefault, it's temporary during copy mode
        if user_id not in ORIGINAL_PROFILE_DATA: ORIGINAL_PROFILE_DATA[user_id] = {}
        ENEMY_REPLIES.setdefault(user_id, [ # Default enemy replies if list is empty/new user
            "کیرم تو رحم اجاره ای و خونی مالی مادرت",
            # ... (other default replies) ...
            "کیرم تویه اون خرخره مادرت بیا اینحا ببینم تویه نوچه کی دانلود شدی کیفیتت پایینه صدات نمیاد فقط رویه حالیت بی صدا داری امواج های بی ارزش و بیناموسانه از خودت ارسال میکنی که ناگهان دیدی من روانی شدم دست از پا خطا کردم با تبر کائنات کوبیدم رو سر مادرت نمیتونی مارو تازه بالقه گمان کنی"
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

        # Group -1: Outgoing message modifications (bold, translate)
        # Ensure it doesn't process commands by checking regex again? Or rely on outgoing_message_modifier logic.
        # Added ~filters.regex(COMMAND_REGEX) to be explicit
        client.add_handler(MessageHandler(outgoing_message_modifier, filters.text & filters.me & filters.user(user_id) & ~filters.via_bot & ~filters.reply & ~filters.service & ~filters.regex(COMMAND_REGEX)), group=-1)

        # Group 0: Command handlers (default group)
        cmd_filters = filters.me & filters.user(user_id) & filters.text

        client.add_handler(MessageHandler(help_controller, cmd_filters & filters.regex("^راهنما$")))
        client.add_handler(MessageHandler(toggle_controller, cmd_filters & filters.regex("^(بولد روشن|بولد خاموش|سین روشن|سین خاموش|منشی روشن|منشی خاموش|انتی لوگین روشن|انتی لوگین خاموش|تایپ روشن|تایپ خاموش|بازی روشن|بازی خاموش|ضبط ویس روشن|ضبط ویس خاموش|عکس روشن|عکس خاموش|گیف روشن|گیف خاموش|دشمن روشن|دشمن خاموش|دوست روشن|دوست خاموش)$")))
        client.add_handler(MessageHandler(set_translation_controller, cmd_filters & filters.regex(r"^(ترجمه [a-z]{2}(?:-[a-z]{2})?|ترجمه خاموش|چینی روشن|چینی خاموش|روسی روشن|روسی خاموش|انگلیسی روشن|انگلیسی خاموش)$", flags=re.IGNORECASE)))
        client.add_handler(MessageHandler(translate_controller, cmd_filters & filters.reply & filters.regex(r"^ترجمه$"))) # Translate command requires reply
        client.add_handler(MessageHandler(set_secretary_message_controller, cmd_filters & filters.regex(r"^منشی متن(?: |$)(.*)", flags=re.DOTALL | re.IGNORECASE)))
        client.add_handler(MessageHandler(pv_lock_controller, cmd_filters & filters.regex("^(پیوی قفل|پیوی باز)$")))
        client.add_handler(MessageHandler(font_controller, cmd_filters & filters.regex(r"^(فونت|فونت \d+)$")))
        client.add_handler(MessageHandler(clock_controller, cmd_filters & filters.regex("^(ساعت روشن|ساعت خاموش)$")))
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
        client.add_handler(MessageHandler(block_unblock_controller, cmd_filters & filters.reply & filters.regex("^(بلاک روشن|بلاک خاموش)$"))) # Requires reply
        client.add_handler(MessageHandler(mute_unmute_controller, cmd_filters & filters.reply & filters.regex("^(سکوت روشن|سکوت خاموش)$"))) # Requires reply
        client.add_handler(MessageHandler(auto_reaction_controller, cmd_filters & filters.reply & filters.regex("^(ریاکشن .*|ریاکشن خاموش)$"))) # Requires reply
        # Copy profile handler needs careful filter: allow reply only for 'copy روشن'
        client.add_handler(MessageHandler(copy_profile_controller, cmd_filters & filters.regex("^(کپی روشن|کپی خاموش)$"))) # Logic inside handles reply check
        client.add_handler(MessageHandler(save_message_controller, cmd_filters & filters.reply & filters.regex("^ذخیره$"))) # Requires reply
        client.add_handler(MessageHandler(repeat_message_controller, cmd_filters & filters.reply & filters.regex(r"^تکرار \d+(?: \d+)?$"))) # Requires reply
        client.add_handler(MessageHandler(delete_messages_controller, cmd_filters & filters.regex(r"^(حذف(?: \d+)?|حذف همه)$")))
        client.add_handler(MessageHandler(game_controller, cmd_filters & filters.regex(r"^(تاس|تاس \d+|بولینگ)$")))

        # Group 1: Auto-reply handlers (lower priority than commands and basic management)
        # Added ~filters.user(user_id) to ensure these don't trigger on own messages if filters somehow match
        client.add_handler(MessageHandler(enemy_handler, is_enemy & ~filters.me & ~filters.user(user_id) & ~filters.bot & ~filters.service), group=1)
        client.add_handler(MessageHandler(friend_handler, is_friend & ~filters.me & ~filters.user(user_id) & ~filters.bot & ~filters.service), group=1)
        client.add_handler(MessageHandler(secretary_auto_reply_handler, filters.private & ~filters.me & ~filters.user(user_id) & ~filters.bot & ~filters.service), group=1)

        # --- Start Background Tasks ---
        tasks = [
            asyncio.create_task(update_profile_clock(client, user_id)),
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

async def delete_messages_controller(client, message):
    user_id = client.me.id
    chat_id = message.chat.id
    command = message.text.strip()
    try:
        if command == "حذف همه":
            # حذف تمام پیام‌های خود کاربر در این چت
            message_ids = []
            async for msg in client.get_chat_history(chat_id):
                if msg.from_user and msg.from_user.id == user_id:
                    message_ids.append(msg.id)
                if len(message_ids) >= 100:  # حذف دسته‌ای برای جلوگیری از فلاد
                    await client.delete_messages(chat_id, message_ids)
                    message_ids = []
                    await asyncio.sleep(1)  # جلوگیری از فلاد
            if message_ids:
                await client.delete_messages(chat_id, message_ids)
            await message.edit_text("✅ تمام پیام‌های شما حذف شد.")
        else:
            match = re.match(r"^حذف (\d+)$", command)
            if match:
                num = int(match.group(1))
                # حذف num پیام آخر خود کاربر
                message_ids = []
                count = 0
                async for msg in client.get_chat_history(chat_id, limit=num * 2):  # دو برابر برای اطمینان
                    if msg.from_user and msg.from_user.id == user_id:
                        message_ids.append(msg.id)
                        count += 1
                        if count >= num:
                            break
                if message_ids:
                    await client.delete_messages(chat_id, message_ids)
                await message.edit_text(f"✅ {len(message_ids)} پیام حذف شد.")
            else:
                await message.edit_text("⚠️ دستور نامعتبر. مثال: حذف 100 یا حذف همه")
    except FloodWait as e:
        await asyncio.sleep(e.value + 1)
        await message.edit_text(f"⚠️ فلاد ویت: {e.value} ثانیه صبر کنید.")
    except Exception as e:
        logging.error(f"Delete Messages: Error for user {user_id}: {e}")
        await message.edit_text("⚠️ خطایی در حذف پیام‌ها رخ داد.")

async def game_controller(client, message):
    user_id = client.me.id
    command = message.text.strip()
    chat_id = message.chat.id
    try:
        await message.delete()
        if command == "بولینگ":
            await client.send_dice(chat_id, emoji="🎳")
        elif command.startswith("تاس"):
            match = re.match(r"^تاس (\d+)$", command)
            if match:
                value = int(match.group(1))
                if 1 <= value <= 6:
                    await client.send_dice(chat_id, emoji="🎲", value=value)
                else:
                    await client.send_message(chat_id, "⚠️ عدد باید بین 1 تا 6 باشد.")
            else:
                await client.send_dice(chat_id, emoji="🎲")
        else:
            await client.send_message(chat_id, "⚠️ دستور نامعتبر.")
    except Exception as e:
        logging.error(f"Game Controller: Error for user {user_id}: {e}")
        await client.send_message(chat_id, "⚠️ خطایی در بازی رخ داد.")
