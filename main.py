# -*- coding: utf-8 -*-
# self_merged.py
# ترکیب کامل: کد اصلی شما + قابلیت‌های اضافه‌شده (بر اساس self.txt)
# کامنت‌ها و دستورات فارسی در سراسر فایل
# هشدار: اجرای این فایل نیازمند پکیج‌ها و تنظیمات محیطی است (Pyrogram, aiohttp, pymongo, matplotlib, numpy, gTTS و غیره)
# اگر پکیج‌ها نصب نیستند، قابلیت‌های وابسته به صورت مشروط غیرفعال می‌شوند.

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
import json
import tempfile
import shutil

# Optional heavy imports: matplotlib, numpy, gTTS, googletrans, pytz
# آنها به صورت شرطی بارگذاری می‌شوند؛ اگر نصب نبودند، قابلیت‌های وابسته غیرفعال می‌شوند.
HAS_MATPLOTLIB = True
HAS_NUMPY = True
HAS_GTTs = True
HAS_GOOGLETRANS = True
HAS_PYTZ = True

try:
    import matplotlib.pyplot as plt
except Exception:
    HAS_MATPLOTLIB = False
    logging.warning("matplotlib در دسترس نیست؛ قابلیت ساخت عکس ساعت غیرفعال خواهد بود.")

try:
    import numpy as np
except Exception:
    HAS_NUMPY = False
    logging.warning("numpy در دسترس نیست؛ قابلیت ساخت عکس ساعت غیرفعال خواهد بود.")

try:
    from gtts import gTTS
except Exception:
    HAS_GTTs = False
    logging.warning("gTTS در دسترس نیست؛ قابلیت تبدیل متن به صدا غیرفعال خواهد بود.")

try:
    from googletrans import Translator as GoogleTranslator
except Exception:
    HAS_GOOGLETRANS = False
    logging.warning("googletrans در دسترس نیست؛ قابلیت مترجم آفلاین به صورت محدود کار خواهد کرد.")

try:
    import pytz
except Exception:
    HAS_PYTZ = False
    logging.warning("pytz در دسترس نیست؛ از zoneinfo استفاده خواهد شد یا زمان محلی استفاده می‌شود.")

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
user_settings_collection = None
if MONGO_URI and "<db_password>" not in MONGO_URI:
    try:
        mongo_client = MongoClient(MONGO_URI, server_api=ServerApi('1'), tlsCAFile=certifi.where())
        mongo_client.admin.command('ping')
        db = mongo_client['telegram_self_bot']
        sessions_collection = db['sessions']
        user_settings_collection = db['user_settings']
        logging.info("Successfully connected to MongoDB!")
    except Exception as e:
        logging.error(f"Could not connect to MongoDB: {e}")
        mongo_client = None
        sessions_collection = None
        user_settings_collection = None
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
    "bengali":      {'0':'০','1':'১','2':'২','3':'৩','4':'৪','5':'৫','6':'৬','7':'۷','8':'۸','9':'۹',':':' : '},
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
    "fancy1":       {'0':'０','1':'１','2':'２','3':'３','4':'４','5':'５','6':'６','7':'۷','8':'８','9':'９',':':'：'},
    "fancy2":       {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵',':':':'},
    "fancy3":       {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "fancy4":       {'0':'⓿','1':'❶','2':'❷','3':'❸','4':'❹','5':'❺','6':'❻','7':'❼','8':'❽','9':'❾',':':'∶'},
    "ethiopic":     {'0':'፩','1':'፪','2':'፫','3':'፬','4':'፭','5':'፮','6':'፯','7':'፰','8':'፱','9':'፲',':':' : '},
    "gothic":       {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "runic":        {'0':'ᛟ','1':'ᛁ','2':'ᛒ','3':'ᛏ','4':'ᚠ','5':'ᚢ','6':'ᛋ','7':'ᚷ','8':'ᚺ','9':'ᛉ',':':' : '},
    "math_bold":    {'0':'𝟎','1':'𝟏','2':'𝟐','3':'𝟑','4':'𝟒','5':'𝟓','6':'𝟔','7':'𝟕','8':'𝟖','9':'𝟗',':':':'},
    "math_italic":  {'0':'𝟢','1':'𝟣','2':'𝟤','3':'𝟥','4':'𝟦','5':'𝟧','6':'𝟨','7':'𝟩','8':'𝟪','9':'𝟫',':':':'},
    "math_sans":    {'0':'𝟬','1':'𝟭','2':'𝟮','3':'𝟯','4':'𝟰','5':'𝟱','6':'𝟲','7':'𝟳','8':'𝟴','9':'𝟵',':':':'},
    "math_monospace": {'0':'𝟶','1':'𝟷','2':'𝟸','3':'𝟹','4':'𝟺','5':'𝟻','6':'𝟼','7':'𝟽','8':'𝟾','9':'𝟿',':':':'},
    "math_double":  {'0':'𝟘','1':'𝟙','2':'𝟚','3':'𝟛','4':'𝟜','5':'𝟝','6':'𝟞','7':'𝟟','8':'𝟠','9':'𝟡',':':':'},
    "japanese":     {'0':'零','1':'壱','2':'弐','3':'参','4':'四','5':'伍','6':'陸','7':'漆','8':'捌','9':'玖',':':' : '},
    "emoji":        {'0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣','5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣',':':':'},
    "shadow":       {'0':'🅾','1':'🅰','2':'🅱','3':'🅲','4':'🅳','5':'🅴','6':'🅵','7':'G','8':'🅷','9':'🅸',':':' : '},
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

# --- Feature Variables (global state kept per user_id) ---
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
# Additional toggles from self.txt
TEXT_MODES = {}  # {user_id: {hashtag:bool,bold:bool,italic:bool,delete:bool,code:bool,underline:bool,reverse:bool,part:bool,mention:bool,spoiler:bool}}
TIME_MODES = {}  # {user_id: {timename:bool,timebio:bool,timeprofile:bool,timecrash:bool}}
LISTS = {}       # {user_id: {enemy:[],crash:[]}}

# --- Task Management ---
EVENT_LOOP = asyncio.new_event_loop()
ACTIVE_CLIENTS = {}
ACTIVE_BOTS = {}

DEFAULT_SECRETARY_MESSAGE = "سلام! منشی هستم. پیامتون رو دیدم، بعدا جواب می‌دم."

COMMAND_REGEX = r"^(تایپ روشن|تایپ خاموش|بازی روشن|بازی خاموش|ضبط ویس روشن|ضبط ویس خاموش|عکس روشن|عکس خاموش|گیف روشن|گیف خاموش|ترجمه [a-z]{2}(?:-[a-z]{2})?|ترجمه خاموش|چینی روشن|چینی خاموش|روسی روشن|روسی خاموش|انگلیسی روشن|انگلیسی خاموش|بولد روشن|بولد خاموش|سین روشن|سین خاموش|ساعت روشن|ساعت خاموش|فونت|فونت \d+|منشی روشن|منشی خاموش|منشی متن(?: |$)(.*)|انتی لوگین روشن|انتی لوگین خاموش|پیوی قفل|پیوی باز|ذخیره|تکرار \d+( \d+)?|حذف همه|حذف(?: \d+)?|دشمن روشن|دشمن خاموش|تنظیم دشمن|حذف دشمن|پاکسازی لیست دشمن|لیست دشمن|لیست متن دشمن|تنظیم متن دشمن .*|حذف متن دشمن(?: \d+)?|دوست روشن|دوست خاموش|تنظیم دوست|حذف دوست|پاکسازی لیست دوست|لیست دوست|لیست متن دوست|تنظیم متن دوست .*|حذف متن دوست(?: \d+)?|بلاک روشن|بلاک خاموش|سکوت روشن|سکوت خاموش|ریاکشن .*|ریاکشن خاموش|کپی روشن|کپی خاموش|تاس|تاس \d+|بولینگ|راهنما|ترجمه)$"

# --- Helper functions for DB persistence (user settings) ---
async def load_user_settings(user_id: int) -> dict:
    """بارگذاری تنظیمات کاربر از MongoDB؛ اگر موجود نبود، مقدار پیش‌فرض ایجاد می‌کند."""
    defaults = {
        "font_style": "stylized",
        "disable_clock": False,
        "modes": {
            "hashtag": "off","bold":"off","italic":"off","delete":"off","code":"off",
            "underline":"off","reverse":"off","part":"off","mention":"off","spoiler":"off"
        },
        "time_modes": {"timename":"off","timebio":"off","timeprofile":"off","timecrash":"off"},
        "lists": {"enemy": [], "crash": []},
        "secretary_message": DEFAULT_SECRETARY_MESSAGE,
        "auto_reactions": {},
        "auto_translate": None
    }
    if user_settings_collection is None:
        # Fall back to in-memory defaults
        return defaults
    try:
        doc = user_settings_collection.find_one({"user_id": user_id})
        if not doc:
            # Insert defaults
            user_settings_collection.insert_one({"user_id": user_id, **defaults, "created_at": datetime.utcnow()})
            return defaults
        # Merge defaults with stored doc
        merged = defaults.copy()
        merged.update({k: doc.get(k, v) for k, v in defaults.items()})
        # Ensure nested dicts exist
        merged["modes"] = doc.get("modes", defaults["modes"])
        merged["time_modes"] = doc.get("time_modes", defaults["time_modes"])
        merged["lists"] = doc.get("lists", defaults["lists"])
        merged["secretary_message"] = doc.get("secretary_message", defaults["secretary_message"])
        merged["auto_reactions"] = doc.get("auto_reactions", defaults["auto_reactions"])
        merged["auto_translate"] = doc.get("auto_translate", defaults["auto_translate"])
        return merged
    except Exception as e:
        logging.error(f"load_user_settings error for {user_id}: {e}")
        return defaults

async def save_user_settings(user_id: int, settings: dict):
    """ذخیره تنظیمات کاربر در MongoDB."""
    if user_settings_collection is None:
        return
    try:
        settings_copy = settings.copy()
        settings_copy["updated_at"] = datetime.utcnow()
        user_settings_collection.update_one({"user_id": user_id}, {"$set": settings_copy}, upsert=True)
    except Exception as e:
        logging.error(f"save_user_settings error for {user_id}: {e}")

# --- Basic utilities ---
def stylize_time(time_str: str, style: str) -> str:
    font_map = FONT_STYLES.get(style, FONT_STYLES["stylized"])
    return ''.join(font_map.get(char, char) for char in time_str)

def safe_filename(prefix='tmp', suffix='.dat'):
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    os.close(fd)
    return path

# --- Image clock maker (async wrapper) ---
async def make_clock_image(h: int, m: int, s: int, background_path: str, out_path: str):
    """اگر matplotlib و numpy نصب باشند، تصویر ساعت می‌سازد و ذخیره می‌کند."""
    if not (HAS_MATPLOTLIB and HAS_NUMPY):
        raise RuntimeError("matplotlib یا numpy نصب نیست؛ قابلیت ساخت تصویر غیرفعال است.")
    # استفاده از اجرای همگام در حلقهٔ اجرا برای جلوگیری از مشکل matplotlib در async contexts
    def _make():
        img = plt.imread(background_path) if os.path.exists(background_path) else None
        fig = plt.figure(figsize=(4,4), dpi=300, facecolor=[0.2,0.2,0.2])
        ax_image = fig.add_axes([0,0,1,1])
        ax_image.axis('off')
        if img is not None:
            ax_image.imshow(img)
        axc = fig.add_axes([0.062,0.062,0.88,0.88], projection='polar')
        axc.cla()
        seconds = np.multiply(np.ones(5), s * 2 * np.pi / 60)
        minutes = np.multiply(np.ones(5), m * 2 * np.pi / 60) + (seconds / 60)
        hours = np.multiply(np.ones(5), h * 2 * np.pi / 12) + (minutes / 12)
        axc.axis('off')
        axc.set_theta_zero_location('N')
        axc.set_theta_direction(-1)
        axc.plot(hours, np.linspace(0.00,0.70,5), c='c', linewidth=2.0)
        axc.plot(minutes, np.linspace(0.00,0.85,5), c='b', linewidth=1.5)
        axc.plot(seconds, np.linspace(0.00,1.00,5), c='r', linewidth=1.0)
        axc.plot(minutes, np.linspace(0.73,0.83,5), c='w', linewidth=1.0)
        axc.plot(hours, np.linspace(0.60,0.68,5), c='w', linewidth=1.5)
        axc.plot(seconds, np.linspace(0.80,0.98,5), c='w', linewidth=0.5)
        axc.set_rmax(1)
        plt.savefig(out_path)
        plt.close(fig)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _make)
    return out_path

# --- Translation wrapper (uses google translate API endpoint or googletrans if installed) ---
async def translate_text(text: str, target_lang: str = "fa") -> str:
    if not text: return text
    # Prefer existing HTTP-based function to avoid googletrans dependency when possible
    encoded_text = quote(text)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={encoded_text}"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            headers = {'User-Agent': 'Mozilla/5.0'}
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    try:
                        data = await response.json(content_type=None)
                        if isinstance(data, list) and data and isinstance(data[0], list):
                            translated_text = "".join(segment[0] for segment in data[0] if isinstance(segment, list) and segment and isinstance(segment[0], str))
                            return translated_text.strip() if translated_text else text
                    except Exception:
                        pass
    except Exception:
        pass
    # Fallback to googletrans if available
    if HAS_GOOGLETRANS:
        try:
            gt = GoogleTranslator()
            res = gt.translate(text, dest=target_lang)
            return getattr(res, 'text', text)
        except Exception as e:
            logging.warning(f"googletrans fallback failed: {e}")
    return text

# --- Text to speech wrapper (gTTS) ---
async def text_to_speech_and_send(client, chat_id: int, text: str):
    if not HAS_GTTs:
        await client.send_message(chat_id, "⚠️ قابلیت تبدیل متن به صدا فعال نیست (gTTS نصب نشده).")
        return
    # Save to temp file and send
    tmp = safe_filename(prefix='tts_', suffix='.mp3')
    try:
        def _save():
            tts = gTTS(text=text, lang='fa', slow=False)
            tts.save(tmp)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _save)
        await client.send_audio(chat_id, tmp)
    except Exception as e:
        logging.error(f"TTS error: {e}")
        try:
            await client.send_message(chat_id, f"⚠️ خطا در تولید صدا: {type(e).__name__}")
        except Exception: pass
    finally:
        try:
            if os.path.exists(tmp): os.remove(tmp)
        except: pass

# End of part 1
# ادامه در پیام بعدی: ثبت هندلرهای پایه، کنترل مودها، پیاده‌سازی دستورات مشابه self.txt و اتصال به start_bot_instance و Flask.
# --- Part 2: Handlers, mode controllers, list management, entertainment, admin tools ---

# --- Utilities to initialize in-memory state from DB per user ---
async def init_user_state(user_id: int):
    """بارگذاری تنظیمات کاربر به متغیرهای حافظه‌ای برای عملکرد سریع"""
    settings = await load_user_settings(user_id)
    # modes
    TEXT_MODES[user_id] = {k: (v == "on" or v == "On" or v == True) for k, v in settings.get("modes", {}).items()}
    TIME_MODES[user_id] = {k: (v == "on" or v == "On" or v == True) for k, v in settings.get("time_modes", {}).items()}
    LISTS[user_id] = settings.get("lists", {"enemy": [], "crash": []})
    USER_FONT_CHOICES[user_id] = settings.get("font_style", "stylized")
    CLOCK_STATUS[user_id] = not settings.get("disable_clock", False)
    CUSTOM_SECRETARY_MESSAGES[user_id] = settings.get("secretary_message", DEFAULT_SECRETARY_MESSAGE)
    AUTO_REACTION_TARGETS[user_id] = settings.get("auto_reactions", {})
    AUTO_TRANSLATE_TARGET[user_id] = settings.get("auto_translate", None)
    # ensure other defaults
    ENEMY_REPLIES.setdefault(user_id, [])
    FRIEND_REPLIES.setdefault(user_id, [])
    ENEMY_LIST[user_id] = set(LISTS[user_id].get("enemy", []))
    FRIEND_LIST.setdefault(user_id, set())
    MUTED_USERS.setdefault(user_id, set())
    USERS_REPLIED_IN_SECRETARY.setdefault(user_id, set())
    BOLD_MODE_STATUS.setdefault(user_id, False)
    AUTO_SEEN_STATUS.setdefault(user_id, False)
    ANTI_LOGIN_STATUS.setdefault(user_id, False)
    COPY_MODE_STATUS.setdefault(user_id, False)
    TYPING_MODE_STATUS.setdefault(user_id, False)
    PLAYING_MODE_STATUS.setdefault(user_id, False)
    RECORD_VOICE_STATUS.setdefault(user_id, False)
    UPLOAD_PHOTO_STATUS.setdefault(user_id, False)
    WATCH_GIF_STATUS.setdefault(user_id, False)
    PV_LOCK_STATUS.setdefault(user_id, False)

async def persist_user_state(user_id: int):
    """ذخیره تنظیمات متداول به DB"""
    if user_settings_collection is None:
        return
    try:
        settings = {
            "user_id": user_id,
            "font_style": USER_FONT_CHOICES.get(user_id, "stylized"),
            "disable_clock": not CLOCK_STATUS.get(user_id, True),
            "modes": {k: ("on" if v else "off") for k, v in TEXT_MODES.get(user_id, {}).items()},
            "time_modes": {k: ("on" if v else "off") for k, v in TIME_MODES.get(user_id, {}).items()},
            "lists": {"enemy": list(ENEMY_LIST.get(user_id, set())), "crash": LISTS.get(user_id, {}).get("crash", [])},
            "secretary_message": CUSTOM_SECRETARY_MESSAGES.get(user_id, DEFAULT_SECRETARY_MESSAGE),
            "auto_reactions": AUTO_REACTION_TARGETS.get(user_id, {}),
            "auto_translate": AUTO_TRANSLATE_TARGET.get(user_id, None),
            "updated_at": datetime.utcnow()
        }
        user_settings_collection.update_one({"user_id": user_id}, {"$set": settings}, upsert=True)
    except Exception as e:
        logging.error(f"persist_user_state error for {user_id}: {e}")

# --- Outgoing modifier extended (text modes from self.txt) ---
async def outgoing_text_modes(client, message):
    """ویرایش متن‌های ارسالی بر اساس مودهای متنی (hashtag, bold, italic, delete, code, underline, reverse, part, mention)"""
    user_id = client.me.id
    if not message.text or message.entities:
        return
    modes = TEXT_MODES.get(user_id, {})
    original = message.text
    new_text = original
    try:
        if modes.get("hashtag"):
            new_text = new_text.replace(" ", "_")
        if modes.get("bold"):
            if not (new_text.startswith("**") or new_text.startswith("__")):
                new_text = f"**{new_text}**"
        if modes.get("italic"):
            new_text = f"*{new_text}*"
        if modes.get("delete"):
            new_text = f"~~{new_text}~~"
        if modes.get("code"):
            new_text = f"`{new_text}`"
        if modes.get("underline"):
            new_text = f"__{new_text}__"
        if modes.get("reverse"):
            new_text = new_text[::-1]
        if modes.get("part"):
            # gradual typing visual; attempt to show progressive edits (cautious: may hit rate limits)
            if len(new_text) <= 1:
                pass
            else:
                # perform a fast progressive edit (limited to short texts)
                if len(new_text) <= 50:
                    try:
                        await message.edit(new_text)
                        await asyncio.sleep(0.1)
                    except Exception:
                        pass
        if modes.get("mention") and message.reply_to_message and message.reply_to_message.from_user:
            rid = message.reply_to_message.from_user.id
            new_text = f"[{new_text}](tg://openmessage?user_id={rid})"
        # spoiler ignored as Pyrogram handles entities differently; skipping complex spoiler creation
        if new_text != original:
            try:
                await message.edit(new_text, disable_web_page_preview=True)
            except MessageNotModified:
                pass
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except Exception as e:
                logging.debug(f"outgoing_text_modes edit failed: {e}")
    except Exception as e:
        logging.error(f"outgoing_text_modes error: {e}", exc_info=True)

# --- Incoming handlers: enemy/friend, secretary, pv_lock, auto_reaction, auto_seen (integration) ---
async def enemy_auto_reply(client, message):
    user_id = client.me.id
    if not message.from_user:
        return
    if not ENEMY_ACTIVE.get(user_id, False):
        return
    if message.from_user.id in ENEMY_LIST.get(user_id, set()):
        replies = ENEMY_REPLIES.get(user_id, [])
        if replies:
            text = random.choice(replies)
            try:
                await message.reply_text(text, quote=True)
            except Exception as e:
                logging.debug(f"enemy_auto_reply failed: {e}")

async def friend_auto_reply(client, message):
    user_id = client.me.id
    if not message.from_user:
        return
    if not FRIEND_ACTIVE.get(user_id, False):
        return
    if message.from_user.id in FRIEND_LIST.get(user_id, set()):
        replies = FRIEND_REPLIES.get(user_id, [])
        if replies:
            text = random.choice(replies)
            try:
                await message.reply_text(text, quote=True)
            except Exception as e:
                logging.debug(f"friend_auto_reply failed: {e}")

async def secretary_handler_incoming(client, message):
    owner = client.me.id
    if message.chat.type == ChatType.PRIVATE and SECRETARY_MODE_STATUS.get(owner, False):
        if message.from_user and not message.from_user.is_bot and not message.from_user.is_self:
            target = message.from_user.id
            replied = USERS_REPLIED_IN_SECRETARY.setdefault(owner, set())
            if target not in replied:
                txt = CUSTOM_SECRETARY_MESSAGES.get(owner, DEFAULT_SECRETARY_MESSAGE)
                try:
                    await message.reply_text(txt, quote=True)
                    replied.add(target)
                except Exception as e:
                    logging.debug(f"secretary reply failed: {e}")

async def pv_lock_delete(client, message):
    owner = client.me.id
    if PV_LOCK_STATUS.get(owner, False) and message.chat.type == ChatType.PRIVATE:
        try:
            await message.delete()
        except Exception:
            pass

async def auto_reaction_on_message(client, message):
    user_id = client.me.id
    if not message.from_user:
        return
    emoji = AUTO_REACTION_TARGETS.get(user_id, {}).get(message.from_user.id)
    if emoji:
        try:
            await client.send_reaction(message.chat.id, message.id, emoji)
        except Exception:
            pass

async def auto_mark_seen(client, message):
    user_id = client.me.id
    if message.chat.type == ChatType.PRIVATE and AUTO_SEEN_STATUS.get(user_id, False):
        try:
            await client.read_chat_history(message.chat.id)
        except Exception:
            pass

# --- Handlers for list management and commands similar to self.txt (addin/del/list) ---
async def cmd_add_enemy(client, message):
    user_id = client.me.id
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.edit_text("⚠️ برای افزودن به لیست دشمن، روی پیام کاربر ریپلای کنید.")
        return
    target = message.reply_to_message.from_user.id
    ENEMY_LIST.setdefault(user_id, set()).add(target)
    # persist
    LISTS.setdefault(user_id, {})["enemy"] = list(ENEMY_LIST[user_id])
    await persist_user_state(user_id)
    await message.edit_text(f"✅ کاربر `{target}` به لیست دشمن اضافه شد.")

async def cmd_del_enemy(client, message):
    user_id = client.me.id
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.edit_text("⚠️ برای حذف از لیست دشمن، روی پیام کاربر ریپلای کنید.")
        return
    target = message.reply_to_message.from_user.id
    enemies = ENEMY_LIST.get(user_id, set())
    if target in enemies:
        enemies.remove(target)
        LISTS.setdefault(user_id, {})["enemy"] = list(enemies)
        await persist_user_state(user_id)
        await message.edit_text(f"✅ کاربر `{target}` از لیست دشمن حذف شد.")
    else:
        await message.edit_text("ℹ️ کاربر در لیست دشمن نبود.")

async def cmd_list_enemy(client, message):
    user_id = client.me.id
    enemies = ENEMY_LIST.get(user_id, set())
    if not enemies:
        await message.edit_text("ℹ️ لیست دشمن خالی است.")
        return
    txt = "**📋 لیست دشمنان:**\n"
    for eid in enemies:
        try:
            u = await client.get_users(eid)
            display = u.first_name or str(eid)
        except Exception:
            display = str(eid)
        txt += f"- {display} (`{eid}`)\n"
    await message.edit_text(txt)

async def cmd_add_crash(client, message):
    user_id = client.me.id
    if not message.reply_to_message:
        await message.edit_text("⚠️ برای افزودن به کراش باید روی پیام یا کاربر ریپلای کنید.")
        return
    target = message.reply_to_message.from_user.id
    js_crash = LISTS.setdefault(user_id, {}).setdefault("crash", [])
    if target in js_crash:
        await message.edit_text("ℹ️ کاربر در لیست کراش از قبل وجود دارد.")
        return
    js_crash.append(target)
    await persist_user_state(user_id)
    await message.edit_text(f"✅ کاربر `{target}` به لیست کراش اضافه شد.")

async def cmd_del_crash(client, message):
    user_id = client.me.id
    if not message.reply_to_message:
        await message.edit_text("⚠️ برای حذف از کراش باید روی پیام یا کاربر ریپلای کنید.")
        return
    target = message.reply_to_message.from_user.id
    js_crash = LISTS.setdefault(user_id, {}).setdefault("crash", [])
    if target in js_crash:
        js_crash.remove(target)
        await persist_user_state(user_id)
        await message.edit_text(f"✅ کاربر `{target}` از لیست کراش حذف شد.")
    else:
        await message.edit_text("ℹ️ کاربر در لیست کراش موجود نبود.")

async def cmd_list_crash(client, message):
    user_id = client.me.id
    js_crash = LISTS.get(user_id, {}).get("crash", [])
    if not js_crash:
        await message.edit_text("ℹ️ لیست کراش خالی است.")
        return
    txt = "📝 لیست کراش:\n"
    for i in js_crash:
        txt += f"- `{i}`\n"
    await message.edit_text(txt)

# --- Entertainment: dice, bowling, fun, heart (mimic self.txt behavior) ---
async def cmd_dice(client, message):
    chat_id = message.chat.id
    txt = message.text.strip()
    if txt == "تاس":
        # simple single dice
        await client.send_dice(chat_id, emoji="🎲")
        try:
            await message.delete()
        except: pass
    else:
        m = re.match(r"^تاس (\d+)$", txt)
        if m:
            try:
                target = int(m.group(1))
                if 1 <= target <= 6:
                    attempts = 0
                    while attempts < 20:
                        res = await client.send_dice(chat_id, emoji="🎲")
                        attempts += 1
                        if getattr(res, "dice", None) and res.dice.value == target:
                            break
                        await asyncio.sleep(1)
                    try:
                        await message.delete()
                    except: pass
                else:
                    await message.edit_text("⚠️ عدد تاس باید بین ۱ تا ۶ باشد.")
            except Exception:
                await message.edit_text("⚠️ فرمت دستور نامعتبر. مثال: `تاس` یا `تاس ۶`")

async def cmd_bowling(client, message):
    chat_id = message.chat.id
    attempts = 0
    while attempts < 10:
        res = await client.send_dice(chat_id, emoji="🎳")
        attempts += 1
        if getattr(res, "dice", None) and res.dice.value == 10:
            break
        await asyncio.sleep(1)
    try:
        await message.delete()
    except: pass

async def cmd_fun(event_client, message):
    # pattern: فان X
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        await message.edit_text("⚠️ مثال استفاده: فان love یا فان ocLock")
        return
    arg = parts[1].strip().lower()
    if arg == "love":
        emoticons = ['🤍','🖤','💜','💙','💚','💛','🧡','❤️','🤎','💖']
    elif arg == "oclock":
        emoticons = ['🕐','🕑','🕒','🕓','🕔','🕕','🕖','🕗','🕘','🕙','🕚','🕛']
    elif arg == "star":
        emoticons = ['💥','⚡️','✨','🌟','⭐️','💫']
    elif arg == "snow":
        emoticons = ['❄️','☃️','⛄️']
    else:
        emoticons = list(arg)[:10]
    random.shuffle(emoticons)
    for emoji in emoticons:
        try:
            await asyncio.sleep(1)
            await message.edit(emoji)
        except Exception:
            pass

async def cmd_heart(client, message):
    try:
        for x in range(1,4):
            for i in range(1,11):
                await message.edit('➣ ' + str(x) + ' ❦' * i + ' | ' + str(10 * i) + '%')
                await asyncio.sleep(0.2)
    except Exception:
        pass

# --- Admin tools: tagall, tagadmins, clean (delete), info, status ---
async def cmd_tagall(client, message):
    if not message.chat or not getattr(message.chat, "id", None):
        return
    chat = await client.get_chat(message.chat.id)
    mentions = '✅ اعضای آنلاین گروه:\n'
    try:
        async for member in client.get_chat_members(message.chat.id, limit=200):
            name = member.user.first_name if member.user and member.user.first_name else str(member.user.id)
            mentions += f"[{name}](tg://user?id={member.user.id})\n"
        await message.reply_text(mentions)
        await message.delete()
    except Exception as e:
        await message.edit_text(f"⚠️ خطا در تگ کردن: {type(e).__name__}")

async def cmd_tagadmins(client, message):
    try:
        mentions = '⚡️ ادمین‌های گروه:\n'
        async for member in client.get_chat_members(message.chat.id, filter="administrators"):
            name = member.user.first_name if member.user and member.user.first_name else str(member.user.id)
            mentions += f"[{name}](tg://user?id={member.user.id})\n"
        await message.reply_text(mentions)
        await message.delete()
    except Exception as e:
        await message.edit_text(f"⚠️ خطا: {type(e).__name__}")

async def cmd_clean(client, message):
    # pattern: clean N or حذف N
    m = re.match(r'^(clean|حذف) (\d+)$', message.text)
    if not m:
        await message.edit_text("⚠️ فرمت: حذف 10")
        return
    n = int(m.group(2))
    try:
        deleted = 0
        async for msg in client.get_chat_history(message.chat.id, limit=n+5):
            if msg.from_user and msg.from_user.id == client.me.id:
                try:
                    await client.delete_messages(message.chat.id, msg.id)
                    deleted += 1
                except Exception:
                    pass
        await message.edit_text(f"✅ {deleted} پیام حذف شد.")
    except Exception as e:
        await message.edit_text(f"⚠️ خطا در حذف پیام‌ها: {type(e).__name__}")

async def cmd_info(client, message):
    target = None
    if message.is_reply:
        target = message.reply_to_message.from_user.id
    else:
        parts = message.text.split()
        if len(parts) == 2:
            try:
                target = int(parts[1])
            except:
                target = None
    if not target:
        if message.chat.type == ChatType.PRIVATE:
            target = message.chat.id
        else:
            await message.edit_text("⚠️ برای دریافت اطلاعات، آی‌دی یا ریپلای لازم است.")
            return
    try:
        full = await client.get_users(target)
        about = ""
        try:
            full_info = await client.invoke(functions.users.GetFullUser(id=await client.resolve_peer(target)))
            about = getattr(full_info.full_user, "about", "") or ""
        except Exception:
            about = ""
        photos = await client.get_profile_photos(target, limit=1)
        txt = f"اطلاعات کاربر:\nشناسه: `{target}`\nنام: {full.first_name or ''}\nنام خانوادگی: {full.last_name or ''}\nنام کاربری: @{full.username if getattr(full, 'username', None) else ''}\nبیو: {about}\n"
        if photos:
            await client.send_photo(message.chat.id, photos[0].file_id, caption=txt)
            await message.delete()
        else:
            await message.edit_text(txt)
    except Exception as e:
        await message.edit_text(f"⚠️ خطا در دریافت اطلاعات: {type(e).__name__}")

async def cmd_status(client, message):
    # aggregate basic stats similar to self.txt status
    private_chats = bots = groups = broadcast_channels = 0
    async for dialog in client.get_dialogs(limit=500):
        if dialog.chat.type == ChatType.PRIVATE:
            private_chats += 1
            if dialog.chat.is_bot:
                bots += 1
        elif dialog.chat.type == ChatType.SUPERGROUP or dialog.chat.type == ChatType.GROUP:
            groups += 1
        elif dialog.chat.type == ChatType.CHANNEL:
            broadcast_channels += 1
    txt = f"وضعیت:\nچت‌های خصوصی: {private_chats}\nگروه‌ها: {groups}\nکانال‌ها: {broadcast_channels}\nبات‌ها: {bots}"
    await message.edit_text(txt)

# --- Translation command (reply) and TTS (if available) ---
async def cmd_translate_reply(client, message):
    if not message.reply_to_message or not message.reply_to_message.text:
        await message.edit_text("⚠️ برای ترجمه باید روی پیام ریپلای کنید.")
        return
    text = message.reply_to_message.text
    translated = await translate_text(text, "fa")
    try:
        await message.edit_text(translated)
    except MessageNotModified:
        pass
    except Exception:
        try:
            await message.reply_text(translated, quote=True)
            await message.delete()
        except Exception:
            pass

async def cmd_tts_reply(client, message):
    if not message.reply_to_message or not message.reply_to_message.text:
        await message.edit_text("⚠️ برای تبدیل به صدا، روی پیام ریپلای کنید.")
        return
    text = message.reply_to_message.text
    await text_to_speech_and_send(client, message.chat.id, text)

# --- Font listing and choosing (already partially present) ---
async def cmd_font_list(client, message):
    # reuse FONT_KEYS_ORDER and FONT_DISPLAY_NAMES
    parts = []
    current = "📜 لیست فونت‌های موجود:\n"
    for i, key in enumerate(FONT_KEYS_ORDER):
        line = f"{i+1}. {FONT_DISPLAY_NAMES.get(key, key)}: {stylize_time('12:34', key)}\n"
        if len(current) + len(line) > 4090:
            parts.append(current)
            current = ""
        current += line
    parts.append(current + "\nبرای انتخاب: فونت [عدد]")
    for i, p in enumerate(parts):
        if i == 0:
            await message.edit_text(p)
        else:
            await client.send_message(message.chat.id, p)
            await asyncio.sleep(0.3)

async def cmd_font_choose(client, message):
    m = re.match(r"^فونت (\d+)$", message.text.strip())
    if not m:
        await message.edit_text("⚠️ فرمت: فونت 3")
        return
    idx = int(m.group(1)) - 1
    if idx < 0 or idx >= len(FONT_KEYS_ORDER):
        await message.edit_text(f"⚠️ عدد فونت نامعتبر. از 1 تا {len(FONT_KEYS_ORDER)}.")
        return
    user_id = client.me.id
    USER_FONT_CHOICES[user_id] = FONT_KEYS_ORDER[idx]
    await persist_user_state(user_id)
    await message.edit_text(f"✅ فونت ساعت به {FONT_DISPLAY_NAMES.get(FONT_KEYS_ORDER[idx])} تغییر کرد.")
    # immediate update of profile if CLOCK active
    if CLOCK_STATUS.get(user_id, False) and not COPY_MODE_STATUS.get(user_id, False):
        try:
            me = await client.get_me()
            base_name_match = re.match(r"^(.*?)\s*[" + re.escape(ALL_CLOCK_CHARS) + r":\s]*$", me.first_name or "")
            base = base_name_match.group(1).strip() if base_name_match else (me.username or f"User_{user_id}")
            tehran_time = datetime.now(TEHRAN_TIMEZONE).strftime("%H:%M")
            styl = stylize_time(tehran_time, USER_FONT_CHOICES[user_id])
            new_name = f"{base} {styl}"[:64]
            await client.update_profile(first_name=new_name)
        except Exception as e:
            logging.debug(f"Immediate profile update on font change failed: {e}")

# --- Clock control functions (time in name/bio/profile) ---
async def apply_clock_to_profile(client, user_id: int):
    """Set profile name and/or bio/photo based on TIME_MODES and USER_FONT_CHOICES"""
    try:
        me = await client.get_me()
        current_name = me.first_name or ""
        base_name_match = re.match(r"^(.*?)\s*[" + re.escape(ALL_CLOCK_CHARS) + r":\s]*$", current_name)
        base = base_name_match.group(1).strip() if base_name_match else (me.username or f"User_{user_id}")

        font = USER_FONT_CHOICES.get(user_id, "stylized")
        now = datetime.now(TEHRAN_TIMEZONE).strftime("%H:%M")
        styl = stylize_time(now, font)

        if TIME_MODES.get(user_id, {}).get("timename"):
            new_name = f"{base} {styl}"[:64]
            await client.update_profile(first_name=new_name)
        else:
            # restore base name if clock was removed
            if CLOCK_STATUS.get(user_id, False) is False:
                await client.update_profile(first_name=base[:64])

        if TIME_MODES.get(user_id, {}).get("timebio"):
            try:
                await client.invoke(functions.account.UpdateProfile(about=f"❦ {styl}"))
            except Exception:
                try:
                    await client.update_profile(bio=f"❦ {styl}")
                except Exception:
                    pass

        if TIME_MODES.get(user_id, {}).get("timeprofile") and HAS_MATPLOTLIB and HAS_NUMPY:
            # create clock image and upload as profile photo
            h, m, s = map(int, datetime.now(TEHRAN_TIMEZONE).strftime("%H:%M:%S").split(":"))
            bg = os.path.join(os.getcwd(), "clock_background.jpg")
            outp = safe_filename(prefix="clock_", suffix=".jpg")
            try:
                await make_clock_image(h, m, s, bg, outp)
                # pyrogram: set_profile_photo
                try:
                    # delete previous photos to avoid duplicates
                    photos = await client.get_chat_photos("me")
                    if photos:
                        file_ids = [p.file_id async for p in client.get_chat_photos("me")]
                        try:
                            await client.delete_profile_photos(file_ids)
                        except Exception:
                            pass
                    await client.set_profile_photo(photo=outp)
                except Exception:
                    pass
            finally:
                try:
                    if os.path.exists(outp): os.remove(outp)
                except:
                    pass

    except Exception as e:
        logging.debug(f"apply_clock_to_profile error: {e}")

# --- Command router: toggle controller extended for modes from self.txt ---
async def toggle_extended(client, message):
    user_id = client.me.id
    cmd = message.text.strip()
    try:
        # textual mode toggles like "hashtag on/off" in Persian mapping
        mapping_on = {
            "hashtag روشن": ("hashtag", True),
            "بولد روشن": ("bold", True),
            "ایتالیک روشن": ("italic", True),
            "delete روشن": ("delete", True),
            "code روشن": ("code", True),
            "زیرخط روشن": ("underline", True),
            "معکوس روشن": ("reverse", True),
            "part روشن": ("part", True),
            "mention روشن": ("mention", True),
            "اسپویلر روشن": ("spoiler", True)
        }
        mapping_off = {k.replace("روشن", "خاموش"): (v[0], False) for k, v in mapping_on.items()}
        if cmd in mapping_on or cmd in mapping_off:
            key, val = (mapping_on.get(cmd) or mapping_off.get(cmd))
            TEXT_MODES.setdefault(user_id, {})[key] = val
            await persist_user_state(user_id)
            await message.edit_text(f"✅ مود {key} {'فعال' if val else 'غیرفعال'} شد.")
            return
        # time mode toggles (.timename on/off / .timebio ...)
        tm_map = {
            "timename on": ("timename", True),
            "timename off": ("timename", False),
            "timebio on": ("timebio", True),
            "timebio off": ("timebio", False),
            "timeprofile on": ("timeprofile", True),
            "timeprofile off": ("timeprofile", False),
            "timecrash on": ("timecrash", True),
            "timecrash off": ("timecrash", False),
        }
        # accept Persian forms like ".timename on" or "timename on"
        normalized = cmd.replace(".", "").lower()
        if normalized in tm_map:
            key, val = tm_map[normalized]
            TIME_MODES.setdefault(user_id, {})[key] = val
            await persist_user_state(user_id)
            await message.edit_text(f"✅ تنظیم زمان ({key}) {'فعال' if val else 'غیرفعال'} شد.")
            # apply immediately if turning on
            if val:
                await apply_clock_to_profile(client, user_id)
            return
        # other simple toggles: typing/game/voice/video/sticker
        simple_map = {
            "تایپ روشن": ("typing", True), "تایپ خاموش": ("typing", False),
            "بازی روشن": ("game", True), "بازی خاموش": ("game", False),
            "ضبط ویس روشن": ("voice", True), "ضبط ویس خاموش": ("voice", False),
            "عکس روشن": ("photo", True), "عکس خاموش": ("photo", False),
            "گیف روشن": ("gif", True), "گیف خاموش": ("gif", False),
        }
        if cmd in simple_map:
            k, v = simple_map[cmd]
            if k == "typing":
                TYPING_MODE_STATUS[user_id] = v
            elif k == "game":
                PLAYING_MODE_STATUS[user_id] = v
            elif k == "voice":
                RECORD_VOICE_STATUS[user_id] = v
            elif k == "photo":
                UPLOAD_PHOTO_STATUS[user_id] = v
            elif k == "gif":
                WATCH_GIF_STATUS[user_id] = v
            await message.edit_text(f"✅ تنظیم {k} {'فعال' if v else 'غیرفعال'} شد.")
            return
        # fallback: command not recognized by this extended toggler
        await message.edit_text("⚠️ دستور شناخته نشد.")
    except Exception as e:
        logging.error(f"toggle_extended error: {e}")
        try:
            await message.edit_text("⚠️ خطایی در پردازش دستور رخ داد.")
        except:
            pass

# --- Register handlers into client inside start_bot_instance (we will call add_handlers there) ---
def register_feature_handlers(client):
    """ثبت هندلرهای سطح بالا در client؛ این تابع در start_bot_instance فراخوانی می‌شود."""
    user_id = None
    # We'll wrap handlers into MessageHandler objects when start_bot_instance has a real client instance
    # This is just placeholder; actual registration happens later where we have user_id
    pass

# End of Part 2
# Next: Part 3 will contain: start_bot_instance enhancements to load settings and register all handlers with correct filters,
# plus Flask route handlers integration and loop startup orchestration. (I will now continue with the combined finalization.)
# --- Part 3: ثبت هندلرها داخل start_bot_instance و نهایی‌سازی راه‌اندازی ---
# این بخش دستورات فارسی و هندلرهای مربوط به قابلیت‌هایی که از self.txt خواستی را ثبت می‌کند.
# توجه: این تابع باید در همان ماژولی که start_bot_instance تعریف شده فراخوانی شود.
# اگر در فایل اصلی (که قبلاً بخش بزرگی از start_bot_instance داشت) نسخه دیگری از start_bot_instance موجود است،
# مطمئن شو که این بخش را با بخش قبلی ادغام کنی (یا جایگزین مناسب انجام دهی) — این نسخه طوری نوشته شده که کمترین تداخلی داشته باشد.

def _make_cmd_filter(user_id):
    """کمک‌کننده برای ساخت فیلتر دستورات کاربر (فقط پیام‌های خود کاربر)."""
    return filters.me & filters.user(user_id) & filters.text

def register_all_feature_handlers_for_client(client: Client, user_id: int):
    """
    ثبت همه‌ی هندلرهای مربوط به قابلیت‌های اضافه‌شده برای یک client مشخص.
    این تابع هنگام راه‌اندازی هر session (در start_bot_instance) باید فراخوانی شود.
    """
    # Helper to add handler safely
    def add(handler_fn, flt, group=0):
        try:
            client.add_handler(MessageHandler(handler_fn, flt), group=group)
        except Exception as e:
            logging.error(f"Failed to add handler {handler_fn.__name__}: {e}")

    # پایه: حالت‌های خروجی (ویرایش متن ارسالی) — گروه -1 (قبل از بقیه)
    out_filter = filters.text & filters.me & filters.user(user_id) & ~filters.via_bot & ~filters.service
    add(outgoing_text_modes, out_filter, group=-1)

    # PV lock (در گروه -5 در کد اصلی هم بود) — حذف پیام‌های خصوصی ورودی
    add(pv_lock_delete, filters.private & ~filters.me & ~filters.user(user_id) & ~filters.bot & ~filters.service, group=-5)

    # Auto seen (group -4)
    add(auto_mark_seen, filters.private & ~filters.me & ~filters.user(user_id), group=-4)

    # General incoming manager (mute, reactions, etc.) - اگر تابع incoming_message_manager در فایل اصلی وجود دارد،
    # آن را نگه دارید؛ در غیر این صورت از auto_reaction_on_message و دیگر هندلرهای جزئی استفاده کنید.
    # اینجا ما هندلرهای ماژولار را ثبت می‌کنیم:
    add(auto_reaction_on_message, filters.all & ~filters.me & ~filters.user(user_id) & ~filters.service, group=-3)
    add(enemy_auto_reply, filters.all & ~filters.me & ~filters.user(user_id) & ~filters.service, group=1)
    add(friend_auto_reply, filters.all & ~filters.me & ~filters.user(user_id) & ~filters.service, group=1)
    add(secretary_handler_incoming, filters.private & ~filters.me & ~filters.user(user_id) & ~filters.service, group=1)

    # Commands (group 0) - mapping commands to functions
    cmd_base = _make_cmd_filter(user_id)

    # راهنما
    add(help_controller, cmd_base & filters.regex("^راهنما$"))

    # toggle_extended handles many toggles (typing, game, text modes, time modes)
    add(toggle_extended, cmd_base & filters.regex(r".*(روشن|خاموش|timename|timebio|timeprofile|timecrash).*", flags=re.IGNORECASE))

    # translation (reply)
    add(cmd_translate_reply, cmd_base & filters.reply & filters.regex(r"^ترجمه$"))

    # tts (نام پیشنهادی: تبدیل پیام ریپلای‌شده به صدا)
    add(cmd_tts_reply, cmd_base & filters.reply & filters.regex(r"^(tts|صوت|ویس)$"))

    # add/del/list enemy
    add(cmd_add_enemy, cmd_base & filters.reply & filters.regex(r"^(تنظیم دشمن|addenemy)$"))
    add(cmd_del_enemy, cmd_base & filters.reply & filters.regex(r"^(حذف دشمن|delenemy)$"))
    add(cmd_list_enemy, cmd_base & filters.regex(r"^(لیست دشمن|listenemy)$"))

    # crash list
    add(cmd_add_crash, cmd_base & filters.reply & filters.regex(r"^(addcrash|افزودن کراش)$"))
    add(cmd_del_crash, cmd_base & filters.reply & filters.regex(r"^(delcrash|حذف کراش)$"))
    add(cmd_list_crash, cmd_base & filters.regex(r"^(listcrash|لیست کراش)$"))

    # entertainment
    add(cmd_dice, cmd_base & filters.regex(r"^(تاس|تاس \d+)$"))
    add(cmd_bowling, cmd_base & filters.regex(r"^(بولینگ|bowling)$"))
    add(cmd_fun, cmd_base & filters.regex(r"^(فان|fun) "))
    add(cmd_heart, cmd_base & filters.regex(r"^(قلب|heart)$"))

    # admin tools
    add(cmd_tagall, cmd_base & filters.regex(r"^(tagall|تگ)$"))
    add(cmd_tagadmins, cmd_base & filters.regex(r"^(tagadmins|تگ ادمین ها)$"))
    add(cmd_clean, cmd_base & filters.regex(r"^(clean|حذف) \d+$"))
    add(cmd_info, cmd_base & filters.regex(r"^(info|اطلاعات)"))
    add(cmd_status, cmd_base & filters.regex(r"^(status|وضعیت)$"))

    # font commands
    add(cmd_font_list, cmd_base & filters.regex(r"^فونت$"))
    add(cmd_font_choose, cmd_base & filters.regex(r"^فونت \d+$"))

    # translate reply and save message (ذخیره)
    add(cmd_translate_reply, cmd_base & filters.reply & filters.regex(r"^ترجمه$"))
    add(save_message_controller, cmd_base & filters.reply & filters.regex(r"^ذخیره$"))

    # copy profile commands (keep original copy_profile_controller if present)
    add(copy_profile_controller, cmd_base & filters.regex(r"^(کپی روشن|کپی خاموش)$"))

    # repeat and delete messages controllers (if present in main code they will run)
    add(repeat_message_controller, cmd_base & filters.reply & filters.regex(r"^تکرار \d+(?: \d+)?$"))
    add(delete_messages_controller, cmd_base & filters.regex(r"^(حذف(?: \d+)?|حذف همه)$"))

    # Additional mappings for translation to languages shortcuts
    add(set_translation_controller, cmd_base & filters.regex(r"^(ترجمه [a-z]{2}(?:-[a-z]{2})?|ترجمه خاموش|چینی روشن|چینی خاموش|روسی روشن|روسی خاموش|انگلیسی روشن|انگلیسی خاموش)$", flags=re.IGNORECASE))

    # Block/unblock, mute/unmute, auto reaction controllers if present
    add(block_unblock_controller, cmd_base & filters.reply & filters.regex(r"^(بلاک روشن|بلاک خاموش)$"))
    add(mute_unmute_controller, cmd_base & filters.reply & filters.regex(r"^(سکوت روشن|سکوت خاموش)$"))
    add(auto_reaction_controller, cmd_base & filters.reply & filters.regex(r"^(ریاکشن .*|ریاکشن خاموش)$"))

    # secretary message setter
    add(set_secretary_message_controller, cmd_base & filters.regex(r"^منشی متن(?: |$)(.*)", flags=re.DOTALL | re.IGNORECASE))
    add(pv_lock_controller, cmd_base & filters.regex(r"^(پیوی قفل|پیوی باز)$"))

    # help fallback: if a new command was not recognized, notify user (handled by earlier controllers)

    logging.info(f"Feature handlers registered for user {user_id}.")


# --- Enhanced start_bot_instance wrapper (invokes register_all_feature_handlers_for_client) ---
# If your original start_bot_instance exists, you can insert a call to register_all_feature_handlers_for_client(client, user_id)
# right after the client has started and user_id was obtained. For clarity, below is a minimal snippet to show where:

async def start_bot_instance_enhanced(session_string: str, phone: str, font_style: str, disable_clock: bool = False):
    """
    نسخهٔ تقویت‌شدهٔ راه‌اندازی instance که علاوه بر کارهای قبلی،
    تنظیمات کاربر را بارگذاری و هندلرهای جدید را ثبت می‌کند.
    """
    safe_phone_name = re.sub(r'\W+', '', phone)
    client_name = f"bot_session_{safe_phone_name}"
    client = Client(client_name, api_id=API_ID, api_hash=API_HASH, session_string=session_string)
    user_id = None
    try:
        logging.info(f"[EnhancedStart] Starting client for {phone}...")
        await client.start()
        me = await client.get_me()
        user_id = me.id
        logging.info(f"[EnhancedStart] Client started for user {user_id} ({me.first_name or me.username or phone}).")

    except Exception as e:
        logging.error(f"[EnhancedStart] Failed to start client for {phone}: {e}", exc_info=True)
        try:
            if client.is_connected:
                await client.stop()
        except:
            pass
        return

    # Ensure single instance per user_id
    if user_id in ACTIVE_BOTS:
        old_client, tasks = ACTIVE_BOTS.pop(user_id)
        for t in tasks:
            try:
                t.cancel()
            except:
                pass
        try:
            if old_client and old_client.is_connected:
                await old_client.stop()
        except:
            pass

    # Initialize user state from DB
    try:
        await init_user_state(user_id)
    except Exception as e:
        logging.error(f"[EnhancedStart] init_user_state error for {user_id}: {e}")

    # Register feature handlers
    try:
        register_all_feature_handlers_for_client(client, user_id)
    except Exception as e:
        logging.error(f"[EnhancedStart] register handlers failed for {user_id}: {e}")

    # Start background tasks (clock, anti-login, status actions) if not already started
    tasks = []
    try:
        tasks.append(asyncio.create_task(update_profile_clock(client, user_id)))
    except Exception as e:
        logging.error(f"[EnhancedStart] Could not start update_profile_clock: {e}")
    try:
        tasks.append(asyncio.create_task(anti_login_task(client, user_id)))
    except Exception as e:
        logging.error(f"[EnhancedStart] Could not start anti_login_task: {e}")
    try:
        tasks.append(asyncio.create_task(status_action_task(client, user_id)))
    except Exception as e:
        logging.error(f"[EnhancedStart] Could not start status_action_task: {e}")

    ACTIVE_BOTS[user_id] = (client, tasks)
    logging.info(f"[EnhancedStart] Instance for user {user_id} is running with features enabled.")

    # Persist initial user settings
    try:
        settings = {
            "font_style": USER_FONT_CHOICES.get(user_id, font_style),
            "disable_clock": disable_clock,
        }
        await persist_user_state(user_id)
    except Exception:
        pass

    # keep function alive while client runs (optional)
    # Do not block here; the client runs in the shared event loop.

# --- Finalization: Hook to integrate enhanced start into existing auto-login sequence ---
# If run_asyncio_loop earlier reads from DB and schedules start_bot_instance tasks,
# change it to schedule start_bot_instance_enhanced instead for new sessions:
#
#   EVENT_LOOP.create_task(start_bot_instance_enhanced(session_string, phone, font_style, disable_clock))
#
# Also, when send_code_task/sign_in_task/check_password_task finish exporting a session string,
# schedule start_bot_instance_enhanced instead of the original start_bot_instance to ensure features are active.

# --- Main run orchestration (if you want to use this merged file as entry point) ---
if __name__ == "__main__":
    logging.info("========================================")
    logging.info(" Starting Enhanced Telegram Self Bot... ")
    logging.info("========================================")

    # Start asyncio loop in background thread
    loop_thread = Thread(target=run_asyncio_loop, name="AsyncioLoopThread", daemon=True)
    loop_thread.start()

    # Start Flask server (this is the same run_flask defined earlier)
    run_flask()

    # After Flask stops, signal loop to stop
    if loop_thread.is_alive() and EVENT_LOOP.is_running():
        EVENT_LOOP.call_soon_threadsafe(EVENT_LOOP.stop)

    loop_thread.join(timeout=15)
    if mongo_client:
        try:
            mongo_client.close()
        except Exception as e:
            logging.error(f"Error closing mongo client: {e}")

    logging.info("Enhanced self bot stopped.")
