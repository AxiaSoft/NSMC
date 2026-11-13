#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=============================================================================
🤖 ربات هوشمند ضد رید و محافظت از سوپرگروه تلگرام (Pyrogram) — نسخه ۴
=============================================================================
هدف:
- محافظت کامل از سوپرگروه در برابر موج بات‌ها، ریدها (Raids) و حساب‌های جعلی
- ارسال پیام خوش‌آمد با کپچای شیشه‌ای و اخراج (Kick بدون بن) در صورت عدم تأیید
- ثبت گزارش افزودن عضو توسط کاربران و هشدار در صورت فراتر رفتن از سقف روزانه
- مرکز مدیریت اعضا در پیوی اونر: بن و آزادسازی اعضای گروه بدون مراجعه به گروه
- دستور اضطراری /panic جهت ابطال سریع لینک دعوت قبلی و صدور لینک جدید
- عملیات /sweep جهت بن دائمی اعضایی که در بازه تعیین‌شده کپچا را حل نکرده‌اند
- سیاست «سکوت در گروه»: لاگ آنلاین/آفلاین شدن ربات فقط و فقط به پیوی اونر می‌رود
- پیکربندی زنده از طریق منوهای شیشه‌ای و فایل config.json بدون نیاز به ری‌استارت

تغییرات نسخه ۴.۰.۰:
1) لاگ وضعیت چرخه حیات ربات (آنلاین/آفلاین/کرش) دیگر هرگز به گروه یا کانال لاگ
   ارسال نمی‌شود و تنها در پیوی اونر (admin_ids) نمایش داده می‌شود.
2) ارسال سایر لاگ‌های امنیتی به کانال/گروه لاگ به صورت پیش‌فرض خاموش است و از
   منوی «🔔 لاگ و اعلان‌ها» قابل کنترل است؛ همچنین اگر log_channel_id برابر با یکی
   از گروه‌های محافظت‌شده باشد، ربات به صورت سخت‌گیرانه از ارسال لاگ به آن خودداری می‌کند.
3) ماژول جدید «🚫 مدیریت اعضا»: بن/آزادسازی اعضای گروه از پیوی با آیدی عددی،
   یوزرنیم، فوروارد پیام کاربر، لیست اعضای تأیید نشده و لیست بن‌شده‌های گروه.
4) بازطراحی منوها: صفحه‌بندی لیست‌ها، دکمه بن در گزارش‌ها، منوی راهنما، نمایش
   آپ‌تایم، وضعیت لحظه‌ای ماژول‌ها در منوی اصلی و تأییدیه برای عملیات مخرب.
5) رفع باگ‌ها: NameError در مسیر «افزودن ربات توسط کاربر عادی»، کلیدگذاری صف کپچا
   بر اساس (گروه + کاربر) تا تداخل چندگروهی از بین برود، و پینگ واقعی API.

محیط اجرا:
- سازگار کامل با Termux (اندروید) و Windows و انواع لینوکس
- استفاده انحصاری از مسیرهای استاندارد (pathlib) بدون وابستگی به سیستم‌عامل خاص
=============================================================================
"""

import os
import sys
import json
import time
import asyncio
import inspect
import functools
import logging
import platform
import warnings
from pathlib import Path
from datetime import datetime
from importlib import metadata as pkg_metadata
from typing import Dict, Any, List, Optional, Tuple

# ---------------------------------------------------------------------------
# ۰. شیم سازگاری پایتون ۳.۱۲ / ۳.۱۳ / ۳.۱۴ (باید پیش از import پایروگرام اجرا شود)
# ---------------------------------------------------------------------------
# کتابخانه Pyrogram 2.0.106 در زمان import تابع asyncio.get_event_loop() را صدا می‌زند.
# از پایتون ۳.۱۴ به بعد، این تابع در نبود «لوپ جاری» به جای ساخت لوپ جدید، خطای
#   RuntimeError: There is no current event loop in thread 'MainThread'
# می‌دهد و ربات پیش از شروع کار می‌شکند. این شیم یک لوپ استاندارد می‌سازد و آن را
# به عنوان لوپ جاری ثبت می‌کند تا پایروگرام قدیمی هم روی پایتون جدید import شود.
# روی پایتون‌های قدیمی‌تر هیچ اثر جانبی ندارد.
def _ensure_event_loop_for_legacy_pyrogram() -> None:
    """ساخت و ثبت event loop پیش از import پایروگرام (سازگاری با پایتون ۳.۱۲ تا ۳.۱۴)"""
    if sys.version_info < (3, 10):
        return
    with warnings.catch_warnings():
        # set_event_loop در پایتون‌های جدید DeprecationWarning می‌دهد؛ برای ما بی‌ضرر است
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            except Exception as exc:  # در بدترین حالت ربات با فورک‌های جدید کار می‌کند
                print(f"⚠️  ساخت event loop پیش از import پایروگرام ناموفق بود: {exc}")
        except Exception:
            pass


_ensure_event_loop_for_legacy_pyrogram()

import pyrogram
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions,
    ChatMemberUpdated,
    ChatInviteLink,
    User,
)
from pyrogram.enums import ChatType, ChatMemberStatus, ChatMembersFilter
from pyrogram.errors import (
    FloodWait,
    RPCError,
    ChatAdminRequired,
    UserAdminInvalid,
    UserNotParticipant,
    UserIdInvalid,
    UsernameNotOccupied,
    PeerIdInvalid,
    MessageNotModified,
)
# ---------------------------------------------------------------------------
# ۱. پیکربندی مسیرها و لاگر سیستم (کاملاً مستقل از سیستم‌عامل)
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent
CONFIG_FILE: Path = BASE_DIR / "config.json"
STATE_FILE: Path = BASE_DIR / "bot_state.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("AntiRaidBot")

# ---------------------------------------------------------------------------
# ۲. ساختار تنظیمات پیش‌فرض (Default Config)
# ---------------------------------------------------------------------------
BOT_VERSION: str = "4.1.0"

# ساختار تنظیمات پیش‌فرض (Default Config)
# نکته: کلیدهای جدید نسخه ۴ به صورت «ادغام عمیق» با config.json موجود ترکیب می‌شوند،
# بنابراین نیازی به بازنویسی دستی فایل تنظیمات قدیمی نیست.
DEFAULT_CONFIG: Dict[str, Any] = {
    "telegram": {
        "api_id": 0,
        "api_hash": "YOUR_API_HASH_HERE",
        "bot_token": "YOUR_BOT_TOKEN_HERE"
    },
    "admin_ids": [
        123456789
    ],
    "log_channel_id": 0,
    # ------------------------------------------------------------------
    # 🔔 سیاست اعلان‌ها (مهم‌ترین تنظیم نسخه ۴)
    #   status_log_to_owner_pv  : لاگ آنلاین/آفلاین/کرش ربات → فقط پیوی اونر (قفل‌شده)
    #   send_logs_to_channel    : ارسال سایر لاگ‌های امنیتی به کانال لاگ → پیش‌فرض خاموش
    #   notify_on_moderation    : گزارش عملیات بن/آزادسازی دستی → پیوی اونر
    # هیچ‌کدام از این لاگ‌ها تحت هیچ شرایطی به داخل گروه‌های محافظت‌شده ارسال نمی‌شوند.
    # ------------------------------------------------------------------
    "notifications": {
        "status_log_to_owner_pv": True,
        "send_logs_to_channel": False,
        "notify_on_moderation": True
    },
    # ------------------------------------------------------------------
    # 🚫 تنظیمات مرکز مدیریت اعضا (بن/آزادسازی از پیوی)
    # ------------------------------------------------------------------
    "moderation": {
        "unverified_page_size": 5,
        "banned_page_size": 5,
        "banned_fetch_limit": 100,
        "require_confirm": True
    },
    "captcha": {
        "timeout_seconds": 60,
        "welcome_text": (
            "سلام {user} عزیز! 🌸\n"
            "به گروه خوش آمدید.\n\n"
            "⚠️ برای مقابله با بات‌های مخرب، لطفاً ظرف {time} ثانیه روی دکمه زیر کلیک کنید؛ "
            "در غیر این صورت از گروه اخراج خواهید شد."
        ),
        "button_text": "🤖 من ربات نیستم (تأیید عضویت)",
        "verified_text": "✅ هویت شما با موفقیت تأیید شد. خوش آمدید!",
        "timeout_text": "⏱️ کاربر {user} به دلیل عدم تأیید کپچا در زمان مقرر ({time} ثانیه) از گروه اخراج شد."
    },
    "anti_add": {
        "max_adds_per_day": 3,
        "violation_action": "warn",  # گزینه‌ها: "warn" (هشدار)، "kick" (اخراج موقت)، "ban" (بن دائم)
        "kick_added_on_violation": True,
        "warning_text": (
            "⚠️ **هشدار امنیتی: نقض سقف مجاز افزودن عضو!**\n\n"
            "👤 **کاربر متخلف:** {user} (`{user_id}`)\n"
            "📊 **تعداد اد در ۲۴ ساعت گذشته:** {count} نفر (سقف مجاز: {limit})\n"
            "⚡ **اقدام سیستمی:** {action}\n\n"
            "📋 **لیست اعضای اضافه شده توسط این کاربر:**\n"
            "{members}"
        )
    },
    "sweep": {
        "retention_hours": 24
    },
    "modules": {
        "captcha": True,
        "anti_add": True,
        "panic": True,
        "sweep": True,
        "moderation": True,
        "logging": True
    },
    "command_aliases": {
        "panic": ["panic", "ریzone", "اضطرار", "بحران"],
        "sweep": ["sweep", "جارو", "پاکسازی"],
        "config": ["config", "تنظیمات"],
        "set": ["set", "تنظیم"],
        "toggle": ["toggle", "تغییر"]
    }
}

# ---------------------------------------------------------------------------
# ۳. توابع بارگذاری و ذخیره‌سازی پیکربندی (Thread-safe JSON Persistence)
# ---------------------------------------------------------------------------
def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    ادغام عمیق تنظیمات کاربر روی ساختار پیش‌فرض.
    با این روش، کلیدهای جدیدِ اضافه‌شده در نسخه‌های بعدی ربات به صورت خودکار
    به config.json قدیمی تزریق می‌شوند و مقادیر دست‌خورده کاربر حفظ می‌گردند.
    """
    result: Dict[str, Any] = dict(base or {})
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> Dict[str, Any]:
    """بارگذاری تنظیمات از فایل config.json یا ساخت نمونه اولیه در صورت عدم وجود"""
    if not CONFIG_FILE.exists():
        logger.warning("فایل config.json یافت نشد؛ ایجاد فایل پیش‌فرض نمونه...")
        save_config_file(DEFAULT_CONFIG)
        print("\n" + "=" * 70)
        print("⚠️  فایل تنظیمات نمونه (config.json) ایجاد شد!")
        print("لطفاً فایل config.json را ویرایش کرده و مقادیر زیر را در آن وارد کنید:")
        print("   1. telegram -> api_id (از سایت my.telegram.org)")
        print("   2. telegram -> api_hash (از سایت my.telegram.org)")
        print("   3. telegram -> bot_token (از ربات @BotFather)")
        print("   4. admin_ids -> آیدی عددی ادمین‌های ربات")
        print("سپس مجدداً ربات را با دستور 'python bot.py' اجرا نمایید.")
        print("=" * 70 + "\n")
        sys.exit(0)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # ادغام عمیق کلیدهای پیش‌فرض با کانفیگ بارگذاری شده (در صورت اضافه شدن فیلد جدید)
        merged = _deep_merge(DEFAULT_CONFIG, data)

        # نرمال‌سازی آیدی مدیران برای جلوگیری از خطای تایپی در config.json
        safe_admins: List[int] = []
        for raw in merged.get("admin_ids", []) or []:
            try:
                safe_admins.append(int(str(raw).strip()))
            except (TypeError, ValueError):
                logger.warning(f"آیدی نامعتبر در admin_ids نادیده گرفته شد: {raw!r}")
        merged["admin_ids"] = safe_admins
        return merged
    except Exception as e:
        logger.error(f"خطا در خواندن فایل config.json: {e}")
        sys.exit(1)


def save_config_file(cfg: Dict[str, Any]) -> None:
    """ذخیره تنظیمات در فایل config.json با فرمت استاندارد UTF-8"""
    try:
        temp_file = BASE_DIR / "config.json.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
        temp_file.replace(CONFIG_FILE)
    except Exception as e:
        logger.error(f"خطا در ذخیره سازی config.json: {e}")


def get_setting(section: str, key: str, default: Any = None) -> Any:
    """خواندن امن یک تنظیم تو در تو با بازگشت به مقدار پیش‌فرض در صورت نبود"""
    user_value = config.get(section, {})
    if isinstance(user_value, dict) and key in user_value:
        return user_value[key]
    base_value = DEFAULT_CONFIG.get(section, {})
    if isinstance(base_value, dict) and key in base_value:
        return base_value[key]
    return default


def set_setting(section: str, key: str, value: Any) -> None:
    """تنظیم یک کلید تو در تو و ذخیره فوری روی دیسک"""
    config.setdefault(section, {})[key] = value
    save_config_file(config)


# شیء عمومی تنظیمات در حافظه
config: Dict[str, Any] = load_config()

# ---------------------------------------------------------------------------
# ۴. متغیرهای سراسری وضعیت و حافظه موقت (In-Memory State & Cache)
# ---------------------------------------------------------------------------
# زمان دقیق شروع به کار ربات (جهت محاسبه آپ‌تایم در منوها و لاگ آفلاین)
BOT_START_TIME: float = time.time()

# مشخصات خود ربات پس از اتصال موفق به تلگرام (در main مقداردهی می‌شود)
BOT_ME: Optional[User] = None

# دیکشنری نگهداری سوپرگروه‌های شناسایی‌شده تحت پوشش ربات:
# ساختار: { "chat_id_str": { "id": int, "title": str, "updated_at": float } }
known_groups: Dict[str, Dict[str, Any]] = {}

# دیکشنری نگهداری عضوهای تأیید نشده برای عملیات /sweep:
# ساختار: { "chat_id:user_id": { "chat_id": int, "user_id": int, "join_time": float,
#                                 "first_name": str, "username": str } }
# نکته نسخه ۴: کلیدها بر اساس «گروه + کاربر» ساخته می‌شوند تا ورود همزمان یک کاربر
# به دو گروه مختلف باعث بازنویسی رکورد یکدیگر نشود.
unverified_joins: Dict[str, Dict[str, Any]] = {}

# دیکشنری تاریخچه افزودن اعضا توسط هر کاربر در ۲۴ ساعت:
# ساختار: { "inviter_id": { "name": str, "username": str, "adds": [ {...} ] } }
user_add_history: Dict[str, Any] = {}

# دیکشنری رصد ورودی‌های لینک‌های دعوت (چه کسی با لینک چه فردی وارد شده است):
# ساختار: { "creator_id": { "name": str, "username": str, "count": int, "joins": list } }
link_join_history: Dict[str, Dict[str, Any]] = {}

# دیکشنری تسک‌های در حال اجرای کپچا (برای لغو شدن پس از تأیید یا بن):
# ساختار: { "chat_id:user_id": { "chat_id": int, "user_id": int, "message_id": int, "task": Task } }
pending_verifications: Dict[str, Dict[str, Any]] = {}

# کش جهت جلوگیری از پردازش تکراری جوین‌ها (Deduplication)
recent_events_cache: Dict[Tuple[int, int], float] = {}

# 🚫 سوابق بن‌های انجام‌شده توسط ربات (دستی از پیوی یا خودکار با Sweep):
# ساختار: { "chat_id:user_id": { "chat_id", "user_id", "first_name", "username",
#                                 "by", "by_name", "reason", "time", "auto" } }
ban_records: Dict[str, Dict[str, Any]] = {}

# ⌨️ ماشین حالت ورودی متنی پیوی اونر (برای بن دستی با آیدی/یوزرنیم):
# ساختار: { admin_id_int: { "action": str, "chat_id": int, "started_at": float, "step": str } }
pending_admin_input: Dict[int, Dict[str, Any]] = {}

# دلیل بن در انتظار تأیید (چون callback_data تلگرام حداکثر ۶۴ بایت است):
# ساختار: { "admin_id:chat_id:user_id": "reason" }
pending_ban_reasons: Dict[str, str] = {}


def member_key(chat_id: Any, user_id: Any) -> str:
    """ساخت کلید یکتای «گروه + کاربر» برای صف کپچا، اعضای تأیید نشده و سوابق بن"""
    return f"{int(chat_id)}:{int(user_id)}"


def register_known_group(chat_id: int, title: Optional[str] = None) -> None:
    """ثبت یا به‌روزرسانی مشخصات سوپرگروه در حافظه کش دیتابیس"""
    if not chat_id or chat_id >= 0:
        return
    cid_str = str(chat_id)
    existing = known_groups.get(cid_str, {})
    new_title = title or existing.get("title") or f"گروه `{chat_id}`"
    known_groups[cid_str] = {
        "id": chat_id,
        "title": new_title,
        "updated_at": time.time()
    }
    save_state()


def group_title(chat_id: Any) -> str:
    """عنوان ثبت‌شده یک سوپرگروه (یا برچسب آیدی در صورت نبود رکورد)"""
    if str(chat_id) == "all":
        return "تمام گروه‌ها (تجمیعی)"
    info = known_groups.get(str(chat_id), {})
    return info.get("title") or f"گروه `{chat_id}`"


def migrate_legacy_keys(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    تبدیل کلیدهای قدیمی (فقط آیدی کاربر) به کلیدهای جدید «گروه:کاربر».
    این تابع باعث می‌شود bot_state.json نسخه‌های قبلی بدون از دست رفتن داده خوانده شود.
    """
    migrated: Dict[str, Any] = {}
    for key, value in (raw or {}).items():
        if not isinstance(value, dict):
            continue
        if ":" in str(key):
            migrated[str(key)] = value
            continue
        cid = value.get("chat_id") or 0
        uid = value.get("user_id")
        if uid is None:
            try:
                uid = int(key)
            except (TypeError, ValueError):
                continue
        value.setdefault("user_id", uid)
        if cid:
            value.setdefault("chat_id", cid)
            migrated[member_key(cid, uid)] = value
        else:
            migrated[str(uid)] = value
    return migrated


def load_state() -> None:
    """بارگذاری وضعیت‌های ثبت شده از دیسک جهت پایداری داده‌ها پس از ری‌استارت"""
    if not STATE_FILE.exists():
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        known_groups.clear()
        known_groups.update(data.get("known_groups", {}) or {})

        unverified_joins.clear()
        unverified_joins.update(migrate_legacy_keys(data.get("unverified_joins", {}) or {}))

        user_add_history.clear()
        user_add_history.update(data.get("user_add_history", {}) or {})

        link_join_history.clear()
        link_join_history.update(data.get("link_join_history", {}) or {})

        ban_records.clear()
        ban_records.update(migrate_legacy_keys(data.get("ban_records", {}) or {}))

        # کشف خودکار گروه‌ها از رکوردهای پیشین جهت حفظ یکپارچگی
        for u in unverified_joins.values():
            cid = u.get("chat_id")
            if cid and str(cid) not in known_groups:
                known_groups[str(cid)] = {"id": cid, "title": f"گروه `{cid}`", "updated_at": u.get("join_time", 0)}

        for item in link_join_history.values():
            for j in item.get("joins", []):
                cid = j.get("chat_id")
                if cid and str(cid) not in known_groups:
                    known_groups[str(cid)] = {"id": cid, "title": f"گروه `{cid}`", "updated_at": j.get("time", 0)}

        for item in user_add_history.values():
            raw_adds = item.get("adds", []) if isinstance(item, dict) else (item if isinstance(item, list) else [])
            for a in raw_adds:
                cid = a.get("chat_id")
                if cid and str(cid) not in known_groups:
                    known_groups[str(cid)] = {"id": cid, "title": f"گروه `{cid}`", "updated_at": a.get("time", 0)}

        for b in ban_records.values():
            cid = b.get("chat_id")
            if cid and str(cid) not in known_groups:
                known_groups[str(cid)] = {"id": cid, "title": f"گروه `{cid}`", "updated_at": b.get("time", 0)}

        logger.info(
            f"داده‌های وضعیت بارگذاری شدند ({len(known_groups)} گروه، "
            f"{len(unverified_joins)} کاربر تأیید نشده، {len(ban_records)} سابقه بن)."
        )
    except Exception as e:
        logger.warning(f"عدم امکان خواندن bot_state.json: {e}")


def save_state() -> None:
    """ذخیره وضعیت بر روی دیسک به صورت ایمن"""
    try:
        temp_state = BASE_DIR / "bot_state.json.tmp"
        with open(temp_state, "w", encoding="utf-8") as f:
            json.dump({
                "known_groups": known_groups,
                "unverified_joins": unverified_joins,
                "user_add_history": user_add_history,
                "link_join_history": link_join_history,
                "ban_records": ban_records
            }, f, ensure_ascii=False, indent=2)
        temp_state.replace(STATE_FILE)
    except Exception as e:
        logger.error(f"خطا در ذخیره وضعیت bot_state.json: {e}")

# ---------------------------------------------------------------------------
# ۵. مقداردهی کلاینت پایروگرام و کلاس فرمت امن (Safe Formatter & Client Setup)
# ---------------------------------------------------------------------------
class SafeDict(dict):
    """کلاس فرمت امن برای جلوگیری از کرش ربات در صورت نبود یک متغیر در متن‌های سفارشی کانفیگ"""
    def __missing__(self, key):
        return f"{{{key}}}"

tg_cfg = config.get("telegram", {})
API_ID = tg_cfg.get("api_id", 0)
API_HASH = tg_cfg.get("api_hash", "")
BOT_TOKEN = tg_cfg.get("bot_token", "")

app = Client(
    name="anti_raid_bot_session",
    api_id=int(API_ID) if API_ID else 12345678,
    api_hash=str(API_HASH) if API_HASH else "0123456789abcdef0123456789abcdef",
    bot_token=str(BOT_TOKEN) if BOT_TOKEN else "123456:dummy_token_abc_xyz",
    workdir=str(BASE_DIR)
)

# ---------------------------------------------------------------------------
# ۵.۵. لایه سازگاری پایتون و کتابخانه تلگرام (Python 3.9–3.14 Compatibility)
# ---------------------------------------------------------------------------
# این ربات باید روی سه پیاده‌سازی متفاوت کار کند:
#   • Pyrogram رسمی 2.0.106  (پایتون ۳.۹ تا ۳.۱۱)
#   • kurigram               (فورک به‌روز؛ پایتون ۳.۱۰ تا ۳.۱۴+)
#   • pyrofork               (فورک به‌روز؛ پایتون ۳.۱۰ تا ۳.۱۴+)
# تفاوت‌های کلیدی که این لایه یکدست می‌کند:
#   ۱) حذف پارامتر disable_web_page_preview از edit_text/reply_text در فورک‌های جدید
#      (جایگزین: link_preview_options)
#   ۲) تغییر کلیدواژه‌های ChatPermissions در pyrofork (تفکیک رسانه‌ها)
#   ۳) جایگزینی فیلدهای forward_from / forward_from_chat با شیء forward_origin
#   ۴) نبود wheel برای tgcrypto روی پایتون ۳.۱۲+ (جایگزین: tgcrypto2)


def _method_accepts(func: Any, name: str) -> bool:
    """بررسی اینکه آیا یک تابع کلیدواژه مشخص را می‌پذیرد یا خیر"""
    try:
        params = inspect.signature(func).parameters
    except (TypeError, ValueError):
        return True
    if name in params:
        return True
    return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())


def _install_link_preview_compat() -> List[str]:
    """
    ترجمه شفاف پارامتر قدیمی disable_web_page_preview به link_preview_options.

    در فورک‌های جدید (kurigram) پارامتر disable_web_page_preview از توابع
    edit_text و reply_text حذف شده است؛ بدون این لایه، همه فراخوانی‌های ربات با
    TypeError می‌شکستند. این تابع یک بار در زمان بارگذاری اجرا می‌شود و فقط در صورت
    نیاز، پوسته‌ای سازگار دور همان توابع می‌گذارد (بدون تغییر رفتار در Pyrogram رسمی).
    """
    patched: List[str] = []
    try:
        from pyrogram.types import LinkPreviewOptions
    except Exception:
        LinkPreviewOptions = None

    for owner, name in (
        (Message, "edit_text"),
        (Message, "reply_text"),
        (Message, "edit_caption"),
        (Message, "reply"),
        (Client, "send_message"),
        (Client, "edit_message_text"),
    ):
        func = getattr(owner, name, None)
        if func is None or getattr(func, "_nsmc_preview_patched", False):
            continue
        if _method_accepts(func, "disable_web_page_preview"):
            continue
        if not _method_accepts(func, "link_preview_options"):
            continue

        def make_wrapper(original, owner_name, method_name):
            # پوسته همگام (نه async): کتابخانه تلگرام، متدها را طوری می‌پوشاند که هم با
            # await و هم به‌صورت همگام قابل استفاده باشند. این پوسته فقط کلیدواژه را
            # ترجمه می‌کند و دقیقاً همان چیزی را برمی‌گرداند که تابع اصلی برمی‌گرداند.
            @functools.wraps(original)
            def wrapper(self, *args, **kwargs):
                disabled = kwargs.pop("disable_web_page_preview", None)
                if disabled and LinkPreviewOptions is not None and "link_preview_options" not in kwargs:
                    try:
                        kwargs["link_preview_options"] = LinkPreviewOptions(is_disabled=True)
                    except Exception:
                        pass
                return original(self, *args, **kwargs)

            wrapper.__qualname__ = f"{owner_name}.{method_name}"
            wrapper._nsmc_preview_patched = True
            return wrapper

        try:
            setattr(owner, name, make_wrapper(func, owner.__name__, name))
            patched.append(f"{owner.__name__}.{name}")
        except Exception as exc:
            logger.warning(f"اعمال لایه سازگاری روی {owner.__name__}.{name} ناموفق بود: {exc}")
    return patched


def detect_telegram_library() -> Tuple[str, str]:
    """تشخیص اینکه ماژول pyrogram توسط کدام پکیج (رسمی یا فورک) نصب شده است"""
    for dist in ("kurigram", "pyrofork", "Pyrogram", "pyrogram"):
        try:
            return dist, pkg_metadata.version(dist)
        except Exception:
            continue
    return "pyrogram", str(getattr(pyrogram, "__version__", "نامشخص"))


def detect_mixed_installs() -> List[str]:
    """
    تشخیص نصب هم‌زمان چند کتابخانه تلگرام.

    Pyrogram رسمی، kurigram و pyrofork هر سه پوشه‌ای به نام «pyrogram» در
    site-packages می‌سازند؛ نصب هم‌زمان آن‌ها فایل‌ها را خراب می‌کند و رفتار
    غیرقابل پیش‌بینی می‌سازد. این تابع نام پکیج‌های نصب‌شده را برمی‌گرداند.
    """
    found: Dict[str, str] = {}
    for dist in ("pyrogram", "kurigram", "pyrofork"):
        try:
            found[dist] = pkg_metadata.version(dist)
        except Exception:
            continue
    return [f"{name} {ver}" for name, ver in found.items()] if len(found) > 1 else []


def detect_crypto_acceleration() -> bool:
    """آیا شتاب‌دهنده رمزنگاری (tgcrypto/tgcrypto2) نصب است؟"""
    try:
        import tgcrypto  # noqa: F401
        return True
    except Exception:
        return False


TELEGRAM_LIB, TELEGRAM_LIB_VERSION = detect_telegram_library()
CRYPTO_ACCELERATED = detect_crypto_acceleration()
PREVIEW_COMPAT_PATCHED = _install_link_preview_compat()


def is_official_pyrogram() -> bool:
    """آیا نسخه رسمی (و قدیمی) Pyrogram نصب است؟"""
    return str(TELEGRAM_LIB).lower() == "pyrogram"


def runtime_report() -> Dict[str, Any]:
    """گزارش فنی محیط اجرا برای نمایش در منوی «وضعیت سیستم»"""
    return {
        "python": platform.python_version(),
        "python_info": sys.version_info,
        "library": TELEGRAM_LIB,
        "library_version": TELEGRAM_LIB_VERSION,
        "crypto": CRYPTO_ACCELERATED,
        "patched": PREVIEW_COMPAT_PATCHED,
        "official": is_official_pyrogram(),
        "mixed": detect_mixed_installs(),
    }


def compatibility_warnings() -> List[str]:
    """هشدارهای سازگاری همراه با دستور اصلاح (فارسی و آماده کپی)"""
    warns: List[str] = []
    info = sys.version_info
    exe = f'"{sys.executable}"' if " " in sys.executable else sys.executable

    mixed = detect_mixed_installs()
    if mixed:
        keep = "kurigram" if info >= (3, 10) else "Pyrogram"
        drop = [name.split()[0] for name in mixed if name.split()[0].lower() != keep.lower()]
        warns.append(
            "⚠️ بیش از یک کتابخانه تلگرام به‌طور هم‌زمان نصب است و فایل‌های ماژول pyrogram را خراب می‌کند:\n"
            f"   نصب‌شده‌ها: {', '.join(mixed)}\n"
            f"   برای اصلاح، فقط «{keep}» را نگه دارید:\n"
            f"   {exe} -m pip uninstall -y {' '.join(drop)}\n"
            f"   {exe} -m pip install --force-reinstall {keep}"
        )

    if info >= (3, 12) and is_official_pyrogram():
        warns.append(
            f"⚠️ پایتون {platform.python_version()} با Pyrogram رسمی {TELEGRAM_LIB_VERSION} ترکیب شده است.\n"
            f"   این نسخه برای پایتون ۳.۱۲+ نگهداری نمی‌شود؛ توصیه اکید، نصب فورک به‌روز kurigram است:\n"
            f"   {exe} -m pip uninstall -y pyrogram\n"
            f"   {exe} -m pip install kurigram"
        )
    elif info < (3, 9):
        warns.append(
            f"⚠️ پایتون {platform.python_version()} قدیمی‌تر از حداقل نسخه پشتیبانی‌شده (۳.۹) است."
        )

    if not CRYPTO_ACCELERATED:
        if info >= (3, 12):
            warns.append(
                "⚠️ شتاب‌دهنده رمزنگاری نصب نیست (سرعت ربات کمتر می‌شود، ولی کار می‌کند).\n"
                f"   برای پایتون {platform.python_version()} از پکیج tgcrypto2 استفاده کنید (wheel آماده دارد):\n"
                f"   {exe} -m pip install tgcrypto2"
            )
        else:
            warns.append(
                "⚠️ شتاب‌دهنده رمزنگاری نصب نیست (سرعت ربات کمتر می‌شود، ولی کار می‌کند).\n"
                f"   {exe} -m pip install tgcrypto==1.2.5"
            )

    return warns


def restricted_chat_permissions() -> ChatPermissions:
    """محدودسازی کامل ارسال پیام تا زمان حل کپچا (سازگار با همه نسخه‌ها)"""
    return ChatPermissions(can_send_messages=False)


def unrestricted_chat_permissions() -> ChatPermissions:
    """
    بازگرداندن دسترسی کامل کاربر پس از تأیید کپچا.

    Pyrogram 2.0.106 و kurigram کلیدواژه‌های قدیمی (can_send_media_messages و
    can_send_other_messages) را می‌پذیرند، اما pyrofork آن‌ها را با کلیدواژه‌های
    تفکیک‌شده رسانه (can_send_photos و …) جایگزین کرده است. این تابع هر دو امضا را
    امتحان می‌کند تا ربات روی همه کتابخانه‌ها یکسان کار کند.
    """
    legacy_kwargs: Dict[str, bool] = dict(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_send_polls=True,
        can_invite_users=True,
    )
    modern_kwargs: Dict[str, bool] = dict(
        can_send_messages=True,
        can_add_web_page_previews=True,
        can_send_polls=True,
        can_invite_users=True,
        can_send_audios=True,
        can_send_docs=True,
        can_send_games=True,
        can_send_gifs=True,
        can_send_inline=True,
        can_send_photos=True,
        can_send_plain=True,
        can_send_roundvideos=True,
        can_send_stickers=True,
        can_send_videos=True,
        can_send_voices=True,
    )
    for kwargs in (legacy_kwargs, modern_kwargs):
        try:
            return ChatPermissions(**kwargs)
        except TypeError:
            continue
        except Exception as exc:
            logger.debug(f"ساخت ChatPermissions ناموفق بود: {exc}")
    return ChatPermissions(can_send_messages=True)


# ---------------------------------------------------------------------------
# دسترسی یکدست به اطلاعات پیام فورواردشده (سازگار با forward_origin و فیلدهای قدیمی)
# ---------------------------------------------------------------------------
def get_forward_origin(message: Message) -> Optional[Any]:
    """شیء جدید forward_origin در فورک‌های به‌روز (در Pyrogram رسمی وجود ندارد)"""
    return getattr(message, "forward_origin", None)


def is_forwarded_message(message: Message) -> bool:
    """آیا پیام فوروارد شده است؟ (بدون فعال‌کردن هشدارهای deprecation)"""
    if get_forward_origin(message) is not None:
        return True
    return bool(
        getattr(message, "forward_date", None)
        or getattr(message, "forward_from", None)
        or getattr(message, "forward_from_chat", None)
    )


def get_forward_user(message: Message) -> Optional[User]:
    """کاربر مبدأ پیام فورواردشده (در صورت مخفی نبودن حساب)"""
    origin = get_forward_origin(message)
    if origin is not None:
        return getattr(origin, "sender_user", None)
    return getattr(message, "forward_from", None)


def get_forward_user_id(message: Message) -> Optional[int]:
    """آیدی عددی کاربر مبدأ؛ اگر حساب مخفی باشد None برمی‌گردد"""
    user = get_forward_user(message)
    if user is not None and getattr(user, "id", None):
        return int(user.id)
    legacy_id = getattr(message, "forward_from_id", None)
    if legacy_id:
        return int(legacy_id)
    origin = get_forward_origin(message)
    if origin is not None:
        sender_id = getattr(origin, "sender_user_id", None)
        if sender_id:
            return int(sender_id)
    return None


def get_forward_chat(message: Message) -> Optional[Any]:
    """چت/کانال مبدأ پیام فورواردشده"""
    origin = get_forward_origin(message)
    if origin is not None:
        return getattr(origin, "chat", None) or getattr(origin, "sender_chat", None)
    return getattr(message, "forward_from_chat", None)


def get_forward_sender_name(message: Message) -> str:
    """نام نمایشی فرستنده (وقتی حساب کاربر مخفی است)"""
    origin = get_forward_origin(message)
    if origin is not None:
        name = getattr(origin, "sender_user_name", None)
        if name:
            return str(name)
    return str(getattr(message, "forward_sender_name", "") or "")


def get_forward_date(message: Message) -> Optional[int]:
    """زمان فوروارد شدن پیام"""
    origin = get_forward_origin(message)
    if origin is not None:
        date = getattr(origin, "date", None)
        if date:
            return int(date)
    date = getattr(message, "forward_date", None)
    return int(date) if date else None


# ---------------------------------------------------------------------------
# ۶. توابع کمکی امنیتی، لاگ‌گیری و اعلان‌های پیوی (Helpers & Logging Policy)
# ---------------------------------------------------------------------------
def is_duplicate_event(chat_id: int, user_id: int, ttl_seconds: float = 8.0) -> bool:
    """بررسی اینکه آیا رویداد این کاربر در ثانیه‌های اخیر قبلاً پردازش شده یا خیر"""
    now = time.time()
    # پاکسازی رکوردهای منقضی کش
    for key in list(recent_events_cache.keys()):
        if now - recent_events_cache[key] > ttl_seconds:
            del recent_events_cache[key]

    event_key = (chat_id, user_id)
    if event_key in recent_events_cache:
        return True
    recent_events_cache[event_key] = now
    return False


def is_admin_user(user_id: int) -> bool:
    """بررسی شناسه کاربر با لیست ادمین‌های مجاز (اونر) در config.json"""
    try:
        configured_admins = [int(a) for a in config.get("admin_ids", []) if a]
    except (TypeError, ValueError):
        configured_admins = []
    return int(user_id) in configured_admins


async def is_admin(client: Client, message: Message) -> bool:
    """
    بررسی دسترسی منحصراً برای ادمین اصلی (تنها آیدی‌های ثبت‌شده در admin_ids در config.json).
    سایر ادمین‌های تلگرامی گروه یا اعضای عادی دسترسی ندارند و ربات به آنها هیچ پاسخی نمی‌دهد (سکوت مطلق).
    """
    user = message.from_user
    if not user:
        return False
    return is_admin_user(user.id)


async def safe_edit(message: Message, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> None:
    """ویرایش امن پیام جهت جلوگیری از بروز خطای MessageNotModified تلگرام"""
    try:
        await message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
    except MessageNotModified:
        pass
    except Exception as e:
        logger.warning(f"عدم امکان ویرایش پیام: {e}")


def format_uptime(seconds: float) -> str:
    """تبدیل ثانیه به متن خوانای فارسی برای نمایش آپ‌تایم ربات"""
    total = int(max(0, seconds))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts: List[str] = []
    if days:
        parts.append(f"{days} روز")
    if hours:
        parts.append(f"{hours} ساعت")
    if minutes:
        parts.append(f"{minutes} دقیقه")
    if not parts:
        parts.append(f"{secs} ثانیه")
    return " و ".join(parts)


def resolve_log_channel() -> Optional[Any]:
    """
    تبدیل امن شناسه کانال لاگ به مقدار قابل استفاده.
    خروجی: عدد منفی (کانال/سوپرگروه) یا رشته @username یا None (بدون کانال لاگ).
    """
    log_channel = config.get("log_channel_id", 0)
    if isinstance(log_channel, str):
        cleaned = log_channel.strip()
        if not cleaned or cleaned in ("0", "null", "None"):
            return None
        if cleaned.startswith("@"):
            return cleaned
        if cleaned.startswith("-100") or cleaned.lstrip("-").isdigit():
            try:
                value = int(cleaned)
            except ValueError:
                return None
            return value if value < 0 else None
        return None
    try:
        value = int(log_channel)
    except (TypeError, ValueError):
        return None
    return value if value < 0 else None


def is_protected_group(chat_id: Any) -> bool:
    """آیا این شناسه یکی از سوپرگروه‌های محافظت‌شده توسط ربات است؟"""
    return str(chat_id) in known_groups


def _stamp_log(text: str, header: str) -> str:
    """افزودن سربرگ و زمان به متن لاگ"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"{header} | `{now_str}`\n──────────────────────\n{text}"


async def _send_to_owner_pv(formatted: str) -> int:
    """ارسال متن آماده‌شده فقط به پیوی مدیران مجاز (اونر) و بازگرداندن تعداد موفق‌ها"""
    admin_ids = [int(a) for a in config.get("admin_ids", []) if a]
    if not admin_ids:
        logger.warning("هیچ آیدی مدیری در config.json ثبت نشده است؛ لاگ به کسی ارسال نشد.")
        return 0

    delivered = 0
    for admin_id in admin_ids:
        for _attempt in range(2):
            try:
                await app.send_message(chat_id=admin_id, text=formatted, disable_web_page_preview=True)
                delivered += 1
                break
            except FloodWait as e:
                wait = min(int(getattr(e, "value", 5) or 5), 30)
                logger.warning(f"FloodWait در ارسال لاگ به پیوی {admin_id}؛ انتظار {wait} ثانیه")
                await asyncio.sleep(wait)
            except Exception as e:
                logger.debug(f"عدم امکان ارسال لاگ به پیوی ادمین {admin_id}: {e}")
                break

    if delivered == 0:
        logger.warning("ارسال لاگ به پیوی مدیران ناموفق بود؛ ابتدا در پیوی ربات دستور /start را بفرستید.")
    return delivered


async def _send_to_log_channel(formatted: str) -> bool:
    """ارسال لاگ به کانال لاگ — فقط در صورت فعال بودن گزینه و غیرگروه بودن مقصد"""
    channel = resolve_log_channel()
    if not channel:
        return False
    # 🔒 قفل سخت‌گیرانه نسخه ۴: هرگز لاگ امنیتی به داخل گروه‌های محافظت‌شده فرستاده نمی‌شود
    if isinstance(channel, int) and is_protected_group(channel):
        logger.warning(
            f"log_channel_id ({channel}) یکی از گروه‌های محافظت‌شده است؛ "
            "طبق سیاست ربات، هیچ لاگی به داخل گروه ارسال نمی‌شود."
        )
        return False
    try:
        await app.send_message(chat_id=channel, text=formatted, disable_web_page_preview=True)
        return True
    except Exception as e:
        logger.debug(f"عدم امکان ارسال لاگ به کانال لاگ: {e}")
        return False


async def send_owner_log(text: str, header: str = "📋 گزارش امنیتی ربات") -> int:
    """
    ارسال گزارش منحصراً به پیوی اونر/ادمین‌های مجاز.
    این تابع به هیچ عنوان به گروه یا کانال لاگ چیزی ارسال نمی‌کند.
    """
    return await _send_to_owner_pv(_stamp_log(text, header))


async def send_log(text: str, pv_only: bool = False) -> None:
    """
    ارسال گزارش‌های امنیتی ربات.

    مقصد پیش‌فرض: پیوی اونر (در صورت فعال بودن ماژول logging).
    ارسال به کانال لاگ تنها زمانی انجام می‌شود که:
      ۱) گزینه notifications.send_logs_to_channel فعال باشد، و
      ۲) مقصد، یکی از گروه‌های محافظت‌شده نباشد.
    با pv_only=True گزارش حتی به کانال لاگ هم فرستاده نمی‌شود.
    """
    formatted = _stamp_log(text, "📋 گزارش امنیتی ربات")

    if config.get("modules", {}).get("logging", True):
        await _send_to_owner_pv(formatted)

    if pv_only:
        return
    if not get_setting("notifications", "send_logs_to_channel", False):
        return
    await _send_to_log_channel(formatted)


async def send_status_log(text: str) -> None:
    """
    🔔 لاگ وضعیت چرخه حیات ربات: آنلاین شدن، آفلاین شدن و کرش.

    طبق درخواست صریح، این لاگ‌ها **فقط** در پیوی اونر (admin_ids) ارسال می‌شوند و
    تحت هیچ شرایطی به گروه یا کانال لاگ نمی‌روند. همچنین برخلاف سایر لاگ‌ها،
    با خاموش بودن ماژول logging هم مسدود نمی‌شوند تا اونر همیشه از وضعیت ربات باخبر باشد.
    """
    if not get_setting("notifications", "status_log_to_owner_pv", True):
        logger.info("اعلان وضعیت ربات در تنظیمات غیرفعال شده است؛ چیزی به پیوی ارسال نشد.")
        return
    await _send_to_owner_pv(_stamp_log(text, "🔔 وضعیت ربات (فقط پیوی اونر)"))


async def auto_delete_message(client: Client, chat_id: int, message_id: int, delay_seconds: int = 10) -> None:
    """حذف خودکار پیام پس از تأخیر مشخص شده جهت جلوگیری از شلوغی سوپرگروه"""
    await asyncio.sleep(delay_seconds)
    try:
        await client.delete_messages(chat_id, message_id)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# ۷. منطق کپچا، تایمر اخراج و لغو کپچا (Captcha & Timeout Logic)
# ---------------------------------------------------------------------------
async def kick_member(client: Client, chat_id: int, user_id: int) -> bool:
    """
    اخراج موقت (Kick) یک عضو: ابتدا بن و بلافاصله آن‌بن تا کاربر بتواند بعداً دوباره وارد شود.
    خروجی: True در صورت موفقیت.
    """
    try:
        await client.ban_chat_member(chat_id, user_id)
        await client.unban_chat_member(chat_id, user_id)
        logger.info(f"کاربر {user_id} از گروه {chat_id} اخراج (Kick) شد.")
        return True
    except FloodWait as e:
        wait = min(int(getattr(e, "value", 5) or 5), 60)
        logger.warning(f"FloodWait در اخراج کاربر {user_id}؛ انتظار {wait} ثانیه")
        await asyncio.sleep(wait)
        try:
            await client.ban_chat_member(chat_id, user_id)
            await client.unban_chat_member(chat_id, user_id)
            return True
        except Exception as e2:
            logger.error(f"خطا در اخراج کاربر {user_id} پس از FloodWait: {e2}")
            return False
    except RPCError as e:
        logger.error(f"خطا در اخراج کاربر {user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"خطای غیرمنتظره در اخراج کاربر {user_id}: {e}")
        return False


def cancel_pending_captcha(chat_id: Any, user_id: Any) -> bool:
    """
    لغو تایمر کپچا و حذف کاربر از صف اعضای تأیید نشده.
    هنگام بن دستی از پیوی فراخوانی می‌شود تا تایمر اخراج، بن را به Kick تبدیل نکند.
    """
    key = member_key(chat_id, user_id)
    pending = pending_verifications.pop(key, None)
    if pending and pending.get("task"):
        pending["task"].cancel()
    removed = unverified_joins.pop(key, None) is not None
    if removed:
        save_state()
    return bool(pending or removed)


async def captcha_timeout_worker(client: Client, chat_id: int, user_id: int, message_id: int, user_name: str, seconds: int):
    """تسک پس‌زمینه تایمر کپچا؛ در صورت عدم کلیک، کاربر کیک (نه بن) می‌شود"""
    key = member_key(chat_id, user_id)
    try:
        await asyncio.sleep(seconds)

        # اگر کاربر همچنان در لیست انتظار باشد یعنی دکمه را نزده است
        if key in pending_verifications:
            pending_verifications.pop(key, None)
            unverified_joins.pop(key, None)
            save_state()

            # اخراج موقت: بن و سپس آن‌بن فوری تا بعداً بتواند دوباره وارد شود
            kicked_successfully = await kick_member(client, chat_id, user_id)

            # حذف پیام خوش‌آمد و کپچا از داخل گروه (گروه تمیز می‌ماند)
            try:
                await client.delete_messages(chat_id, message_id)
            except Exception:
                pass

            # ارسال لاگ اخراج منحصراً به پیوی ادمین (گروه کاملاً تمیز می‌ماند)
            await send_log(
                f"⏱️ **اخراج به علت انقضای کپچا (Kick)**\n"
                f"👤 کاربر: **{user_name}** (`{user_id}`)\n"
                f"💬 گروه: {group_title(chat_id)} (`{chat_id}`)\n"
                f"⏳ مهلت: {seconds} ثانیه\n"
                f"📌 نتیجه: {'موفقیت‌آمیز' if kicked_successfully else 'ناموفق (بررسی دسترسی ادمین ربات)'}"
            )
    except asyncio.CancelledError:
        # کاربر قبل از اتمام زمان دکمه را زد و تسک کنسل شد
        pass
    except Exception as e:
        logger.error(f"خطای پیش‌بینی‌نشده در تایمر کپچا: {e}")

# ---------------------------------------------------------------------------
# ۷.۵. ثبت و رهگیری لینک‌های دعوت (Invite Links Tracker)
# ---------------------------------------------------------------------------
group_owner_cache: Dict[int, User] = {}

async def get_group_owner(client: Client, chat_id: int) -> Optional[User]:
    """دریافت خودکار اطلاعات مالک سوپرگروه جهت انتساب لینک عمومی اصلی"""
    if chat_id in group_owner_cache:
        return group_owner_cache[chat_id]
    try:
        async for m in client.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
            if m.status == ChatMemberStatus.OWNER:
                group_owner_cache[chat_id] = m.user
                return m.user
    except Exception as e:
        logger.warning(f"عدم امکان دریافت مالک گروه: {e}")
    return None

async def record_invite_link_join(
    client: Client,
    chat_id: int,
    member: User,
    invite_link: Optional[ChatInviteLink] = None
) -> str:
    """
    ثبت عضو وارد شده در تاریخچه لینک‌های دعوت و بازگرداندن متن جزئیات جهت لاگ.
    اگر لینک عمومی اصلی استفاده شده باشد، به طور خودکار به مالک گروه (سازنده لینک) منتسب می‌گردد.
    """
    now = time.time()
    link_url = "لینک اصلی گروه"
    link_title = "لینک عمومی"

    creator_id_str = None
    creator_name = None
    creator_uname = ""
    creator_mention = ""

    if invite_link:
        link_url = invite_link.invite_link or "لینک اصلی گروه"
        link_title = invite_link.name or ("لینک اصلی گروه" if invite_link.is_primary else "لینک بدون عنوان")

        if invite_link.creator:
            creator = invite_link.creator
            creator_id_str = str(creator.id)
            creator_name = creator.first_name
            creator_uname = creator.username or ""
            creator_mention = creator.mention

    # اگر سازنده مستقیماً در آبجکت تلگرام مشخص نبود (لینک عمومی اصلی گروه)، سازنده همان مالک گروه است
    if not creator_id_str:
        owner = await get_group_owner(client, chat_id)
        if owner:
            creator_id_str = str(owner.id)
            creator_name = owner.first_name
            creator_uname = owner.username or ""
            creator_mention = f"{owner.mention} (مالک گروه)"
            link_title = "لینک اصلی گروه"
        else:
            creator_id_str = "primary"
            creator_name = "مالک گروه (لینک اصلی)"
            creator_uname = ""
            creator_mention = "مالک گروه (لینک اصلی)"

    link_details_log = (
        f"\n👑 **سازنده لینک:** {creator_mention} (`{creator_id_str}`)"
        f"\n🏷️ **عنوان لینک:** {link_title}"
        f"\n🔗 **آدرس لینک:** `{link_url}`"
    )

    c_stat = link_join_history.setdefault(creator_id_str, {
        "name": creator_name,
        "username": creator_uname,
        "count": 0,
        "joins": []
    })
    c_stat["name"] = creator_name
    c_stat["username"] = creator_uname

    # بررسی ثبت تکراری عضو در بازه زمانی کوتاه
    existing_joins = c_stat.setdefault("joins", [])
    recent_dup = any(
        j.get("user_id") == member.id and (now - j.get("time", 0)) < 60
        for j in existing_joins
    )
    if not recent_dup:
        c_stat["count"] = c_stat.get("count", 0) + 1
        existing_joins.append({
            "time": now,
            "chat_id": chat_id,
            "user_id": member.id,
            "user_name": member.first_name,
            "link": link_url,
            "link_name": link_title
        })

    # در صورت وجود رکورد قدیمی بدون نام (primary)، ادغام با حساب مالک گروه
    if creator_id_str != "primary" and "primary" in link_join_history:
        prim = link_join_history.pop("primary", None)
        if prim:
            c_stat["count"] = c_stat.get("count", 0) + prim.get("count", 0)
            for pj in prim.get("joins", []):
                if pj.get("user_id") not in [x.get("user_id") for x in existing_joins]:
                    existing_joins.append(pj)

    save_state()
    logger.info(f"ورود با لینک ثبت گردید: عضو {member.id} ({member.first_name}) توسط {creator_name} ({creator_id_str})")
    return link_details_log

# ---------------------------------------------------------------------------
# ۸. هسته مرکزی پردازش عضویت و افزودن اعضا (Core Join & Add Processor)
# ---------------------------------------------------------------------------
async def process_member_join_or_add(
    client: Client,
    chat_id: int,
    member: User,
    inviter: Optional[User],
    invite_link: Optional[ChatInviteLink] = None
) -> None:
    """
    پردازش جامع رویداد پیوستن یا افزوده شدن عضو جدید به سوپرگروه:
    - تفکیک ورود خودکار با لینک از اد شدن توسط کاربر دیگر
    - شناسایی دقیق اینکه چه کسی سازنده لینک دعوت بوده است
    - محدودسازی موقت کاربر و ارسال کپچا
    - محاسبه سقف مجاز اد و اعمال واکنش متناسب در صورت نقض
    """
    # بررسی کش جلوگیری از تکرار
    if is_duplicate_event(chat_id, member.id):
        return

    # بررسی ربات بودن عضو اضافه شده: آیا خود بات حاضر است؟
    me = await client.get_me()
    if member.id == me.id:
        logger.info(f"ربات به گروه {chat_id} اضافه گردید.")
        return

    # آیا کاربر از ادمین‌های مجاز (اونر) است؟ ادمین‌ها از قوانین معاف هستند
    configured_admins = [int(a) for a in config.get("admin_ids", []) if a]
    is_member_admin = member.id in configured_admins

    # ---------------------------------------------------------
    # الف) حالت اول: کاربر خودش با لینک یا جستجو وارد شده است
    # ---------------------------------------------------------
    is_self_join = (inviter is None) or (inviter.id == member.id)

    if is_self_join:
        logger.info(f"Self-join detected: {member.first_name} ({member.id}) in chat {chat_id}")

        # ثبت لینک و دریافت توضیحات لاگ
        link_log_details = await record_invite_link_join(client, chat_id, member, invite_link)

        if config.get("modules", {}).get("captcha", True) and not is_member_admin:
            # ۱. محدود کردن موقت دسترسی ارسال پیام تا زمان حل کپچا
            try:
                await client.restrict_chat_member(
                    chat_id,
                    member.id,
                    restricted_chat_permissions()
                )
            except Exception as e:
                logger.warning(f"عدم امکان محدودسازی کاربر {member.id}: {e}")

            # ۲. ثبت در دیتابیس اعضای تأیید نشده برای عملیات /sweep و بن دستی از پیوی
            captcha_key = member_key(chat_id, member.id)
            unverified_joins[captcha_key] = {
                "chat_id": chat_id,
                "user_id": member.id,
                "join_time": time.time(),
                "first_name": member.first_name,
                "username": member.username or ""
            }
            save_state()

            # ۳. آماده‌سازی و ارسال دکمه شیشه‌ای کپچا
            timeout_sec = int(config.get("captcha", {}).get("timeout_seconds", 60))
            welcome_tmpl = config.get("captcha", {}).get("welcome_text", "")
            btn_label = config.get("captcha", {}).get("button_text", "🤖 من ربات نیستم")

            welcome_msg_text = welcome_tmpl.format_map(SafeDict(
                user=member.first_name,
                mention=member.mention,
                time=timeout_sec,
                user_id=member.id
            ))
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(btn_label, callback_data=f"verify:{member.id}")]
            ])

            try:
                captcha_msg = await client.send_message(chat_id, welcome_msg_text, reply_markup=keyboard)

                # ۴. استارت تسک تایمر کپچا
                timer_task = asyncio.create_task(
                    captcha_timeout_worker(client, chat_id, member.id, captcha_msg.id, member.first_name, timeout_sec)
                )
                pending_verifications[captcha_key] = {
                    "chat_id": chat_id,
                    "user_id": member.id,
                    "message_id": captcha_msg.id,
                    "task": timer_task
                }
            except Exception as e:
                logger.error(f"خطا در ارسال پیام کپچا به گروه: {e}")

            # ۵. ثبت رویداد در لاگ (فقط پیوی اونر) همراه با اطلاعات لینک
            await send_log(
                f"📥 **ورود عضو جدید به گروه**\n"
                f"👤 نام: {member.mention} (`{member.id}`)"
                f"{link_log_details}\n"
                f"💬 گروه: {group_title(chat_id)} (`{chat_id}`)\n"
                f"⏳ کپچا ارسال شد (مهلت: {timeout_sec} ثانیه)"
            )
        return

    # ---------------------------------------------------------
    # ب) حالت دوم: کاربر توسط شخص دیگری اد شده است (افزودن از مخاطبین)
    # ---------------------------------------------------------
    logger.info(f"Member add detected: {inviter.first_name} ({inviter.id}) added {member.first_name} ({member.id})")

    # 🔧 رفع باگ نسخه قبل: این متغیر پیش از استفاده تعریف می‌شد و باعث NameError می‌گشت
    is_inviter_admin = inviter.id in configured_admins

    # ۱. آیا کاربر اضافه شده یک ربات است؟ کاربران عادی به هیچ وجه اجازه افزودن ربات ندارند
    if member.is_bot and not is_inviter_admin:
        try:
            await client.ban_chat_member(chat_id, member.id)
        except Exception:
            pass
        # ارسال گزارش منحصراً به پیوی ادمین (هیچ پیامی به گروه ارسال نمی‌شود)
        await send_log(
            f"🚫 **مسدودسازی ربات اضافه شده توسط کاربر عادی**\n"
            f"👤 دعوت کننده: {inviter.mention} (`{inviter.id}`)\n"
            f"🤖 ربات مسدود شده: @{member.username or member.first_name} (`{member.id}`)\n"
            f"💬 گروه: {group_title(chat_id)} (`{chat_id}`)"
        )
        return

    # ۲. آیا شخص اد کننده (Inviter) ادمین مجاز ربات است؟ ادمین‌ها آزاد هستند
    if is_inviter_admin:
        await send_log(
            f"➕ **افزودن عضو توسط ادمین**\n"
            f"👑 ادمین: {inviter.mention} (`{inviter.id}`)\n"
            f"👤 کاربر اضافه شده: {member.mention} (`{member.id}`)\n"
            f"💬 گروه: {group_title(chat_id)} (`{chat_id}`)"
        )
        return

    # ۳. بررسی قفل بودن کامل اد کردن (اگر سقف اد روی ۰ تنظیم شده باشد)
    max_limit = int(config.get("anti_add", {}).get("max_adds_per_day", 3))
    if max_limit == 0 and config.get("modules", {}).get("anti_add", True):
        # افزودن عضو از مخاطبین کاملاً قفل است! عضو جدید فوراً اخراج می‌شود
        await kick_member(client, chat_id, member.id)
        # ارسال لاگ به پیوی ادمین (سکوت کامل در گروه)
        await send_log(
            f"⛔ **جلوگیری از افزودن عضو (قفل اد فعال است)**\n"
            f"👤 دعوت کننده: {inviter.mention} (`{inviter.id}`)\n"
            f"👥 کاربر اخراج شده: {member.mention} (`{member.id}`)\n"
            f"💬 گروه: {group_title(chat_id)} (`{chat_id}`)"
        )
        return

    # ۴. عضو اضافه شده در صورت فعال بودن کپچا باید کپچا حل کند
    if config.get("modules", {}).get("captcha", True):
        try:
            await client.restrict_chat_member(
                chat_id,
                member.id,
                restricted_chat_permissions()
            )
        except Exception:
            pass

        captcha_key = member_key(chat_id, member.id)
        unverified_joins[captcha_key] = {
            "chat_id": chat_id,
            "user_id": member.id,
            "join_time": time.time(),
            "first_name": member.first_name,
            "username": member.username or ""
        }
        save_state()

        timeout_sec = int(config.get("captcha", {}).get("timeout_seconds", 60))
        welcome_tmpl = config.get("captcha", {}).get("welcome_text", "")
        btn_label = config.get("captcha", {}).get("button_text", "🤖 من ربات نیستم")
        welcome_msg_text = welcome_tmpl.format_map(SafeDict(
            user=member.first_name,
            mention=member.mention,
            time=timeout_sec,
            user_id=member.id
        ))
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(btn_label, callback_data=f"verify:{member.id}")]
        ])

        try:
            captcha_msg = await client.send_message(chat_id, welcome_msg_text, reply_markup=keyboard)
            timer_task = asyncio.create_task(
                captcha_timeout_worker(client, chat_id, member.id, captcha_msg.id, member.first_name, timeout_sec)
            )
            pending_verifications[captcha_key] = {
                "chat_id": chat_id,
                "user_id": member.id,
                "message_id": captcha_msg.id,
                "task": timer_task
            }
        except Exception as e:
            logger.error(f"خطا در ارسال کپچا برای عضو اد شده: {e}")

    # ۵. ثبت در تاریخچه اد و بررسی سقف مجاز روزانه
    if config.get("modules", {}).get("anti_add", True):
        now = time.time()
        inviter_key = str(inviter.id)

        # ساختار یکپارچه دیکشنری جهت ثبت نام اد کننده و لیست اد شده‌ها
        entry = user_add_history.setdefault(inviter_key, {
            "name": inviter.first_name,
            "username": inviter.username or "",
            "adds": []
        })
        if isinstance(entry, list):
            entry = {"name": inviter.first_name, "username": inviter.username or "", "adds": entry}
            user_add_history[inviter_key] = entry

        entry["name"] = inviter.first_name
        entry["username"] = inviter.username or ""
        entry.setdefault("adds", []).append({
            "time": now,
            "chat_id": chat_id,
            "user_id": member.id,
            "name": member.first_name,
            "username": member.username or ""
        })

        # فیلتر کردن رکوردهای ۲۴ ساعت اخیر همین گروه (۸۶۴۰۰ ثانیه)
        cutoff_24h = now - 86400
        recent_adds = [
            x for x in entry["adds"]
            if x.get("time", 0) >= cutoff_24h and (x.get("chat_id") == chat_id or x.get("chat_id") is None)
        ]
        entry["adds"] = [x for x in entry["adds"] if x.get("time", 0) >= cutoff_24h]
        save_state()

        adds_count = len(recent_adds)

        # لاگ معمولی افزودن عضو از مخاطبین
        await send_log(
            f"➕ **افزودن عضو از مخاطبین**\n"
            f"👤 اضافه کننده: {inviter.mention} (`{inviter.id}`)\n"
            f"👥 عضو اضافه شده: {member.mention} (`{member.id}`)\n"
            f"📊 آمار اد ۲۴ ساعت: {adds_count}/{max_limit}\n"
            f"💬 گروه: {group_title(chat_id)} (`{chat_id}`)"
        )

        # بررسی نقض سقف مجاز روزانه
        if adds_count > max_limit:
            action = config.get("anti_add", {}).get("violation_action", "warn").lower()
            action_desc = ""

            if action == "kick":
                ok = await kick_member(client, chat_id, inviter.id)
                action_desc = "اخراج موقت اد کننده (Kick)" if ok else "خطا در اخراج اد کننده"
            elif action == "ban":
                try:
                    await client.ban_chat_member(chat_id, inviter.id)
                    action_desc = "مسدودسازی دائمی اد کننده (Ban)"
                except Exception as e:
                    action_desc = f"خطا در بن: {e}"
            else:
                action_desc = "فقط ثبت اخطار (بدون اخراج)"

            # اخراج عضو اضافه شده هنگام تخلف جهت جلوگیری از انباشت اکانت فیک
            kick_added_setting = config.get("anti_add", {}).get("kick_added_on_violation", True)
            if kick_added_setting:
                if await kick_member(client, chat_id, member.id):
                    action_desc += " + اخراج عضو اضافه شده"

            # تهیه لیست فرمت‌شده از اعضای اد شده توسط این فرد
            lines = []
            for idx, item in enumerate(recent_adds, 1):
                u_name = item.get("name", "کاربر")
                u_id = item.get("user_id")
                lines.append(f"{idx}. [{u_name}](tg://user?id={u_id}) (`{u_id}`)")
            members_list_str = "\n".join(lines)

            # ارسال گزارش تخلف فوری منحصراً به پیوی ادمین (هیچ پیامی به گروه ارسال نمی‌شود)
            await send_log(
                f"🚨 **هشدار فوری: نقض سقف اد مخاطب!**\n\n"
                f"👤 متخلف: {inviter.mention} (`{inviter.id}`)\n"
                f"📊 تعداد اد در ۲۴ ساعت: {adds_count} (سقف: {max_limit})\n"
                f"⚡ اقدام انجام شده: **{action_desc}**\n"
                f"💬 گروه: {group_title(chat_id)} (`{chat_id}`)\n\n"
                f"📋 **لیست کاربران اضافه شده:**\n{members_list_str}"
            )

# ---------------------------------------------------------------------------
# ۹. هندلرهای پایروگرام برای رویدادهای عضویت (Event Handlers)
# ---------------------------------------------------------------------------
@app.on_message(filters.new_chat_members)
async def on_new_chat_members_handler(client: Client, message: Message):
    """هندلر پیام‌های سیستمی ورود اعضا به گروه"""
    chat_id = message.chat.id
    register_known_group(chat_id, message.chat.title)
    inviter = message.from_user
    for member in message.new_chat_members:
        await process_member_join_or_add(client, chat_id, member, inviter, invite_link=None)

@app.on_chat_member_updated()
async def on_chat_member_updated_handler(client: Client, update: ChatMemberUpdated):
    """هندلر به‌روزرسانی وضعیت اعضا (پشتیبانی از سوپرگروه‌هایی با پیام‌های سیستمی مخفی و تشخیص لینک دعوت)"""
    old = update.old_chat_member
    new = update.new_chat_member
    if not new:
        return

    old_status = old.status if old else ChatMemberStatus.LEFT
    new_status = new.status

    was_not_in_group = old_status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]
    is_now_in_group = new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED]

    if was_not_in_group and is_now_in_group:
        chat_id = update.chat.id
        register_known_group(chat_id, update.chat.title)
        member = new.user
        inviter = update.from_user
        invite_link = update.invite_link
        await process_member_join_or_add(client, chat_id, member, inviter, invite_link=invite_link)

@app.on_message(filters.group)
async def on_group_activity_tracker(client: Client, message: Message):
    """ثبت خودکار سوپرگروه در حافظه کش دیتابیس در صورت مشاهده هرگونه فعالیت یا پیام"""
    if message.chat and message.chat.id < 0:
        cid_str = str(message.chat.id)
        if cid_str not in known_groups or known_groups[cid_str].get("title") != message.chat.title:
            register_known_group(message.chat.id, message.chat.title)

# ---------------------------------------------------------------------------
# ۱۰. هندلر کلیک دکمه کپچا (Callback Query Handler)
# ---------------------------------------------------------------------------
@app.on_callback_query(filters.regex(r"^verify:(\d+)$"))
async def on_captcha_callback(client: Client, query: CallbackQuery):
    """هندلر کلیک روی دکمه شیشه‌ای تأیید کپچا"""
    target_user_id = int(query.matches[0].group(1))

    # اگر کاربر دیگری روی دکمه کلیک کند
    if query.from_user.id != target_user_id:
        await query.answer("⚠️ این دکمه تأیید متعلق به شما نیست!", show_alert=True)
        return

    # کاربر مجاز دکمه را زد
    chat_id = query.message.chat.id
    captcha_key = member_key(chat_id, target_user_id)

    # ۱. کنسل کردن تایمر اخراج
    pending_info = pending_verifications.pop(captcha_key, None)
    if pending_info and pending_info.get("task"):
        pending_info["task"].cancel()

    # ۲. حذف از لیست unverified_joins چون کپچا با موفقیت حل شد
    unverified_joins.pop(captcha_key, None)
    save_state()

    # ۳. بازگرداندن دسترسی کامل ارسال پیام به کاربر
    #    (از لایه سازگاری استفاده می‌شود تا روی pyrogram/kurigram/pyrofork یکسان کار کند)
    try:
        await client.restrict_chat_member(
            chat_id,
            target_user_id,
            unrestricted_chat_permissions()
        )
    except Exception as e:
        logger.warning(f"عدم امکان آزادسازی پرمیشن کاربر {target_user_id}: {e}")

    await query.answer("✅ هویت شما با موفقیت تأیید شد. خوش آمدید!", show_alert=False)

    # ۴. ویرایش پیام کپچا به پیام موفقیت و حذف خودکار پس از چند ثانیه
    verified_text = config.get("captcha", {}).get("verified_text", "✅ هویت شما با موفقیت تأیید شد. خوش آمدید!")
    success_text = f"{verified_text}\n👤 {query.from_user.mention}"
    try:
        await query.message.edit_text(success_text)
        asyncio.create_task(auto_delete_message(client, chat_id, query.message.id, delay_seconds=8))
    except Exception:
        pass

    # ۵. ارسال لاگ به پیوی اونر
    await send_log(
        f"✅ **تأیید موفقیت‌آمیز کپچا**\n"
        f"👤 کاربر: {query.from_user.mention} (`{query.from_user.id}`)\n"
        f"💬 گروه: {group_title(chat_id)} (`{chat_id}`)"
    )

# ---------------------------------------------------------------------------
# ۱۰.۵. هسته مدیریت اعضا: بن و آزادسازی از پیوی اونر (PV Moderation Core)
# ---------------------------------------------------------------------------
class TargetUser:
    """
    نمایش سبک‌وزن و یکدست از «کاربر هدف» عملیات مدیریتی.
    برای کاربرانی که پروفایلشان با get_users قابل دریافت نیست (اکانت حذف‌شده یا
    محدودیت حریم خصوصی) هم قابل ساخت است تا بن با آیدی عددی همیشه ممکن بماند.
    """
    __slots__ = ("id", "first_name", "username", "is_bot")

    def __init__(self, user_id: Any, first_name: str = "", username: str = "", is_bot: bool = False):
        self.id = int(user_id)
        self.first_name = (first_name or "").strip() or f"کاربر {user_id}"
        self.username = (username or "").strip().lstrip("@")
        self.is_bot = bool(is_bot)

    @property
    def mention(self) -> str:
        return f"[{self.first_name}](tg://user?id={self.id})"

    @property
    def uname_label(self) -> str:
        return f"@{self.username}" if self.username else "—"

    @property
    def short_name(self) -> str:
        name = self.first_name if len(self.first_name) <= 22 else self.first_name[:21] + "…"
        return name


def as_target(user: Any) -> TargetUser:
    """تبدیل آبجکت User پایروگرام یا TargetUser به TargetUser یکدست"""
    if isinstance(user, TargetUser):
        return user
    return TargetUser(
        getattr(user, "id", 0) or 0,
        getattr(user, "first_name", "") or "",
        getattr(user, "username", "") or "",
        bool(getattr(user, "is_bot", False))
    )


def is_protected_user(user_id: Any) -> bool:
    """کاربرانی که هرگز نباید توسط ربات بن شوند (اونر/ادمین‌های مجاز در config.json)"""
    return is_admin_user(user_id)


def find_cached_target(chat_id: Any, user_id: Any) -> Optional[TargetUser]:
    """جستجوی نام و یوزرنیم کاربر در حافظه ربات (بدون تماس با API تلگرام)"""
    uid = int(user_id)

    record = unverified_joins.get(member_key(chat_id, uid))
    if record:
        return TargetUser(uid, record.get("first_name", ""), record.get("username", ""))

    record = ban_records.get(member_key(chat_id, uid))
    if record:
        return TargetUser(uid, record.get("first_name", ""), record.get("username", ""))

    for data in link_join_history.values():
        for join in data.get("joins", []):
            if join.get("user_id") == uid:
                return TargetUser(uid, join.get("user_name", ""), "")

    for data in user_add_history.values():
        if isinstance(data, dict):
            adds = data.get("adds", [])
        elif isinstance(data, list):
            adds = data
        else:
            continue
        for add in adds:
            if add.get("user_id") == uid:
                return TargetUser(uid, add.get("name", ""), add.get("username", ""))

    return None


async def ensure_target(client: Client, chat_id: Any, user_id: Any) -> TargetUser:
    """ساخت TargetUser با اولویت: حافظه ربات ← API تلگرام ← برچسب آیدی"""
    cached = find_cached_target(chat_id, user_id)
    if cached and (cached.first_name or cached.username):
        return cached
    try:
        user = await client.get_users(int(user_id))
        return as_target(user)
    except Exception:
        return cached or TargetUser(user_id)


async def resolve_user_input(client: Client, raw: str) -> Tuple[Optional[TargetUser], str]:
    """
    تبدیل ورودی متنی اونر در پیوی به کاربر هدف.
    ورودی‌های معتبر: آیدی عددی، @username، username بدون @ یا لینک tg://user?id=...
    """
    text = (raw or "").strip()
    if not text:
        return None, "❌ ورودی خالی است؛ آیدی عددی یا یوزرنیم را بفرستید."

    if text.startswith("tg://user?id="):
        text = text.split("=", 1)[1]
    if text.startswith("https://t.me/"):
        text = text.replace("https://t.me/", "").split("/")[0]

    text = text.split()[0]

    # حالت آیدی عددی
    if text.lstrip("-").isdigit():
        uid = int(text)
        if uid <= 0:
            return None, "❌ آیدی عددی نامعتبر است (باید عدد مثبت باشد)."
        try:
            user = await client.get_users(uid)
            return as_target(user), ""
        except Exception:
            return TargetUser(uid), "⚠️ پروفایل این آیدی دریافت نشد (اکانت حذف‌شده یا محدود)؛ عملیات با آیدی عددی انجام می‌شود."

    # حالت یوزرنیم
    username = text.lstrip("@")
    if not username or len(username) < 4:
        return None, "❌ یوزرنیم نامعتبر است؛ باید حداقل ۴ کاراکتر باشد."
    try:
        user = await client.get_users(username)
        return as_target(user), ""
    except UsernameNotOccupied:
        return None, f"❌ یوزرنیم @{username} در تلگرام وجود ندارد."
    except FloodWait as e:
        wait = min(int(getattr(e, "value", 5) or 5), 60)
        return None, f"⏳ تلگرام موقتاً محدود کرده است؛ {wait} ثانیه دیگر دوباره تلاش کنید."
    except Exception as e:
        return None, f"❌ خطا در شناسایی کاربر: {e}"


async def get_bot_privileges(client: Client, chat_id: int) -> Tuple[bool, str]:
    """بررسی اینکه ربات در گروه ادمین است و دسترسی بن/محدودسازی اعضا را دارد"""
    try:
        me = await client.get_me()
    except Exception as e:
        return False, f"❌ عدم امکان دریافت مشخصات ربات: {e}"

    try:
        bot_member = await client.get_chat_member(chat_id, me.id)
    except UserNotParticipant:
        return False, "❌ ربات عضو این گروه نیست."
    except (PeerIdInvalid, UserIdInvalid):
        return False, "❌ شناسه گروه نامعتبر است یا ربات به آن دسترسی ندارد."
    except ChatAdminRequired:
        return False, "❌ ربات دسترسی لازم برای بررسی اعضا را ندارد."
    except Exception as e:
        return False, f"❌ خطا در بررسی دسترسی ربات: {e}"

    if bot_member.status == ChatMemberStatus.OWNER:
        return True, ""
    if bot_member.status != ChatMemberStatus.ADMINISTRATOR:
        return False, "❌ ربات در این گروه ادمین نیست؛ ابتدا آن را ادمین کنید."

    privileges = getattr(bot_member, "privileges", None)
    if not privileges or not getattr(privileges, "can_restrict_members", False):
        return False, "❌ ربات دسترسی «بن/محدودسازی اعضا» (Restrict Members) را ندارد."
    return True, ""


async def get_member_status(client: Client, chat_id: int, user_id: int) -> Tuple[Optional[Any], str]:
    """دریافت وضعیت عضویت یک کاربر در گروه (ChatMember یا None همراه با پیام خطا)"""
    try:
        return await client.get_chat_member(chat_id, user_id), ""
    except UserNotParticipant:
        return None, "LEFT"
    except (UserIdInvalid, PeerIdInvalid):
        return None, "INVALID"
    except Exception as e:
        return None, f"ERROR: {e}"


STATUS_LABELS: Dict[Any, str] = {
    ChatMemberStatus.OWNER: "👑 مالک گروه",
    ChatMemberStatus.ADMINISTRATOR: "🛡️ ادمین گروه",
    ChatMemberStatus.MEMBER: "👤 عضو عادی",
    ChatMemberStatus.RESTRICTED: "🔇 محدود شده",
    ChatMemberStatus.LEFT: "🚪 خارج شده",
    ChatMemberStatus.BANNED: "⛔ بن شده",
}


async def describe_member_in_group(client: Client, chat_id: int, target: TargetUser) -> str:
    """توصیف خوانای وضعیت فعلی کاربر در گروه برای نمایش در پنل پیوی"""
    member, err = await get_member_status(client, chat_id, target.id)
    if member is None:
        if err == "LEFT":
            return "👤 وضعیت فعلی در گروه: 🚪 خارج شده (در گروه نیست)"
        if err == "INVALID":
            return "👤 وضعیت فعلی در گروه: ⚠️ آیدی نامعتبر یا کاربر ناشناخته"
        return f"👤 وضعیت فعلی در گروه: ⚠️ {err}"

    label = STATUS_LABELS.get(member.status, str(member.status))
    line = f"👤 وضعیت فعلی در گروه: {label}"
    if member.status == ChatMemberStatus.BANNED:
        until = getattr(member, "until_date", None)
        if until and getattr(until, "year", 1970) > 1971:
            line += f" (تا {until.strftime('%Y-%m-%d %H:%M')})"
        else:
            line += " (دائمی)"
    if member.status == ChatMemberStatus.ADMINISTRATOR and getattr(member, "custom_title", None):
        line += f" — {member.custom_title}"
    return line


async def fetch_banned_members(client: Client, chat_id: int, limit: int = 100) -> Tuple[List[Any], str]:
    """دریافت لیست اعضای بن‌شده گروه مستقیماً از تلگرام"""
    items: List[Any] = []
    try:
        async for member in client.get_chat_members(chat_id, filter=ChatMembersFilter.BANNED, limit=limit):
            items.append(member)
    except ChatAdminRequired:
        return items, "❌ ربات دسترسی ادمین لازم برای خواندن لیست بن‌شده‌ها را ندارد."
    except UserAdminInvalid:
        return items, "❌ ربات اجازه دسترسی به لیست بن‌شده‌ها را ندارد."
    except FloodWait as e:
        wait = min(int(getattr(e, "value", 5) or 5), 60)
        return items, f"⏳ تلگرام موقتاً محدود کرده است؛ {wait} ثانیه دیگر تلاش کنید."
    except RPCError as e:
        return items, f"❌ خطای تلگرام در دریافت لیست بن‌شده‌ها: {e}"
    except Exception as e:
        return items, f"❌ خطا در دریافت لیست بن‌شده‌ها: {e}"
    return items, ""


def reason_key(admin_id: Any, chat_id: Any, user_id: Any) -> str:
    """کلید ذخیره موقت دلیل بن (چون callback_data تلگرام حداکثر ۶۴ بایت است)"""
    return f"{int(admin_id)}:{int(chat_id)}:{int(user_id)}"


def pop_ban_reason(admin_id: Any, chat_id: Any, user_id: Any) -> str:
    """خواندن و پاک کردن دلیل ذخیره‌شده برای یک عملیات بن"""
    return pending_ban_reasons.pop(reason_key(admin_id, chat_id, user_id), "")


def record_moderation(chat_id: Any, target: TargetUser, action: str, admin: Any = None,
                      reason: str = "", success: bool = True, auto: bool = False,
                      persist: bool = True) -> None:
    """ثبت سابقه بن/آزادسازی در bot_state.json برای گزارش‌گیری و لیست بن‌شده‌ها"""
    if not success:
        return
    key = member_key(chat_id, target.id)
    if action == "ban":
        ban_records[key] = {
            "chat_id": int(chat_id),
            "user_id": int(target.id),
            "first_name": target.first_name,
            "username": target.username,
            "by": int(admin.id) if getattr(admin, "id", None) else None,
            "by_name": getattr(admin, "first_name", None) or ("ربات (خودکار)" if auto else "سیستم"),
            "reason": (reason or "")[:200],
            "time": time.time(),
            "auto": bool(auto)
        }
    elif action == "unban":
        ban_records.pop(key, None)
    if persist:
        save_state()


async def apply_ban(client: Client, chat_id: int, target: TargetUser, admin: Any = None,
                    reason: str = "", auto: bool = False) -> Tuple[bool, str]:
    """
    🚫 بن دائمی یک عضو گروه — هسته اصلی ماژول «مدیریت اعضا از پیوی».
    تمامی بررسی‌های امنیتی پیش از اجرا انجام می‌شود تا مالک/ادمین گروه هرگز بن نشوند.
    """
    if is_protected_user(target.id):
        return False, "⛔ این کاربر در لیست مدیران مجاز ربات (admin_ids) است و بن نمی‌شود."

    ok, err = await get_bot_privileges(client, chat_id)
    if not ok:
        return False, err

    member, _m_err = await get_member_status(client, chat_id, target.id)
    if member is not None:
        if member.status == ChatMemberStatus.OWNER:
            return False, "⛔ هدف، مالک گروه است و امکان بن کردن او وجود ندارد."
        if member.status == ChatMemberStatus.ADMINISTRATOR:
            return False, "⛔ هدف ادمین گروه است؛ ابتدا او را از ادمینی برکنار کنید."
        if member.status == ChatMemberStatus.BANNED:
            return False, "ℹ️ این کاربر قبلاً در این گروه بن شده است."

    try:
        await client.ban_chat_member(chat_id, target.id)
    except FloodWait as e:
        wait = min(int(getattr(e, "value", 5) or 5), 60)
        await asyncio.sleep(wait)
        try:
            await client.ban_chat_member(chat_id, target.id)
        except Exception as e2:
            return False, f"❌ بن ناموفق پس از انتظار FloodWait: {e2}"
    except UserAdminInvalid:
        return False, "❌ تلگرام اجازه بن این کاربر را به ربات نداد (UserAdminInvalid)."
    except ChatAdminRequired:
        return False, "❌ ربات دسترسی ادمین لازم برای بن کردن را ندارد."
    except (UserIdInvalid, PeerIdInvalid):
        return False, "❌ آیدی کاربر نامعتبر است یا برای ربات ناشناخته است."
    except RPCError as e:
        return False, f"❌ خطای تلگرام: {e}"
    except Exception as e:
        return False, f"❌ خطای غیرمنتظره: {e}"

    # لغو تایمر کپچا تا بن به Kick تبدیل نشود و پاکسازی صف تأیید نشده‌ها
    cancel_pending_captcha(chat_id, target.id)
    # در عملیات دسته‌جمعی (Sweep) ذخیره‌سازی و لاگ تکی انجام نمی‌شود تا پیام‌ها رگباری نشوند
    record_moderation(chat_id, target, "ban", admin=admin, reason=reason, success=True,
                      auto=auto, persist=not auto)

    by_label = f"{admin.first_name} (`{admin.id}`)" if getattr(admin, "id", None) else "ربات (خودکار)"
    if not auto and get_setting("notifications", "notify_on_moderation", True):
        await send_log(
            f"🚫 **بن دستی عضو گروه از طریق پیوی**\n"
            f"👤 هدف: {target.mention} (`{target.id}`)\n"
            f"🔖 یوزرنیم: {target.uname_label}\n"
            f"💬 گروه: {group_title(chat_id)} (`{chat_id}`)\n"
            f"🛡️ توسط: {by_label}\n"
            f"📝 دلیل: {reason or '—'}",
            pv_only=True
        )
    logger.info(f"کاربر {target.id} در گروه {chat_id} توسط {by_label} بن شد. دلیل: {reason or '-'}")
    return True, "✅ کاربر با موفقیت در این گروه بن (مسدود دائمی) شد."


async def apply_unban(client: Client, chat_id: int, target: TargetUser, admin: Any = None,
                      reason: str = "") -> Tuple[bool, str]:
    """✅ آزادسازی (Unban) یک عضو بن‌شده تا بتواند دوباره وارد گروه شود"""
    ok, err = await get_bot_privileges(client, chat_id)
    if not ok:
        return False, err

    member, m_err = await get_member_status(client, chat_id, target.id)
    if member is not None and member.status not in (ChatMemberStatus.BANNED, ChatMemberStatus.LEFT):
        return False, "ℹ️ این کاربر بن نیست؛ نیازی به آزادسازی ندارد."
    if member is None and m_err == "INVALID":
        return False, "❌ آیدی کاربر نامعتبر است."

    try:
        await client.unban_chat_member(chat_id, target.id)
    except FloodWait as e:
        wait = min(int(getattr(e, "value", 5) or 5), 60)
        await asyncio.sleep(wait)
        try:
            await client.unban_chat_member(chat_id, target.id)
        except Exception as e2:
            return False, f"❌ آزادسازی ناموفق: {e2}"
    except UserAdminInvalid:
        return False, "❌ تلگرام اجازه آزادسازی این کاربر را به ربات نداد."
    except ChatAdminRequired:
        return False, "❌ ربات دسترسی ادمین لازم را ندارد."
    except RPCError as e:
        return False, f"❌ خطای تلگرام: {e}"
    except Exception as e:
        return False, f"❌ خطای غیرمنتظره: {e}"

    record_moderation(chat_id, target, "unban", admin=admin, reason=reason, success=True)
    ban_records.pop(member_key(chat_id, target.id), None)
    save_state()

    by_label = f"{admin.first_name} (`{admin.id}`)" if getattr(admin, "id", None) else "ربات"
    if get_setting("notifications", "notify_on_moderation", True):
        await send_log(
            f"✅ **آزادسازی (Unban) عضو گروه از طریق پیوی**\n"
            f"👤 هدف: {target.mention} (`{target.id}`)\n"
            f"💬 گروه: {group_title(chat_id)} (`{chat_id}`)\n"
            f"🛡️ توسط: {by_label}\n"
            f"📝 توضیح: {reason or '—'}\n"
            f"📌 کاربر اکنون می‌تواند دوباره وارد گروه شود (کپچا همچنان فعال است).",
            pv_only=True
        )
    logger.info(f"کاربر {target.id} در گروه {chat_id} آزاد (Unban) شد.")
    return True, "✅ کاربر آزاد شد و می‌تواند دوباره وارد گروه شود."


def count_group_items(chat_id: Any) -> Dict[str, int]:
    """شمارش سریع آیتم‌های یک گروه برای نمایش در منوها"""
    cid = int(chat_id)
    return {
        "unverified": sum(1 for d in unverified_joins.values() if d.get("chat_id") == cid),
        "banned": sum(1 for d in ban_records.values() if d.get("chat_id") == cid),
        "link_joins": sum(
            len([j for j in data.get("joins", []) if j.get("chat_id") == cid])
            for data in link_join_history.values()
        ),
        "contact_adds": sum(
            len([
                a for a in (data.get("adds", []) if isinstance(data, dict) else (data if isinstance(data, list) else []))
                if a.get("chat_id") == cid
            ])
            for data in user_add_history.values()
        ),
    }


def moderation_enabled() -> bool:
    """آیا ماژول مدیریت اعضا فعال است؟"""
    return bool(config.get("modules", {}).get("moderation", True))

# ---------------------------------------------------------------------------
# ۱۱. سازنده‌های منوهای شیشه‌ای و تعاملی (Interactive Menu Builders)
# ---------------------------------------------------------------------------
SEP = "──────────────────────"

MODULE_ICONS: List[Tuple[str, str, str]] = [
    ("captcha", "🤖 کپچای ورود", "🤖"),
    ("anti_add", "🚫 ضد اد مخاطب", "🚫"),
    ("panic", "🚨 وضعیت اضطراری", "🚨"),
    ("sweep", "🧹 پاکسازی Sweep", "🧹"),
    ("moderation", "🛡️ مدیریت اعضا (بن از پیوی)", "🛡️"),
    ("logging", "📋 لاگ در پیوی اونر", "📋"),
]


def _trim(text: Any, size: int = 24) -> str:
    """کوتاه کردن عنوان‌ها برای جا شدن در دکمه‌های شیشه‌ای"""
    value = str(text or "").strip() or "گروه"
    value = value.replace("\n", " ")
    return value if len(value) <= size else value[:size - 1] + "…"


def _switch(value: bool) -> str:
    return "🟢 فعال" if value else "🔴 خاموش"


def modules_badges() -> str:
    """خلاصه تک‌خطی وضعیت ماژول‌ها برای منوی اصلی"""
    modules = config.get("modules", {})
    return " ".join(f"{icon}{'✅' if modules.get(key, True) else '❌'}" for key, _label, icon in MODULE_ICONS)


def paginate(items: List[Any], page: int, per_page: int) -> Tuple[List[Any], int, int]:
    """برش صفحه‌بندی‌شده یک لیست به همراه شماره صفحه معتبر و تعداد کل صفحات"""
    per_page = max(1, int(per_page))
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = max(0, min(int(page), total_pages - 1))
    start = page * per_page
    return items[start:start + per_page], page, total_pages


def pager_rows(cb_prefix: str, page: int, total_pages: int) -> List[List[InlineKeyboardButton]]:
    """ردیف دکمه‌های ناوبری صفحات (قبلی / شماره صفحه / بعدی)"""
    if total_pages <= 1:
        return []
    return [[
        InlineKeyboardButton("◀️ قبلی", callback_data=f"{cb_prefix}:{(page - 1) % total_pages}"),
        InlineKeyboardButton(f"📄 {page + 1} از {total_pages}", callback_data="noop:page"),
        InlineKeyboardButton("بعدی ▶️", callback_data=f"{cb_prefix}:{(page + 1) % total_pages}")
    ]]


def sorted_groups() -> List[Dict[str, Any]]:
    """لیست گروه‌های شناخته‌شده، مرتب‌شده بر اساس آخرین فعالیت"""
    return sorted(known_groups.values(), key=lambda g: g.get("updated_at", 0), reverse=True)


# ===========================================================================
# منوی اصلی و راهنما
# ===========================================================================
def build_main_menu(user: Optional[User] = None) -> Tuple[str, InlineKeyboardMarkup]:
    """منوی اصلی داشبورد هوشمند مدیریت ربات (بازطراحی نسخه ۴)"""
    user_name = user.first_name if user else "مدیر گرامی"
    user_id = user.id if user else "نامشخص"
    bot_label = f"@{BOT_ME.username}" if BOT_ME else "در حال اتصال…"

    text = (
        f"🛡️ **پنل مدیریت و امنیت سوپرگروه**\n"
        f"{SEP}\n"
        f"👤 اونر: **{user_name}** (`{user_id}`)\n"
        f"🤖 ربات: {bot_label} | نسخه `{BOT_VERSION}`\n"
        f"🟢 وضعیت: **آنلاین** — ⏱️ آپ‌تایم: {format_uptime(time.time() - BOT_START_TIME)}\n"
        f"{SEP}\n"
        f"👥 گروه‌های تحت پوشش: **{len(known_groups)}**\n"
        f"⏳ در انتظار حل کپچا: **{len(unverified_joins)}** نفر\n"
        f"🚫 سوابق بن ثبت‌شده: **{len(ban_records)}** مورد\n"
        f"🧩 ماژول‌ها: {modules_badges()}\n"
        f"{SEP}\n"
        f"🔒 **سیاست لاگ:** اعلان آنلاین/آفلاین شدن ربات فقط به پیوی شما ارسال می‌شود\n"
        f"و هیچ پیام لاگی به داخل گروه نمی‌رود.\n"
        f"{SEP}\n"
        f"👇 بخش مورد نظر را انتخاب کنید:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار و گزارش گروه‌ها", callback_data="menu:stats")],
        [
            InlineKeyboardButton("🚫 مدیریت اعضا (بن)", callback_data="mod:home"),
            InlineKeyboardButton("🚨 عملیات اضطراری", callback_data="menu:emergency")
        ],
        [
            InlineKeyboardButton("🧩 ماژول‌ها", callback_data="menu:settings"),
            InlineKeyboardButton("🛠️ پارامترها", callback_data="menu:params")
        ],
        [
            InlineKeyboardButton("🔔 لاگ و اعلان‌ها", callback_data="menu:logs"),
            InlineKeyboardButton("ℹ️ وضعیت سیستم", callback_data="menu:info")
        ],
        [
            InlineKeyboardButton("📚 راهنما", callback_data="menu:help"),
            InlineKeyboardButton("🔄 به‌روزرسانی پنل", callback_data="menu:refresh")
        ]
    ])
    return text, keyboard


def build_help_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """راهنمای کامل قابلیت‌ها و روش کار با ربات از پیوی"""
    text = (
        f"📚 **راهنمای سریع ربات محافظ گروه**\n"
        f"{SEP}\n"
        f"**۱) اتصال گروه**\n"
        f"ربات را در سوپرگروه عضو کرده و ادمین کنید؛ دسترسی‌های «Ban/Restrict Members»،\n"
        f"«Delete Messages» و «Invite Users» را به آن بدهید. گروه با اولین پیام به‌صورت خودکار ثبت می‌شود.\n\n"
        f"**۲) کپچای ورود**\n"
        f"عضو جدید محدود شده و باید ظرف مهلت تعیین‌شده دکمه تأیید را بزند؛ در غیر این صورت\n"
        f"اخراج (Kick) می‌شود و پیام کپچا از گروه پاک می‌گردد.\n\n"
        f"**۳) 🚫 بن کردن اعضای گروه از پیوی (جدید)**\n"
        f"• منوی اصلی ← «مدیریت اعضا» ← انتخاب گروه ← یکی از این روش‌ها:\n"
        f"   ▫️ لیست اعضای در انتظار کپچا (بن با یک دکمه)\n"
        f"   ▫️ لیست بن‌شده‌های گروه (آزادسازی با یک دکمه)\n"
        f"   ▫️ بن دستی با آیدی عددی یا @username\n"
        f"• یا پیام کاربر مورد نظر را به پیوی ربات **فوروارد** کنید تا پنل اقدام باز شود.\n"
        f"• گزارش هر بن/آزادسازی فقط به پیوی شما ارسال می‌شود؛ گروه هیچ پیامی دریافت نمی‌کند.\n\n"
        f"**۴) عملیات اضطراری**\n"
        f"• **Panic:** ابطال لینک دعوت فعلی و صدور لینک جدید\n"
        f"• **Sweep:** بن دسته‌جمعی اعضای تأیید نشده در بازه زمانی مشخص\n"
        f"• **قفل اد:** مسدودسازی فوری افزودن مخاطب (سقف ۰)\n\n"
        f"**۵) 🔔 سیاست لاگ‌ها (جدید)**\n"
        f"اعلان آنلاین/آفلاین/کرش ربات **فقط** به پیوی اونر می‌رود و هرگز در گروه منتشر نمی‌شود.\n"
        f"سایر لاگ‌های امنیتی نیز به پیوی می‌روند؛ ارسال به کانال لاگ اختیاری و پیش‌فرض خاموش است.\n\n"
        f"**۶) دستورات متنی پیوی**\n"
        f"`/start` پنل اصلی | `/help` راهنما | `/groups` لیست گروه‌ها\n"
        f"`/ban <group_id> <user_id|@username> [دلیل]` بن از راه دور\n"
        f"`/unban <group_id> <user_id|@username>` آزادسازی\n"
        f"`/id <@username|user_id>` شناسایی کاربر | `/status` وضعیت سیستم | `/cancel` لغو ورودی\n"
        f"{SEP}\n"
        f"🔐 تمامی منوها فقط برای آیدی‌های ثبت‌شده در `admin_ids` قابل مشاهده هستند و سایر افراد\n"
        f"هیچ پاسخی دریافت نمی‌کنند (سکوت مطلق)."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 رفتن به مدیریت اعضا", callback_data="mod:home")],
        [InlineKeyboardButton("🔔 تنظیمات لاگ و اعلان‌ها", callback_data="menu:logs")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
    ])
    return text, keyboard


# ===========================================================================
# منوی گروه‌ها و داشبوردها
# ===========================================================================
GROUP_MENU_TITLES: Dict[str, str] = {
    "stats": "📊 **انتخاب سوپرگروه جهت مشاهده آمار و گزارش‌ها:**",
    "panic": "🚨 **انتخاب سوپرگروه جهت فعال‌سازی حالت اضطراری (Panic):**",
    "sweep": "🧹 **انتخاب سوپرگروه جهت پاکسازی اعضای تأیید نشده (Sweep):**",
    "moderation": "🚫 **انتخاب سوپرگروه جهت مدیریت اعضا (بن/آزادسازی):**",
}


def build_groups_menu(purpose: str = "stats", page: int = 0) -> Tuple[str, InlineKeyboardMarkup]:
    """منوی انتخاب گروه با نشانگر وضعیت و صفحه‌بندی"""
    per_page = 8

    if not known_groups:
        text = (
            f"{GROUP_MENU_TITLES.get(purpose, '👥 **انتخاب سوپرگروه:**')}\n"
            f"{SEP}\n"
            f"ℹ️ هنوز گروهی در حافظه ربات ثبت نشده است.\n\n"
            f"📌 **راهنمای اتصال گروه:**\n"
            f"۱. ربات را به سوپرگروه خود اضافه کرده و ادمین کنید.\n"
            f"۲. به محض ارسال اولین پیام یا ورود عضو، گروه به‌صورت خودکار شناسایی و ثبت می‌شود."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 بازخوانی لیست", callback_data=f"menu:{purpose}")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
        ])
        return text, keyboard

    groups = sorted_groups()
    page_items, page, total_pages = paginate(groups, page, per_page)
    header = GROUP_MENU_TITLES.get(purpose, "👥 **انتخاب سوپرگروه:**")

    hint = ""
    if purpose == "moderation":
        hint = "\n💡 روی هر گروه بزنید تا لیست اعضای تأیید نشده، بن‌شده‌ها و بن دستی باز شود."
    text = (
        f"{header}\n"
        f"{SEP}\n"
        f"👥 تعداد گروه‌های ثبت‌شده: **{len(groups)}**{hint}\n"
        f"{SEP}"
    )

    buttons: List[List[InlineKeyboardButton]] = []
    for gdata in page_items:
        gid = gdata.get("id")
        label = f"👥 {_trim(gdata.get('title', gid))}"
        counts = count_group_items(gid)
        if counts["unverified"]:
            label += f" ⏳{counts['unverified']}"
        if purpose == "stats":
            cb = f"group:{gid}"
        elif purpose == "panic":
            cb = f"emerg_panic_confirm:{gid}"
        elif purpose == "sweep":
            cb = f"emerg_sweep_confirm:{gid}"
        elif purpose == "moderation":
            cb = f"mod:group:{gid}"
            if counts["banned"]:
                label += f" 🚫{counts['banned']}"
        else:
            cb = f"group:{gid}"
        buttons.append([InlineKeyboardButton(label, callback_data=cb)])

    if purpose == "stats" and len(known_groups) > 1:
        buttons.append([InlineKeyboardButton("🌐 گزارش تجمیعی کل گروه‌ها", callback_data="group:all")])

    buttons.extend(pager_rows(f"page:groups:{purpose}", page, total_pages))
    buttons.append([
        InlineKeyboardButton("🔄 به‌روزرسانی لیست", callback_data=f"menu:{purpose}"),
        InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
    ])
    return text, InlineKeyboardMarkup(buttons)


def build_group_picker_for_user(target: TargetUser, page: int = 0) -> Tuple[str, InlineKeyboardMarkup]:
    """انتخاب گروه برای اجرای عملیات روی یک کاربر مشخص (مثلاً پس از فوروارد پیام)"""
    groups = sorted_groups()
    page_items, page, total_pages = paginate(groups, page, 8)

    text = (
        f"🎯 **کاربر شناسایی شد:** {target.mention} (`{target.id}`)\n"
        f"{SEP}\n"
        f"👥 در کدام گروه عملیات انجام شود؟"
    )
    buttons: List[List[InlineKeyboardButton]] = []
    for gdata in page_items:
        gid = gdata.get("id")
        buttons.append([InlineKeyboardButton(f"👥 {_trim(gdata.get('title', gid))}", callback_data=f"mod:group_for:{gid}:{target.id}")])

    if not buttons:
        text += "\n\nℹ️ هنوز گروهی ثبت نشده است."

    buttons.extend(pager_rows(f"page:pickuser:{target.id}", page, total_pages))
    buttons.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")])
    return text, InlineKeyboardMarkup(buttons)


def build_group_dashboard(target_chat_id: Any) -> Tuple[str, InlineKeyboardMarkup]:
    """داشبورد اختصاصی هر گروه شامل آمار لینک‌ها، مخاطبین و کپچا"""
    is_all = (str(target_chat_id) == "all")
    if not is_all:
        try:
            target_chat_id = int(target_chat_id)
        except (TypeError, ValueError):
            pass

    group_title_str = group_title(target_chat_id)
    cid_label = "همه سوپرگروه‌ها" if is_all else f"`{target_chat_id}`"

    # ۱. آمار لینک‌های دعوت
    total_link_joins = 0
    top_link_str = "هنوز ثبت نشده"
    link_rank: List[Tuple[str, int]] = []
    for _cid, data in link_join_history.items():
        joins = [
            j for j in data.get("joins", [])
            if is_all or j.get("chat_id") == target_chat_id or j.get("chat_id") is None
        ]
        if joins:
            count = len(joins)
            total_link_joins += count
            link_rank.append((data.get("name", "نامشخص"), count))
    if link_rank:
        link_rank.sort(key=lambda x: x[1], reverse=True)
        top_link_str = f"{link_rank[0][0]} ({link_rank[0][1]} عضو)"

    # ۲. آمار اد مخاطبین
    total_contact_adds = 0
    top_contact_str = "هنوز ثبت نشده"
    add_rank: List[Tuple[str, int]] = []
    for _uid, data in user_add_history.items():
        raw_adds = data.get("adds", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        name = data.get("name", "کاربر") if isinstance(data, dict) else "کاربر"
        adds = [
            a for a in raw_adds
            if is_all or a.get("chat_id") == target_chat_id or a.get("chat_id") is None
        ]
        if adds:
            count = len(adds)
            total_contact_adds += count
            add_rank.append((name, count))
    if add_rank:
        add_rank.sort(key=lambda x: x[1], reverse=True)
        top_contact_str = f"{add_rank[0][0]} ({add_rank[0][1]} عضو)"

    # ۳. افراد منتظر حل کپچا و بن‌شده‌ها
    unverified_count = sum(
        1 for d in unverified_joins.values()
        if is_all or d.get("chat_id") == target_chat_id
    )
    banned_count = sum(
        1 for d in ban_records.values()
        if is_all or d.get("chat_id") == target_chat_id
    )

    max_limit = config.get("anti_add", {}).get("max_adds_per_day", 3)
    limit_str = "⛔ قفل کامل (۰)" if max_limit == 0 else f"{max_limit} اد در روز"

    text = (
        f"📍 **داشبورد گروه: {_trim(group_title_str, 40)}**\n"
        f"🆔 شناسه: {cid_label}\n"
        f"{SEP}\n"
        f"🔗 ورودی از لینک دعوت: `{total_link_joins}` عضو\n"
        f"👑 برترین دعوت‌کننده با لینک: **{top_link_str}**\n\n"
        f"👥 ورودی از اد مخاطبین: `{total_contact_adds}` عضو\n"
        f"🥇 برترین اد کننده مخاطب: **{top_contact_str}**\n\n"
        f"⏳ در انتظار کپچا: `{unverified_count}` نفر\n"
        f"🚫 بن‌شده توسط ربات: `{banned_count}` نفر\n"
        f"⚙️ سقف مجاز اد: `{limit_str}`\n"
        f"{SEP}\n"
        f"👇 برای گزارش‌ها یا اقدامات امنیتی انتخاب کنید:"
    )

    buttons: List[List[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton("🔗 گزارش لینک‌های دعوت", callback_data=f"rep_links:{target_chat_id}:0"),
            InlineKeyboardButton("👥 گزارش اد مخاطبین", callback_data=f"rep_adds:{target_chat_id}:0")
        ]
    ]

    if not is_all:
        buttons.append([
            InlineKeyboardButton("🚫 مدیریت اعضای گروه", callback_data=f"mod:group:{target_chat_id}")
        ])
        buttons.append([
            InlineKeyboardButton("🚨 Panic (ابطال لینک)", callback_data=f"emerg_panic_confirm:{target_chat_id}"),
            InlineKeyboardButton("🧹 پاکسازی Sweep", callback_data=f"emerg_sweep_confirm:{target_chat_id}")
        ])

    buttons.append([
        InlineKeyboardButton("🔄 به‌روزرسانی آمار", callback_data=f"group:{target_chat_id}"),
        InlineKeyboardButton("🔙 لیست گروه‌ها", callback_data="menu:stats")
    ])
    buttons.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")])
    return text, InlineKeyboardMarkup(buttons)


# ===========================================================================
# گزارش‌های تفکیکی (با دکمه بن سریع)
# ===========================================================================
def build_links_report(target_chat_id: Any, page: int = 0) -> Tuple[str, InlineKeyboardMarkup]:
    """گزارش رتبه‌بندی افرادی که با لینک دعوت عضو آورده‌اند"""
    is_all = (str(target_chat_id) == "all")
    if not is_all:
        try:
            target_chat_id = int(target_chat_id)
        except (TypeError, ValueError):
            pass
    target_title = group_title(target_chat_id)

    stats: List[Dict[str, Any]] = []
    total_joins = 0
    for creator_id, data in link_join_history.items():
        group_joins = [
            j for j in data.get("joins", [])
            if is_all or j.get("chat_id") == target_chat_id or j.get("chat_id") is None
        ]
        if group_joins:
            total_joins += len(group_joins)
            stats.append({
                "cid": creator_id,
                "name": data.get("name", "نامشخص"),
                "username": data.get("username", ""),
                "count": len(group_joins),
                "joins": group_joins
            })
    stats.sort(key=lambda x: x["count"], reverse=True)

    per_page = 3
    page_items, page, total_pages = paginate(stats, page, per_page)

    if not stats:
        text = (
            f"🔗 **گزارش لینک‌های دعوت**\n"
            f"📍 {_trim(target_title, 40)}\n"
            f"{SEP}\n"
            f"ℹ️ هنوز هیچ ورودی از طریق لینک دعوت ثبت نشده است.\n\n"
            f"📌 به محض ورود اولین کاربر با لینک، آمار و نام سازنده لینک اینجا نمایش داده می‌شود."
        )
        page_items = []
    else:
        lines = [
            f"🔗 **گزارش ورود با لینک دعوت**",
            f"📍 {_trim(target_title, 40)} | مجموع: **{total_joins}** عضو",
            SEP
        ]
        for rank, item in enumerate(page_items, start=(page * per_page) + 1):
            uname = f" (@{item['username']})" if item.get("username") else ""
            cid_desc = f" (`{item['cid']}`)" if item["cid"] != "primary" else ""
            lines.append(f"{rank}. 👑 **{item['name']}**{uname}{cid_desc}: **{item['count']} عضو**")
            for j in reversed(item["joins"][-3:]):
                j_name = j.get("user_name", "کاربر")
                j_id = j.get("user_id")
                j_title = j.get("link_name", "لینک")
                j_time = datetime.fromtimestamp(j.get("time", time.time())).strftime("%m-%d %H:%M")
                lines.append(f"   ▫️ [{j_name}](tg://user?id={j_id}) — _{j_title}_ ({j_time})")
            lines.append("")
        lines.append("💡 با دکمه‌های زیر می‌توانید سازنده لینک متخلف را مستقیم از پیوی بن کنید.")
        text = "\n".join(lines)

    buttons: List[List[InlineKeyboardButton]] = []
    for item in page_items:
        creator_id = str(item["cid"])
        if is_all or not creator_id.isdigit():
            continue
        buttons.append([InlineKeyboardButton(
            f"🚫 بن «{_trim(item['name'], 18)}» ({item['count']} عضو)",
            callback_data=f"rep_ban:{target_chat_id}:{creator_id}"
        )])

    buttons.extend(pager_rows(f"page:rep_links:{target_chat_id}", page, total_pages))
    buttons.append([InlineKeyboardButton("🔄 به‌روزرسانی گزارش", callback_data=f"rep_links:{target_chat_id}:{page}")])
    buttons.append([
        InlineKeyboardButton("🔙 داشبورد گروه", callback_data=f"group:{target_chat_id}"),
        InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
    ])
    return text, InlineKeyboardMarkup(buttons)


def build_adds_report(target_chat_id: Any, page: int = 0) -> Tuple[str, InlineKeyboardMarkup]:
    """گزارش رتبه‌بندی افرادی که از مخاطبین عضو اضافه کرده‌اند"""
    is_all = (str(target_chat_id) == "all")
    if not is_all:
        try:
            target_chat_id = int(target_chat_id)
        except (TypeError, ValueError):
            pass
    target_title = group_title(target_chat_id)

    stats: List[Dict[str, Any]] = []
    total_adds = 0
    for uid, data in user_add_history.items():
        if isinstance(data, dict):
            raw_adds = data.get("adds", [])
            name = data.get("name", "کاربر")
            username = data.get("username", "")
        elif isinstance(data, list):
            raw_adds = data
            name = "کاربر"
            username = ""
        else:
            continue

        group_adds = [
            a for a in raw_adds
            if is_all or a.get("chat_id") == target_chat_id or a.get("chat_id") is None
        ]
        if group_adds:
            total_adds += len(group_adds)
            stats.append({"uid": uid, "name": name, "username": username, "count": len(group_adds), "adds": group_adds})
    stats.sort(key=lambda x: x["count"], reverse=True)

    per_page = 3
    page_items, page, total_pages = paginate(stats, page, per_page)

    if not stats:
        text = (
            f"👥 **گزارش افزودن اعضا از مخاطبین**\n"
            f"📍 {_trim(target_title, 40)}\n"
            f"{SEP}\n"
            f"ℹ️ هنوز داده‌ای از اد کردن کاربران ثبت نشده است.\n\n"
            f"📌 به محض اینکه کاربری از Add Member فردی را اضافه کند، در این بخش رتبه‌بندی می‌شود."
        )
    else:
        lines = [
            f"👥 **گزارش اد اعضای گروه از مخاطبین**",
            f"📍 {_trim(target_title, 40)} | مجموع: **{total_adds}** عضو",
            SEP
        ]
        for rank, item in enumerate(page_items, start=(page * per_page) + 1):
            uname = f" (@{item['username']})" if item.get("username") else ""
            lines.append(f"{rank}. 👤 **{item['name']}**{uname} (`{item['uid']}`): **{item['count']} نفر**")
            for a in reversed(item["adds"][-3:]):
                a_name = a.get("name", "مخاطب")
                a_id = a.get("user_id")
                a_time = datetime.fromtimestamp(a.get("time", time.time())).strftime("%m-%d %H:%M")
                lines.append(f"   ▫️ [{a_name}](tg://user?id={a_id}) (`{a_id}`) — _{a_time}_")
            lines.append("")
        lines.append("💡 با دکمه‌های زیر می‌توانید فرد متخلف را مستقیم از پیوی بن کنید.")
        text = "\n".join(lines)

    buttons: List[List[InlineKeyboardButton]] = []
    for item in page_items:
        uid = str(item["uid"])
        if is_all or not uid.isdigit():
            continue
        buttons.append([InlineKeyboardButton(
            f"🚫 بن «{_trim(item['name'], 18)}» ({item['count']} اد)",
            callback_data=f"rep_ban:{target_chat_id}:{uid}"
        )])

    buttons.extend(pager_rows(f"page:rep_adds:{target_chat_id}", page, total_pages))
    buttons.append([InlineKeyboardButton("🔄 به‌روزرسانی گزارش", callback_data=f"rep_adds:{target_chat_id}:{page}")])
    buttons.append([
        InlineKeyboardButton("🔙 داشبورد گروه", callback_data=f"group:{target_chat_id}"),
        InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
    ])
    return text, InlineKeyboardMarkup(buttons)


# ===========================================================================
# 🚫 منوهای مدیریت اعضا (بن/آزادسازی از پیوی اونر)
# ===========================================================================
def build_group_moderation(chat_id: Any) -> Tuple[str, InlineKeyboardMarkup]:
    """پنل مدیریت اعضای یک گروه مشخص"""
    try:
        chat_id = int(chat_id)
    except (TypeError, ValueError):
        pass

    counts = count_group_items(chat_id)
    title = _trim(group_title(chat_id), 40)

    text = (
        f"🚫 **مدیریت اعضای گروه**\n"
        f"📍 {title} (`{chat_id}`)\n"
        f"{SEP}\n"
        f"⏳ در انتظار حل کپچا: **{counts['unverified']}** نفر\n"
        f"🚫 بن‌شده توسط ربات: **{counts['banned']}** نفر\n"
        f"🔗 ورود با لینک دعوت: **{counts['link_joins']}** نفر\n"
        f"👥 اد از مخاطبین: **{counts['contact_adds']}** نفر\n"
        f"{SEP}\n"
        f"**روش‌های بن کردن از پیوی:**\n"
        f"۱. از لیست اعضای تأیید نشده (یک دکمه)\n"
        f"۲. از لیست بن‌شده‌های گروه (برای آزادسازی)\n"
        f"۳. دستی با آیدی عددی یا @username\n"
        f"۴. فوروارد پیام کاربر به پیوی ربات\n"
        f"{SEP}\n"
        f"🔒 هیچ پیامی درباره این عملیات‌ها در گروه ارسال نمی‌شود."
    )

    buttons = [
        [InlineKeyboardButton(f"⏳ اعضای تأیید نشده ({counts['unverified']})", callback_data=f"mod:unverified:{chat_id}:0")],
        [InlineKeyboardButton(f"🚫 لیست بن‌شده‌های گروه ({counts['banned']})", callback_data=f"mod:banned:{chat_id}:0")],
        [InlineKeyboardButton("🎯 بن دستی (آیدی/یوزرنیم)", callback_data=f"mod:manual:{chat_id}")],
        [InlineKeyboardButton("🔍 بررسی وضعیت یک عضو", callback_data=f"mod:lookup:{chat_id}")],
        [InlineKeyboardButton("📊 داشبورد آمار گروه", callback_data=f"group:{chat_id}")],
        [InlineKeyboardButton("🔙 لیست گروه‌ها", callback_data="mod:home"), InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
    ]
    return text, InlineKeyboardMarkup(buttons)


def build_unverified_menu(chat_id: Any, page: int = 0) -> Tuple[str, InlineKeyboardMarkup]:
    """لیست اعضای در انتظار کپچا با دکمه بن برای هر نفر"""
    try:
        chat_id = int(chat_id)
    except (TypeError, ValueError):
        pass

    entries = [d for d in unverified_joins.values() if d.get("chat_id") == chat_id]
    entries.sort(key=lambda d: d.get("join_time", 0), reverse=True)

    per_page = max(1, int(get_setting("moderation", "unverified_page_size", 5)))
    page_items, page, total_pages = paginate(entries, page, per_page)

    now = time.time()
    if not entries:
        text = (
            f"⏳ **اعضای در انتظار حل کپچا**\n"
            f"📍 {_trim(group_title(chat_id), 40)} (`{chat_id}`)\n"
            f"{SEP}\n"
            f"✅ در حال حاضر هیچ عضو تأییدنشده‌ای در صف نیست.\n\n"
            f"📌 به محض ورود عضو جدید و ارسال کپچا، نام او اینجا با دکمه بن ظاهر می‌شود."
        )
    else:
        lines = [
            f"⏳ **اعضای در انتظار حل کپچا**",
            f"📍 {_trim(group_title(chat_id), 40)} | تعداد: **{len(entries)}** نفر",
            SEP
        ]
        for idx, d in enumerate(page_items, start=(page * per_page) + 1):
            uid = d.get("user_id")
            name = d.get("first_name") or f"کاربر {uid}"
            uname = f" (@{d.get('username')})" if d.get("username") else ""
            elapsed = int(now - d.get("join_time", now))
            lines.append(f"{idx}. 👤 [{name}](tg://user?id={uid}){uname} — `{uid}` | ⏱️ {elapsed} ثانیه پیش")
        lines.append("")
        lines.append("👇 با دکمه‌های زیر هر نفر را مستقیم بن کنید (بدون هیچ پیامی در گروه):")
        text = "\n".join(lines)

    buttons: List[List[InlineKeyboardButton]] = []
    for d in page_items:
        uid = d.get("user_id")
        name = _trim(d.get("first_name") or f"کاربر {uid}", 18)
        buttons.append([
            InlineKeyboardButton(f"⛔ بن «{name}»", callback_data=f"mod:ban_confirm:{chat_id}:{uid}"),
            InlineKeyboardButton("🔎", callback_data=f"mod:info:{chat_id}:{uid}")
        ])

    buttons.extend(pager_rows(f"page:unverified:{chat_id}", page, total_pages))
    buttons.append([
        InlineKeyboardButton("🔄 به‌روزرسانی", callback_data=f"mod:unverified:{chat_id}:{page}"),
        InlineKeyboardButton("🔙 پنل گروه", callback_data=f"mod:group:{chat_id}")
    ])
    buttons.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")])
    return text, InlineKeyboardMarkup(buttons)


def build_banned_menu(chat_id: Any, members: List[Any], note: str = "", page: int = 0) -> Tuple[str, InlineKeyboardMarkup]:
    """لیست بن‌شده‌های گروه (از تلگرام + سوابق ربات) با دکمه آزادسازی"""
    try:
        chat_id = int(chat_id)
    except (TypeError, ValueError):
        pass

    merged: Dict[int, Dict[str, Any]] = {}
    for member in members or []:
        user = getattr(member, "user", None)
        if not user:
            continue
        merged[int(user.id)] = {
            "user_id": int(user.id),
            "first_name": user.first_name or f"کاربر {user.id}",
            "username": user.username or "",
            "source": "telegram",
            "reason": "",
            "by_name": "",
            "time": None
        }

    for record in ban_records.values():
        if record.get("chat_id") != chat_id:
            continue
        uid = int(record.get("user_id"))
        if uid in merged:
            merged[uid]["reason"] = record.get("reason", "")
            merged[uid]["by_name"] = record.get("by_name", "")
            merged[uid]["time"] = record.get("time")
            merged[uid]["source"] = "both"
        else:
            merged[uid] = {
                "user_id": uid,
                "first_name": record.get("first_name") or f"کاربر {uid}",
                "username": record.get("username", ""),
                "source": "bot",
                "reason": record.get("reason", ""),
                "by_name": record.get("by_name", ""),
                "time": record.get("time")
            }

    items = list(merged.values())
    items.sort(key=lambda x: x.get("time") or 0, reverse=True)

    per_page = max(1, int(get_setting("moderation", "banned_page_size", 5)))
    page_items, page, total_pages = paginate(items, page, per_page)

    header = (
        f"🚫 **بن‌شده‌های گروه**\n"
        f"📍 {_trim(group_title(chat_id), 40)} (`{chat_id}`)\n"
        f"{SEP}"
    )
    if not items:
        text = (
            f"{header}\n"
            f"✅ لیست بن‌شده‌ها خالی است (یا ربات دسترسی خواندن آن را ندارد).\n\n"
            f"📌 بن‌های انجام‌شده توسط ربات در این لیست با دلیل و نام مجری ثبت می‌شوند."
        )
    else:
        lines = [header, f"👥 تعداد: **{len(items)}** کاربر", ""]
        for idx, item in enumerate(page_items, start=(page * per_page) + 1):
            uid = item["user_id"]
            uname = f" (@{item['username']})" if item.get("username") else ""
            when = ""
            if item.get("time"):
                when = " — " + datetime.fromtimestamp(item["time"]).strftime("%m-%d %H:%M")
            tag = {"telegram": "🌐 تلگرام", "bot": "🤖 ربات", "both": "🤖🌐 ربات+تلگرام"}.get(item["source"], "")
            lines.append(f"{idx}. ⛔ [{item['first_name']}](tg://user?id={uid}){uname} — `{uid}` {tag}{when}")
            if item.get("reason"):
                lines.append(f"   ▫️ دلیل: {item['reason']}")
            if item.get("by_name"):
                lines.append(f"   ▫️ مجری: {item['by_name']}")
        lines.append("")
        lines.append("👇 برای بازگرداندن دسترسی هر کاربر، دکمه آزادسازی او را بزنید:")
        text = "\n".join(lines)

    if note:
        text = f"{note}\n{text}"

    buttons: List[List[InlineKeyboardButton]] = []
    for item in page_items:
        buttons.append([
            InlineKeyboardButton(f"✅ آزادسازی «{_trim(item['first_name'], 16)}»", callback_data=f"mod:unban_confirm:{chat_id}:{item['user_id']}"),
            InlineKeyboardButton("🔎", callback_data=f"mod:info:{chat_id}:{item['user_id']}")
        ])

    buttons.extend(pager_rows(f"page:banned:{chat_id}", page, total_pages))
    buttons.append([
        InlineKeyboardButton("🔄 به‌روزرسانی لیست", callback_data=f"mod:banned:{chat_id}:{page}"),
        InlineKeyboardButton("🔙 پنل گروه", callback_data=f"mod:group:{chat_id}")
    ])
    buttons.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")])
    return text, InlineKeyboardMarkup(buttons)


def build_manual_ban_prompt(chat_id: Any, mode: str = "ban") -> Tuple[str, InlineKeyboardMarkup]:
    """راهنمای دریافت آیدی/یوزرنیم از اونر در پیوی (حالت ورودی متنی)"""
    try:
        chat_id = int(chat_id)
    except (TypeError, ValueError):
        pass

    if mode == "lookup":
        action_text = "**🔍 بررسی وضعیت یک عضو**"
        purpose = "وضعیت عضویت، ادمین بودن و سابقه بن کاربر را به شما نشان دهم."
    else:
        action_text = "**🎯 بن دستی عضو گروه**"
        purpose = "کاربر مورد نظر را شناسایی کنم و پنل تأیید بن را باز کنم."

    text = (
        f"{action_text}\n"
        f"📍 {_trim(group_title(chat_id), 40)} (`{chat_id}`)\n"
        f"{SEP}\n"
        f"⌨️ لطفاً یکی از موارد زیر را **همینجا در پیوی** بفرستید تا {purpose}\n\n"
        f"• آیدی عددی کاربر، مثال: `123456789`\n"
        f"• یوزرنیم کاربر، مثال: `@username`\n"
        f"• لینک پروفایل، مثال: `https://t.me/username`\n"
        f"• یا پیامی از آن کاربر را به پیوی ربات **فوروارد** کنید\n\n"
        f"💡 در حالت بن می‌توانید دلیل را هم اضافه کنید:\n"
        f"`123456789 تبلیغ ربات و اسپم`\n"
        f"{SEP}\n"
        f"⏳ منتظر ورودی شما هستم… برای لغو: `/cancel`"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ لغو و بازگشت", callback_data=f"mod:group:{chat_id}")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
    ])
    return text, keyboard


def build_target_actions(chat_id: Any, target: TargetUser, status_line: str = "", note: str = "") -> Tuple[str, InlineKeyboardMarkup]:
    """پنل اقدام روی یک کاربر مشخص: بن، آزادسازی، بررسی وضعیت"""
    try:
        chat_id = int(chat_id)
    except (TypeError, ValueError):
        pass

    protected = is_protected_user(target.id)
    lines = [
        f"🎯 **پنل اقدام روی کاربر**",
        f"👤 {target.mention} (`{target.id}`)",
        f"🔖 یوزرنیم: {target.uname_label}",
        f"📍 گروه: {_trim(group_title(chat_id), 40)} (`{chat_id}`)",
        SEP
    ]
    if status_line:
        lines.append(status_line)
    if protected:
        lines.append("🛡️ این کاربر در لیست مدیران مجاز ربات است و **بن نمی‌شود**.")
    if note:
        lines.append(note)
    lines.append(SEP)
    lines.append("👇 عملیات مورد نظر را انتخاب کنید:")

    buttons: List[List[InlineKeyboardButton]] = []
    if not protected:
        buttons.append([InlineKeyboardButton("⛔ بن دائمی در این گروه", callback_data=f"mod:ban_confirm:{chat_id}:{target.id}")])
    buttons.append([InlineKeyboardButton("✅ آزادسازی (Unban)", callback_data=f"mod:unban_confirm:{chat_id}:{target.id}")])
    buttons.append([InlineKeyboardButton("🔎 بررسی وضعیت در گروه", callback_data=f"mod:info:{chat_id}:{target.id}")])
    buttons.append([InlineKeyboardButton("🎯 بن کاربر دیگر", callback_data=f"mod:manual:{chat_id}")])
    buttons.append([
        InlineKeyboardButton("🔙 پنل مدیریت گروه", callback_data=f"mod:group:{chat_id}"),
        InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
    ])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


def build_ban_confirm(chat_id: Any, target: TargetUser, status_line: str = "", reason: str = "") -> Tuple[str, InlineKeyboardMarkup]:
    """صفحه تأییدیه بن دائمی (جلوگیری از بن اشتباهی)"""
    try:
        chat_id = int(chat_id)
    except (TypeError, ValueError):
        pass

    lines = [
        f"⚠️ **تأییدیه بن دائمی عضو گروه**",
        f"📍 گروه: {_trim(group_title(chat_id), 40)} (`{chat_id}`)",
        f"👤 کاربر: {target.mention} (`{target.id}`)",
        f"🔖 یوزرنیم: {target.uname_label}",
        SEP
    ]
    if status_line:
        lines.append(status_line)
    if reason:
        lines.append(f"📝 دلیل ثبت‌شده: {reason}")
    lines.extend([
        SEP,
        "با تأیید این عملیات:",
        "۱. کاربر فوراً از گروه حذف و ورود مجدد او مسدود می‌شود.",
        "۲. تایمر کپچای او لغو و از صف تأییدنشده‌ها پاک می‌شود.",
        "۳. گزارش کامل **فقط به پیوی شما** ارسال می‌شود (هیچ پیامی در گروه نمی‌رود).",
        SEP,
        "آیا مطمئن هستید؟"
    ])
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⛔ بله، همین الان بن کن", callback_data=f"mod:do_ban:{chat_id}:{target.id}")],
        [InlineKeyboardButton("❌ انصراف", callback_data=f"mod:group:{chat_id}"), InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
    ])
    return "\n".join(lines), keyboard


def build_unban_confirm(chat_id: Any, target: TargetUser, status_line: str = "") -> Tuple[str, InlineKeyboardMarkup]:
    """صفحه تأییدیه آزادسازی (Unban) کاربر بن‌شده"""
    try:
        chat_id = int(chat_id)
    except (TypeError, ValueError):
        pass

    lines = [
        f"✅ **تأییدیه آزادسازی (Unban) کاربر**",
        f"📍 گروه: {_trim(group_title(chat_id), 40)} (`{chat_id}`)",
        f"👤 کاربر: {target.mention} (`{target.id}`)",
        f"🔖 یوزرنیم: {target.uname_label}",
        SEP
    ]
    if status_line:
        lines.append(status_line)
    lines.extend([
        SEP,
        "پس از آزادسازی، کاربر می‌تواند دوباره با لینک دعوت وارد گروه شود",
        "و در صورت فعال بودن ماژول کپچا، باید مانند بقیه تأیید هویت کند.",
        SEP,
        "آیا مطمئن هستید؟"
    ])
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ بله، آزادسازی کن", callback_data=f"mod:do_unban:{chat_id}:{target.id}")],
        [InlineKeyboardButton("❌ انصراف", callback_data=f"mod:group:{chat_id}"), InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
    ])
    return "\n".join(lines), keyboard


def build_moderation_result(chat_id: Any, target: TargetUser, success: bool, message: str) -> Tuple[str, InlineKeyboardMarkup]:
    """نمایش نتیجه اجرای بن/آزادسازی"""
    try:
        chat_id = int(chat_id)
    except (TypeError, ValueError):
        pass

    icon = "✅" if success else "❌"
    text = (
        f"{icon} **نتیجه عملیات مدیریت عضو**\n"
        f"👤 کاربر: {target.mention} (`{target.id}`)\n"
        f"📍 گروه: {_trim(group_title(chat_id), 40)} (`{chat_id}`)\n"
        f"{SEP}\n"
        f"{message}\n"
        f"{SEP}\n"
        f"🔒 گزارش این عملیات فقط در پیوی شما ثبت شد؛ گروه هیچ پیامی دریافت نکرد."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 به‌روزرسانی لیست بن‌شده‌ها", callback_data=f"mod:banned:{chat_id}:0")],
        [InlineKeyboardButton("🎯 مدیریت کاربر دیگر", callback_data=f"mod:manual:{chat_id}")],
        [InlineKeyboardButton("🔙 پنل مدیریت گروه", callback_data=f"mod:group:{chat_id}"), InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
    ])
    return text, keyboard


# ===========================================================================
# منوهای تنظیمات
# ===========================================================================
def build_modules_settings_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """منوی دکمه‌ای سوئیچ ماژول‌های امنیتی"""
    modules = config.get("modules", {})

    lines = [
        "🧩 **مدیریت ماژول‌های امنیتی ربات**",
        SEP,
        "با کلیک روی هر دکمه، وضعیت آن ماژول بلافاصله تغییر می‌کند:",
        ""
    ]
    for key, label, icon in MODULE_ICONS:
        lines.append(f"{icon} {label.replace(icon + ' ', '', 1)}: {_switch(modules.get(key, True))}")
    lines.extend([
        "",
        SEP,
        "🔔 **نکته مهم:** اعلان آنلاین/آفلاین شدن ربات همیشه و فقط به پیوی اونر می‌رود",
        "و با خاموش کردن ماژول لاگ هم مسدود نمی‌شود.",
        SEP,
        "💡 _تغییرات بلافاصله در config.json ذخیره و بدون ری‌استارت اعمال می‌شوند._"
    ])

    buttons = [[InlineKeyboardButton(f"{icon} {label.split(' ', 1)[1] if ' ' in label else label}: {_switch(modules.get(key, True))}", callback_data=f"toggle:{key}:mods")]
               for key, label, icon in MODULE_ICONS]
    buttons.append([InlineKeyboardButton("🔔 تنظیمات لاگ و اعلان‌ها", callback_data="menu:logs")])
    buttons.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")])
    return "\n".join(lines), InlineKeyboardMarkup(buttons)


def build_notifications_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """🔔 منوی سیاست لاگ‌ها: پیوی اونر در برابر کانال لاگ"""
    modules = config.get("modules", {})
    pv_logs_on = modules.get("logging", True)
    channel_logs_on = bool(get_setting("notifications", "send_logs_to_channel", False))
    status_pv_only = bool(get_setting("notifications", "status_log_to_owner_pv", True))
    moderation_notify = bool(get_setting("notifications", "notify_on_moderation", True))

    channel = resolve_log_channel()
    if channel:
        if isinstance(channel, int) and is_protected_group(channel):
            channel_label = f"`{channel}` ⚠️ (یکی از گروه‌های محافظت‌شده — لاگ به آن ارسال نمی‌شود)"
        else:
            channel_label = f"`{channel}`"
    else:
        channel_label = "تنظیم نشده"

    text = (
        f"🔔 **سیاست لاگ و اعلان‌های ربات**\n"
        f"{SEP}\n"
        f"🟢 **اعلان وضعیت (آنلاین/آفلاین/کرش):** فقط پیوی اونر — {_switch(status_pv_only)}\n"
        f"   🔒 این اعلان‌ها تحت هیچ شرایطی به گروه یا کانال ارسال نمی‌شوند.\n\n"
        f"📋 **لاگ‌های امنیتی در پیوی اونر:** {_switch(pv_logs_on)}\n"
        f"📢 **ارسال لاگ به کانال لاگ:** {_switch(channel_logs_on)}\n"
        f"🚫 **گزارش بن/آزادسازی دستی:** {_switch(moderation_notify)}\n"
        f"📮 **کانال لاگ فعلی:** {channel_label}\n"
        f"{SEP}\n"
        f"💡 برای اتصال کانال لاگ، یک پیام از آن کانال را به پیوی ربات **فوروارد** کنید.\n"
        f"💡 اگر شناسه کانال لاگ برابر با یکی از گروه‌های شما باشد، ربات به‌صورت خودکار\n"
        f"از ارسال لاگ به آن خودداری می‌کند تا گروه آلوده نشود."
    )

    buttons = [
        [InlineKeyboardButton(f"📋 لاگ در پیوی: {_switch(pv_logs_on)}", callback_data="toggle:logging:logs")],
        [InlineKeyboardButton(f"📢 لاگ در کانال لاگ: {_switch(channel_logs_on)}", callback_data="toggle:channel_logs:logs")],
        [InlineKeyboardButton(f"🚫 گزارش بن/آزادسازی: {_switch(moderation_notify)}", callback_data="toggle:notify_moderation:logs")],
        [InlineKeyboardButton(f"🟢 اعلان وضعیت در پیوی: {_switch(status_pv_only)}", callback_data="toggle:status_log:logs")],
        [InlineKeyboardButton("🧪 تست لاگ (فقط پیوی شما)", callback_data="logs:test")]
    ]
    if channel:
        buttons.append([InlineKeyboardButton("🗑️ حذف کانال لاگ", callback_data="logs:unset")])
    buttons.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")])
    return text, InlineKeyboardMarkup(buttons)


def build_params_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """منوی تنظیم پارامترها و سقف‌های امنیتی"""
    captcha_time = config.get("captcha", {}).get("timeout_seconds", 60)
    max_limit = config.get("anti_add", {}).get("max_adds_per_day", 3)
    limit_str = "⛔ قفل کامل (۰)" if max_limit == 0 else f"{max_limit} عضو در روز"
    action = config.get("anti_add", {}).get("violation_action", "warn")
    fa_actions = {"warn": "⚠️ اخطار (Warn)", "kick": "👢 اخراج (Kick)", "ban": "⛔ مسدودسازی (Ban)"}
    action_str = fa_actions.get(action, action)
    retention_hours = config.get("sweep", {}).get("retention_hours", 24)
    page_size = get_setting("moderation", "banned_page_size", 5)

    text = (
        f"🛠️ **تنظیم پارامترها و سقف‌های امنیتی**\n"
        f"{SEP}\n"
        f"⏱️ مهلت حل کپچا: `{captcha_time}` ثانیه\n"
        f"👥 سقف مجاز اد در روز: `{limit_str}`\n"
        f"⚡ اقدام هنگام تخلف اد: `{action_str}`\n"
        f"⏳ بازه نگهداری Sweep: `{retention_hours}` ساعت\n"
        f"📄 اندازه صفحات لیست‌ها: `{page_size}` مورد\n"
        f"{SEP}\n"
        f"👇 پارامتر مورد نظر را برای ویرایش انتخاب کنید:"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏱️ زمان کپچا", callback_data="param:captcha"),
            InlineKeyboardButton("👥 سقف اد مخاطب", callback_data="param:addlimit")
        ],
        [
            InlineKeyboardButton("⚡ اقدام تخلف اد", callback_data="param:action"),
            InlineKeyboardButton("⏳ بازه Sweep", callback_data="param:sweep")
        ],
        [InlineKeyboardButton("📄 اندازه صفحات لیست‌ها", callback_data="param:pagesize")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
    ])
    return text, keyboard


def build_captcha_param_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """تنظیم زمان مهلت کپچا"""
    curr = config.get("captcha", {}).get("timeout_seconds", 60)
    text = (
        f"⏱️ **تنظیم مهلت حل کپچا**\n"
        f"{SEP}\n"
        f"مقدار فعلی: **{curr} ثانیه**\n\n"
        f"با دکمه‌های زیر زمان مهلت کاربر برای تأیید کپچا را تنظیم کنید:"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖ ۳۰s", callback_data="set_cap:step:-30"),
            InlineKeyboardButton("➖ ۱۰s", callback_data="set_cap:step:-10"),
            InlineKeyboardButton("➕ ۱۰s", callback_data="set_cap:step:10"),
            InlineKeyboardButton("➕ ۳۰s", callback_data="set_cap:step:30")
        ],
        [
            InlineKeyboardButton("۳۰ ثانیه", callback_data="set_cap:val:30"),
            InlineKeyboardButton("۶۰ ثانیه", callback_data="set_cap:val:60"),
            InlineKeyboardButton("۹۰ ثانیه", callback_data="set_cap:val:90"),
            InlineKeyboardButton("۱۲۰ ثانیه", callback_data="set_cap:val:120")
        ],
        [
            InlineKeyboardButton("🔙 پارامترها", callback_data="menu:params"),
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
        ]
    ])
    return text, keyboard


def build_addlimit_param_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """تنظیم سقف اد کردن مخاطب توسط کاربران"""
    curr = config.get("anti_add", {}).get("max_adds_per_day", 3)
    curr_str = "⛔ قفل کامل (۰ اد)" if curr == 0 else f"{curr} عضو در ۲۴ ساعت"
    text = (
        f"👥 **تنظیم سقف مجاز اد مخاطب در روز**\n"
        f"{SEP}\n"
        f"وضعیت فعلی: **{curr_str}**\n\n"
        f"اگر سقف را روی ۰ قرار دهید، افزودن عضو توسط اعضای عادی کاملاً قفل می‌شود:"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖ ۱ اد", callback_data="set_limit:step:-1"),
            InlineKeyboardButton("➕ ۱ اد", callback_data="set_limit:step:1")
        ],
        [
            InlineKeyboardButton("⛔ قفل کامل (0)", callback_data="set_limit:val:0"),
            InlineKeyboardButton("۱ عضو", callback_data="set_limit:val:1"),
            InlineKeyboardButton("۳ عضو", callback_data="set_limit:val:3"),
            InlineKeyboardButton("۵ عضو", callback_data="set_limit:val:5")
        ],
        [
            InlineKeyboardButton("🔙 پارامترها", callback_data="menu:params"),
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
        ]
    ])
    return text, keyboard


def build_action_param_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """تعیین نوع اقدام هنگام تخلف اد کردن بیش از حد"""
    curr = config.get("anti_add", {}).get("violation_action", "warn")
    fa_actions = {"warn": "⚠️ اخطار (Warn)", "kick": "👢 اخراج (Kick)", "ban": "⛔ مسدودسازی (Ban)"}
    text = (
        f"⚡ **اقدام انضباطی هنگام نقض سقف اد مخاطب**\n"
        f"{SEP}\n"
        f"اقدام فعلی: **{fa_actions.get(curr, curr)}**\n\n"
        f"در صورتی که کاربری بیش از سقف مجاز روزانه عضو اد کند، چه واکنشی انجام شود؟"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ فقط ثبت اخطار (Warn)", callback_data="set_act:warn")],
        [InlineKeyboardButton("👢 اخراج از سوپرگروه (Kick)", callback_data="set_act:kick")],
        [InlineKeyboardButton("⛔ مسدودسازی دائمی (Ban)", callback_data="set_act:ban")],
        [
            InlineKeyboardButton("🔙 پارامترها", callback_data="menu:params"),
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
        ]
    ])
    return text, keyboard


def build_sweep_param_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """تنظیم ساعات نگهداری اعضا برای عملیات Sweep"""
    curr = config.get("sweep", {}).get("retention_hours", 24)
    text = (
        f"⏳ **بازه زمانی نگهداری اعضا برای Sweep**\n"
        f"{SEP}\n"
        f"بازه فعلی: **{curr} ساعت اخیر**\n\n"
        f"عملیات Sweep اعضایی را که در این بازه کپچا را حل نکرده‌اند بن می‌کند:"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➖ ۱۲h", callback_data="set_swp:step:-12"),
            InlineKeyboardButton("➖ ۶h", callback_data="set_swp:step:-6"),
            InlineKeyboardButton("➕ ۶h", callback_data="set_swp:step:6"),
            InlineKeyboardButton("➕ ۱۲h", callback_data="set_swp:step:12")
        ],
        [
            InlineKeyboardButton("۱۲ ساعت", callback_data="set_swp:val:12"),
            InlineKeyboardButton("۲۴ ساعت", callback_data="set_swp:val:24"),
            InlineKeyboardButton("۴۸ ساعت", callback_data="set_swp:val:48"),
            InlineKeyboardButton("۷۲ ساعت", callback_data="set_swp:val:72")
        ],
        [
            InlineKeyboardButton("🔙 پارامترها", callback_data="menu:params"),
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
        ]
    ])
    return text, keyboard


def build_pagesize_param_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """تنظیم تعداد موارد نمایش داده‌شده در هر صفحه از لیست‌ها"""
    curr = int(get_setting("moderation", "banned_page_size", 5))
    text = (
        f"📄 **اندازه صفحات لیست‌ها**\n"
        f"{SEP}\n"
        f"مقدار فعلی: **{curr} مورد در هر صفحه**\n\n"
        f"این مقدار برای لیست اعضای تأیید نشده، بن‌شده‌ها و گزارش‌ها استفاده می‌شود."
    )
    buttons = [[
        InlineKeyboardButton("➖ ۱", callback_data="set_page:step:-1"),
        InlineKeyboardButton("➕ ۱", callback_data="set_page:step:1")
    ]]
    for value in (3, 5, 8, 10):
        buttons.append([InlineKeyboardButton(f"{value} مورد", callback_data=f"set_page:val:{value}")])
    buttons.append([
        InlineKeyboardButton("🔙 پارامترها", callback_data="menu:params"),
        InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
    ])
    return text, InlineKeyboardMarkup(buttons)


def build_emergency_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """مرکز عملیات اضطراری و پدافند"""
    max_limit = config.get("anti_add", {}).get("max_adds_per_day", 3)
    retention = config.get("sweep", {}).get("retention_hours", 24)
    pending = len(unverified_joins)
    lock_state = "⛔ قفل است" if max_limit == 0 else f"🟢 باز ({max_limit} اد در روز)"

    text = (
        f"🚨 **مرکز عملیات اضطراری و پدافند سوپرگروه**\n"
        f"{SEP}\n"
        f"در شرایط بحرانی یا هجوم ربات‌ها (Raid) این اقدامات فوری در دسترس هستند:\n\n"
        f"• **Panic:** ابطال فوری لینک دعوت فعلی و صدور لینک جدید\n"
        f"• **Sweep:** بن یکجای `{pending}` عضو تأیید نشده در `{retention}` ساعت اخیر\n"
        f"• **قفل اد:** مسدودسازی سریع افزودن مخاطب — وضعیت فعلی: {lock_state}\n"
        f"{SEP}\n"
        f"⚠️ همه این عملیات‌ها تأییدیه دومرحله‌ای دارند و گزارششان فقط به پیوی شما می‌رود."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚨 ابطال و صدور لینک جدید (Panic)", callback_data="menu:panic")],
        [InlineKeyboardButton("🧹 پاکسازی اعضای تأیید نشده (Sweep)", callback_data="menu:sweep")],
        [InlineKeyboardButton("⛔ قفل فوری افزودن مخاطب (سقف 0)", callback_data="emerg:lock_adds")],
        [InlineKeyboardButton("🚫 مدیریت دستی اعضا (بن)", callback_data="mod:home")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
    ])
    return text, keyboard


def build_system_info_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """نمایش مشخصات فنی سیستم و سیاست‌های امنیتی"""
    state_size = STATE_FILE.stat().st_size if STATE_FILE.exists() else 0
    config_size = CONFIG_FILE.stat().st_size if CONFIG_FILE.exists() else 0
    admin_list_str = ", ".join(f"`{x}`" for x in config.get("admin_ids", [])) or "تنظیم نشده"
    channel = resolve_log_channel()
    channel_str = f"`{channel}`" if channel else "تنظیم نشده"
    channel_logs_on = get_setting("notifications", "send_logs_to_channel", False)
    compat_warns = compatibility_warnings()

    text = (
        f"ℹ️ **اطلاعات سیستم و امنیت ربات**\n"
        f"{SEP}\n"
        f"🤖 **نسخه ربات:** `{BOT_VERSION} (Python 3.9–3.14 Compat)`\n"
        f"⏱️ **آپ‌تایم جاری:** {format_uptime(time.time() - BOT_START_TIME)}\n"
        f"🛡️ **اونر/مدیران مجاز:** {admin_list_str}\n"
        f"👥 **سوپرگروه‌های متصل:** `{len(known_groups)}` گروه\n"
        f"⏳ **در انتظار کپچا:** `{len(unverified_joins)}` نفر\n"
        f"🚫 **سوابق بن:** `{len(ban_records)}` مورد\n"
        f"📮 **کانال لاگ:** {channel_str} (ارسال لاگ: {_switch(bool(channel_logs_on))})\n"
        f"💾 **حجم فایل وضعیت:** `{round(state_size / 1024, 2)} KB` | **کانفیگ:** `{round(config_size / 1024, 2)} KB`\n"
        f"🐍 **پایتون:** `{platform.python_version()}` | **کتابخانه:** `{TELEGRAM_LIB} {TELEGRAM_LIB_VERSION}`\n"
        f"🔐 **شتاب رمزنگاری:** {_switch(CRYPTO_ACCELERATED)} (tgcrypto/tgcrypto2)\n"
        f"🧩 **وضعیت سازگاری:** {_switch(not compat_warns)}\n"
        f"📱 **پلتفرم:** `{platform.system()}` — سازگار با ترموکس، ویندوز و لینوکس\n"
        f"{SEP}\n"
        f"🔒 **سیاست امنیت لاگ:**\n"
        f"• اعلان آنلاین/آفلاین/کرش ربات: **فقط پیوی اونر** (قفل‌شده)\n"
        f"• هیچ لاگ امنیتی به داخل گروه‌های محافظت‌شده ارسال نمی‌شود\n"
        f"• عملیات بن/آزادسازی از پیوی، بدون هیچ پیامی در گروه اجرا می‌شود"
    )
    if compat_warns:
        text += (
            f"\n{SEP}\n"
            f"⚠️ **{len(compat_warns)} نکته سازگاری محیط اجرا** — برای دیدن دستور نصب صحیح، "
            f"دکمه «🧩 سازگاری پایتون و کتابخانه» را بزنید."
        )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ پینگ واقعی API تلگرام", callback_data="ping:check"),
            InlineKeyboardButton("🔔 لاگ و اعلان‌ها", callback_data="menu:logs")
        ],
        [InlineKeyboardButton("🧩 سازگاری پایتون و کتابخانه", callback_data="menu:compat")],
        [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data="menu:info")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
    ])
    return text, keyboard


def build_compat_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """
    گزارش سازگاری محیط اجرا: نسخه پایتون، کتابخانه تلگرام، شتاب رمزنگاری
    و دستورهای آماده‌کپی برای اصلاح محیط (سازگار با پایتون ۳.۹ تا ۳.۱۴).
    """
    info = runtime_report()
    py = info["python"]
    exe = sys.executable or "python"
    exe_cmd = f'"{exe}"' if " " in exe else exe
    warn_list = compatibility_warnings()
    warn_block = "\n".join(warn_list) if warn_list else "✅ هیچ هشدار سازگاری‌ای ثبت نشد؛ محیط اجرا استاندارد است."
    mixed_block = (
        f"🧨 **نصب تداخلی:** `{' + '.join(info['mixed'])}` (خطرناک — باید اصلاح شود)\n"
        if info["mixed"] else ""
    )

    text = (
        f"🧩 **سازگاری پایتون و کتابخانه‌ها**\n"
        f"{SEP}\n"
        f"🐍 **پایتون:** `{py}` ({platform.system()})\n"
        f"📦 **کتابخانه فعال:** `{info['library']} {info['library_version']}`\n"
        f"{mixed_block}"
        f"🔐 **شتاب رمزنگاری:** {_switch(info['crypto'])}\n"
        f"🩹 **لایه سازگاری فعال روی:** `{', '.join(info['patched']) or 'نیاز نبود'}`\n"
        f"{SEP}\n"
        f"{warn_block}\n"
        f"{SEP}\n"
        f"📋 **دستورهای نصب (PowerShell / CMD / ترموکس):**\n\n"
        f"۱) پایتون ۳.۹ تا ۳.۱۱ — Pyrogram رسمی:\n"
        f"`{exe_cmd} -m pip install -r requirements.txt`\n\n"
        f"۲) پایتون ۳.۱۲ / ۳.۱۳ / ۳.۱۴ — فورک به‌روز kurigram:\n"
        f"`{exe_cmd} -m pip uninstall -y pyrogram`\n"
        f"`{exe_cmd} -m pip install -r requirements.txt`\n\n"
        f"۳) بررسی نهایی:\n"
        f"`{exe_cmd} -c \"import pyrogram,sys;print(sys.version.split()[0], pyrogram.__version__)\"`\n\n"
        f"💡 فایل `requirements.txt` خودش نسخه درست را بر اساس پایتون شما انتخاب می‌کند "
        f"(environment markers)؛ نیازی به ویرایش دستی نیست.\n"
        f"⚠️ اگر نصب `TgCrypto`/`tgcrypto2` روی سیستم شما شکست خورد (نبود کامپایلر)، "
        f"ربات بدون آن هم کار می‌کند؛ فقط کتابخانه اصلی را نصب کنید."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("ℹ️ بازگشت به وضعیت سیستم", callback_data="menu:info")],
        [InlineKeyboardButton("🔄 به‌روزرسانی گزارش", callback_data="menu:compat")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
    ])
    return text, keyboard

# ---------------------------------------------------------------------------
# ۱۲. دستورات متنی و ورودی پیوی اونر (Private Commands & Input State)
# ---------------------------------------------------------------------------
CANCEL_WORDS = {"cancel", "لغو", "انصراف", "بیخیال", "خروج", "stop"}


def _to_int(value: Any, default: int = 0) -> int:
    """تبدیل امن مقدار به عدد صحیح"""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _split_callback(data: str) -> List[str]:
    """تجزیه callback_data به اجزای جداشده با «:»"""
    return (data or "").split(":")


async def resolve_chat_input(client: Client, raw: str) -> Tuple[Optional[int], str]:
    """
    تبدیل ورودی گروه (آیدی عددی منفی یا @username گروه) به شناسه معتبر.
    خروجی: (chat_id یا None، پیام خطا)
    """
    text = (raw or "").strip()
    if not text:
        return None, "❌ شناسه گروه وارد نشده است."

    if text.startswith("@") or (not text.lstrip("-").isdigit()):
        try:
            chat = await client.get_chat(text)
        except Exception as e:
            return None, f"❌ گروه «{text}» پیدا نشد: {e}"
        if chat.id >= 0:
            return None, "❌ این شناسه یک چت شخصی است، نه گروه."
        if str(chat.id) not in known_groups:
            register_known_group(chat.id, chat.title)
        return chat.id, ""

    chat_id = int(text)
    if chat_id >= 0:
        return None, "❌ شناسه گروه باید عدد منفی باشد (مثال: `-1001234567890`). مقدار داده‌شده شبیه آیدی کاربر است."
    return chat_id, ""


async def _reply_panel(message: Message, builder_result: Tuple[str, InlineKeyboardMarkup]) -> None:
    """ارسال یک پنل آماده (متن + کیبورد) در پاسخ به پیام اونر"""
    text, keyboard = builder_result
    await message.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)


# ---------------------------------------------------------------------------
# ⌨️ ماشین حالت ورودی متنی پیوی (بن دستی / بررسی وضعیت عضو)
# ---------------------------------------------------------------------------
@app.on_message(filters.private & (filters.text | filters.forwarded))
async def handle_admin_input(client: Client, message: Message):
    """
    دریافت آیدی/یوزرنیم یا پیام فورواردشده از اونر در پیوی برای اجرای عملیات مدیریتی.
    این هندلر باید پیش از هندلرهای دستوری ثبت شود و فقط ورودی‌های غیردستوری را مصرف می‌کند.
    """
    if not message.from_user or not is_admin_user(message.from_user.id):
        return  # سکوت مطلق برای افراد غیرمجاز

    admin_id = message.from_user.id
    text = (message.text or "").strip()
    state = pending_admin_input.get(admin_id)

    # هیچ حالت فعالی وجود ندارد
    if not state:
        if text and not text.startswith("/") and not is_forwarded_message(message):
            await message.reply_text(
                f"ℹ️ **هیچ عملیات نیمه‌تمامی در انتظار ورودی نیست.**\n"
                f"{SEP}\n"
                f"برای بن کردن اعضای گروه از پیوی، از مسیر زیر اقدام کنید:\n"
                f"🏠 منوی اصلی ← 🚫 مدیریت اعضا ← انتخاب گروه ← 🎯 بن دستی\n\n"
                f"یا پیام کاربر مورد نظر را به همین چت فوروارد کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚫 مدیریت اعضا (بن)", callback_data="mod:home")],
                    [InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
                ]),
                disable_web_page_preview=True
            )
        message.continue_propagation()
        return

    # دستورات حتی در حالت ورودی فعال هم اولویت دارند (مثل /cancel)
    if text.startswith("/"):
        message.continue_propagation()
        return

    action = state.get("action", "ban")
    chat_id = state.get("chat_id")

    # لغو حالت ورودی با کلمات لغو
    if text.lower() in CANCEL_WORDS or text in CANCEL_WORDS:
        pending_admin_input.pop(admin_id, None)
        await message.reply_text(
            "❌ عملیات لغو شد. هیچ کاربری بن یا بررسی نشد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پنل مدیریت گروه", callback_data=f"mod:group:{chat_id}")]]),
            disable_web_page_preview=True
        )
        message.stop_propagation()
        return

    target: Optional[TargetUser] = None
    note = ""
    reason = ""

    # حالت ۱: کاربر، پیام یک عضو را فوروارد کرده است
    forward_user = get_forward_user(message)
    forward_id = get_forward_user_id(message)
    if forward_user is not None:
        target = as_target(forward_user)
        note = "ℹ️ هدف از روی پیام فورواردشده شناسایی شد."
    elif forward_id:
        target = TargetUser(forward_id)
        note = "⚠️ ارسال‌کننده اصلی ناشناس است؛ فقط آیدی عددی در دسترس بود."
    elif text:
        # حالت ۲: ورودی متنی «آیدی/یوزرنیم [دلیل]»
        pieces = text.split(None, 1)
        target, note = await resolve_user_input(client, pieces[0])
        if len(pieces) > 1:
            reason = pieces[1].strip()[:200]
    else:
        await message.reply_text("❌ ورودی قابل تشخیص نبود؛ آیدی عددی یا @username بفرستید.")
        message.stop_propagation()
        return

    if not target:
        await message.reply_text(
            f"{note}\n\n⏳ همچنان منتظر ورودی معتبر هستم… برای لغو: `/cancel`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو", callback_data=f"mod:group:{chat_id}")]]),
            disable_web_page_preview=True
        )
        message.stop_propagation()
        return

    status_line = await describe_member_in_group(client, chat_id, target)

    if action == "lookup":
        pending_admin_input.pop(admin_id, None)
        await _reply_panel(message, build_target_actions(chat_id, target, status_line, note))
    else:
        pending_admin_input.pop(admin_id, None)
        if reason:
            pending_ban_reasons[reason_key(admin_id, chat_id, target.id)] = reason
        await _reply_panel(message, build_ban_confirm(chat_id, target, status_line, reason))

    message.stop_propagation()


# ---------------------------------------------------------------------------
# دستورات متنی پیوی اونر
# ---------------------------------------------------------------------------
@app.on_message(filters.command(["start", "panel", "menu", "پنل", "شروع"]) & filters.private)
async def handle_start_command(client: Client, message: Message):
    """
    دستور اصلی ربات: /start منحصراً در چت خصوصی (پیوی).
    کاربران غیرمجاز کاملاً نادیده گرفته می‌شوند (سکوت مطلق).
    """
    if not await is_admin(client, message):
        return
    pending_admin_input.pop(message.from_user.id, None)
    await _reply_panel(message, build_main_menu(message.from_user))


@app.on_message(filters.command(["help", "راهنما", "کمک"]) & filters.private)
async def handle_help_command(client: Client, message: Message):
    """نمایش راهنمای کامل قابلیت‌ها"""
    if not await is_admin(client, message):
        return
    await _reply_panel(message, build_help_menu())


@app.on_message(filters.command(["groups", "گروه", "گروهها", "گروه‌ها"]) & filters.private)
async def handle_groups_command(client: Client, message: Message):
    """لیست گروه‌های تحت پوشش"""
    if not await is_admin(client, message):
        return
    await _reply_panel(message, build_groups_menu(purpose="stats"))


@app.on_message(filters.command(["moderation", "ban_panel", "مدیریت", "اعضا"]) & filters.private)
async def handle_moderation_shortcut(client: Client, message: Message):
    """میان‌بر ورود مستقیم به مرکز مدیریت اعضا"""
    if not await is_admin(client, message):
        return
    if not moderation_enabled():
        await message.reply_text(
            "🛡️ ماژول مدیریت اعضا غیرفعال است؛ از منوی «🧩 ماژول‌ها» آن را روشن کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🧩 ماژول‌ها", callback_data="menu:settings")]]),
            disable_web_page_preview=True
        )
        return
    await _reply_panel(message, build_groups_menu(purpose="moderation"))


@app.on_message(filters.command(["status", "info", "وضعیت"]) & filters.private)
async def handle_status_command(client: Client, message: Message):
    """اطلاعات فنی و امنیتی ربات"""
    if not await is_admin(client, message):
        return
    await _reply_panel(message, build_system_info_menu())


@app.on_message(filters.command(["logs", "لاگ", "اعلان"]) & filters.private)
async def handle_logs_command(client: Client, message: Message):
    """سیاست لاگ و اعلان‌ها"""
    if not await is_admin(client, message):
        return
    await _reply_panel(message, build_notifications_menu())


@app.on_message(filters.command(["compat", "python", "install", "سازگاری", "نصب", "پایتون"]) & filters.private)
async def handle_compat_command(client: Client, message: Message):
    """گزارش سازگاری پایتون/کتابخانه و دستورهای نصب صحیح"""
    if not await is_admin(client, message):
        return
    await _reply_panel(message, build_compat_menu())


@app.on_message(filters.command(["cancel", "لغو", "انصراف"]) & filters.private)
async def handle_cancel_command(client: Client, message: Message):
    """لغو عملیات نیمه‌تمام و پاک کردن حالت ورودی"""
    if not await is_admin(client, message):
        return
    removed = pending_admin_input.pop(message.from_user.id, None)
    if removed:
        await message.reply_text(
            f"❌ عملیات «{removed.get('action')}» لغو شد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]]),
            disable_web_page_preview=True
        )
    else:
        await message.reply_text(
            "ℹ️ هیچ عملیات نیمه‌تمامی در جریان نبود.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]]),
            disable_web_page_preview=True
        )


async def _handle_remote_moderation_command(client: Client, message: Message, want_ban: bool) -> None:
    """
    هسته مشترک دستورات /ban و /unban در پیوی:
      /ban   <group_id|@group> <user_id|@username> [دلیل]
      /unban <group_id|@group> <user_id|@username>
    """
    if not await is_admin(client, message):
        return

    args = list(message.command[1:]) if message.command else []
    admin = message.from_user

    if not args:
        usage = (
            f"{'⛔ بن' if want_ban else '✅ آزادسازی'} از راه دور\n"
            f"{SEP}\n"
            f"فرمت دستور:\n"
            f"`/{'ban' if want_ban else 'unban'} <group_id> <user_id|@username>{' [دلیل]' if want_ban else ''}`\n\n"
            f"مثال:\n"
            f"`/{'ban' if want_ban else 'unban'} -1001234567890 987654321{' اسپم و تبلیغ' if want_ban else ''}`\n"
            f"`/{'ban' if want_ban else 'unban'} @mygroup @username`\n\n"
            f"💡 راحت‌تر: پیام کاربر را به پیوی ربات فوروارد کنید یا از منوی «🚫 مدیریت اعضا» استفاده نمایید."
        )
        await message.reply_text(
            usage,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚫 مدیریت اعضا (منو)", callback_data="mod:home")],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
            ]),
            disable_web_page_preview=True
        )
        return

    chat_id, err = await resolve_chat_input(client, args[0])
    if not chat_id:
        await message.reply_text(err, disable_web_page_preview=True)
        return

    if len(args) == 1:
        # فقط گروه داده شده → ورود به حالت ورودی دستی
        if want_ban:
            pending_admin_input[admin.id] = {"action": "ban", "chat_id": chat_id, "started_at": time.time()}
            await _reply_panel(message, build_manual_ban_prompt(chat_id, mode="ban"))
        else:
            await message.reply_text(
                f"❌ برای آزادسازی، آیدی یا یوزرنیم کاربر را هم بنویسید:\n`/unban {args[0]} <user_id|@username>`",
                disable_web_page_preview=True
            )
        return

    target, note = await resolve_user_input(client, args[1])
    if not target:
        await message.reply_text(note or "❌ کاربر شناسایی نشد.", disable_web_page_preview=True)
        return

    reason = " ".join(args[2:]).strip()[:200] if (want_ban and len(args) > 2) else ""
    status_line = await describe_member_in_group(client, chat_id, target)

    if want_ban:
        if reason:
            pending_ban_reasons[reason_key(admin.id, chat_id, target.id)] = reason
        await _reply_panel(message, build_ban_confirm(chat_id, target, status_line, reason))
    else:
        await _reply_panel(message, build_unban_confirm(chat_id, target, status_line))

    if note:
        await message.reply_text(note, disable_web_page_preview=True)


@app.on_message(filters.command(["ban", "بن", "مسدود", "بن_کن"]) & filters.private)
async def handle_ban_command(client: Client, message: Message):
    """🚫 بن کردن عضو یک گروه از طریق پیوی اونر"""
    await _handle_remote_moderation_command(client, message, want_ban=True)


@app.on_message(filters.command(["unban", "آزاد", "آنبن", "رفع_بن"]) & filters.private)
async def handle_unban_command(client: Client, message: Message):
    """✅ آزادسازی (Unban) عضو بن‌شده از طریق پیوی اونر"""
    await _handle_remote_moderation_command(client, message, want_ban=False)


@app.on_message(filters.command(["id", "شناسه", "آیدی", "whois"]) & filters.private)
async def handle_id_command(client: Client, message: Message):
    """شناسایی کاربر و نمایش وضعیت او در همه گروه‌های تحت پوشش"""
    if not await is_admin(client, message):
        return

    target: Optional[TargetUser] = None
    args = list(message.command[1:]) if message.command else []

    if message.reply_to_message and message.reply_to_message.from_user:
        target = as_target(message.reply_to_message.from_user)
    elif args:
        target, note = await resolve_user_input(client, args[0])
        if not target:
            await message.reply_text(note or "❌ کاربر شناسایی نشد.", disable_web_page_preview=True)
            return
    else:
        await message.reply_text(
            f"🔎 **شناسایی کاربر**\n{SEP}\n"
            f"`/id @username` یا `/id 123456789`\n"
            f"همچنین می‌توانید روی پیام یک کاربر در پیوی ربات «ریپلای» کنید و `/id` بزنید.",
            disable_web_page_preview=True
        )
        return

    lines = [
        f"🔎 **شناسنامه کاربر**",
        f"👤 {target.mention}",
        f"🆔 آیدی عددی: `{target.id}`",
        f"🔖 یوزرنیم: {target.uname_label}",
        SEP,
        f"**وضعیت در گروه‌های تحت پوشش:**"
    ]
    if not known_groups:
        lines.append("ℹ️ هنوز گروهی ثبت نشده است.")
    for gid_str, gdata in known_groups.items():
        gid = gdata.get("id")
        lines.append(f"▫️ {_trim(gdata.get('title', gid), 30)} (`{gid}`)")
        lines.append(f"   {await describe_member_in_group(client, gid, target)}")
        record = ban_records.get(member_key(gid, target.id))
        if record:
            when = datetime.fromtimestamp(record.get("time", time.time())).strftime("%Y-%m-%d %H:%M")
            lines.append(f"   📝 سابقه بن ربات: {when} توسط {record.get('by_name', '—')}")

    buttons = []
    for gid_str, gdata in list(known_groups.items())[:5]:
        gid = gdata.get("id")
        buttons.append([InlineKeyboardButton(f"🎯 اقدام در {_trim(gdata.get('title', gid), 18)}", callback_data=f"mod:group_for:{gid}:{target.id}")])
    buttons.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")])

    await message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)


# ---------------------------------------------------------------------------
# 📨 هندلر پیام‌های فورواردشده به پیوی (اتصال کانال لاگ + بن سریع کاربر)
# ---------------------------------------------------------------------------
@app.on_message(filters.private & filters.forwarded)
async def handle_private_forward(client: Client, message: Message):
    """
    دو کاربرد برای پیام فورواردشده به پیوی ربات:
    ۱. فوروارد از یک کانال → پیشنهاد اتصال/قطع آن به عنوان کانال لاگ
    ۲. فوروارد از یک کاربر → باز شدن پنل اقدام (بن/آزادسازی) برای همان کاربر
    """
    if not await is_admin(client, message):
        return

    # ۱) فوروارد از کانال → تنظیم کانال لاگ (با تأیید دکمه‌ای، نه خودکار)
    src_chat = get_forward_chat(message)
    if src_chat is not None and src_chat.type == ChatType.CHANNEL:
        current = resolve_log_channel()
        text = (
            f"📢 **کانال شناسایی شد:** {src_chat.title}\n"
            f"🆔 شناسه: `{src_chat.id}`\n"
            f"{SEP}\n"
            f"📮 کانال لاگ فعلی: {f'`{current}`' if current else 'تنظیم نشده'}\n\n"
            f"آیا این کانال به عنوان مقصد لاگ‌های امنیتی ثبت شود؟\n"
            f"🔒 توجه: لاگ آنلاین/آفلاین ربات همیشه فقط به پیوی شما می‌رود."
        )
        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ ثبت به عنوان کانال لاگ", callback_data=f"logs:set:{src_chat.id}")],
                [InlineKeyboardButton("🗑️ حذف کانال لاگ فعلی", callback_data="logs:unset")],
                [InlineKeyboardButton("🔔 سیاست لاگ‌ها", callback_data="menu:logs")]
            ]),
            disable_web_page_preview=True
        )
        return

    # ۲) فوروارد از کاربر → پنل بن/آزادسازی
    forward_user = get_forward_user(message)
    forward_id = get_forward_user_id(message)
    target: Optional[TargetUser] = None
    if forward_user is not None:
        target = as_target(forward_user)
    elif forward_id:
        target = TargetUser(forward_id)

    if target is None:
        await message.reply_text(
            f"ℹ️ **پیام فورواردشده قابل استفاده نیست.**\n{SEP}\n"
            f"📌 برای بن کردن یک کاربر از پیوی، پیامی از او را فوروارد کنید که «نام ارسال‌کننده»\n"
            f"در آن مخفی نشده باشد؛ یا آیدی عددی/یوزرنیم او را از منوی «🚫 مدیریت اعضا» بفرستید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚫 مدیریت اعضا", callback_data="mod:home")]]),
            disable_web_page_preview=True
        )
        return

    if not known_groups:
        await message.reply_text(
            f"👤 **کاربر شناسایی شد:** {target.mention} (`{target.id}`)\n"
            f"{SEP}\n"
            f"❌ هنوز هیچ گروهی در حافظه ربات ثبت نشده است؛ ابتدا ربات را در سوپرگروه ادمین کنید.",
            disable_web_page_preview=True
        )
        return

    if not moderation_enabled():
        await message.reply_text(
            "🛡️ ماژول مدیریت اعضا غیرفعال است؛ از منوی «🧩 ماژول‌ها» آن را روشن کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🧩 ماژول‌ها", callback_data="menu:settings")]]),
            disable_web_page_preview=True
        )
        return

    if len(known_groups) == 1:
        gid = next(iter(known_groups.values())).get("id")
        status_line = await describe_member_in_group(client, gid, target)
        await _reply_panel(message, build_target_actions(gid, target, status_line, "ℹ️ هدف از پیام فورواردشده شناسایی شد."))
    else:
        await _reply_panel(message, build_group_picker_for_user(target))

# ---------------------------------------------------------------------------
# ۱۲.۵. روتر جامع دکمه‌های شیشه‌ای پنل مدیریت (Admin Callback Query Router)
# ---------------------------------------------------------------------------
@app.on_callback_query(filters.regex(r"^(menu|group|rep_|toggle|param|set_|emerg|exec_|ping|mod:|logs:|page:|noop)"))
async def on_admin_panel_callback(client: Client, query: CallbackQuery):
    """
    روتر جامع دکمه‌های شیشه‌ای پنل مدیریت در چت خصوصی اونر.
    تمام عملیات‌ها (از جمله بن/آزادسازی اعضای گروه) از همین پیوی اجرا می‌شوند
    و هیچ پیامی در گروه منتشر نمی‌گردد.
    """
    if not query.from_user or not is_admin_user(query.from_user.id):
        await query.answer("⛔ شما به این پنل مدیریتی دسترسی ندارید.", show_alert=True)
        return

    if not query.message:
        await query.answer()
        return

    data = query.data or ""
    parts = _split_callback(data)
    admin = query.from_user
    admin_id = admin.id

    async def answer(text: str = "", show_alert: bool = False) -> None:
        """پاسخ امن به کلیک دکمه (از خطای QueryAlreadyAnswered جلوگیری می‌کند)"""
        try:
            if text:
                await query.answer(text[:200], show_alert=show_alert)
            else:
                await query.answer()
        except Exception:
            pass

    async def show(builder_result: Tuple[str, InlineKeyboardMarkup]) -> None:
        """ویرایش پیام فعلی با محتوای یک منو"""
        text, keyboard = builder_result
        await safe_edit(query.message, text, keyboard)

    # ------------------------------------------------------------------
    # ۰. دکمه تزئینی شماره صفحه
    # ------------------------------------------------------------------
    if data.startswith("noop"):
        await answer("📄 برای جابه‌جایی بین صفحات از دکمه‌های قبلی/بعدی استفاده کنید.")
        return

    # ------------------------------------------------------------------
    # ۱. صفحه‌بندی لیست‌ها
    # ------------------------------------------------------------------
    if data.startswith("page:"):
        kind = parts[1] if len(parts) > 1 else ""
        if kind == "groups":
            purpose = parts[2] if len(parts) > 2 else "stats"
            await show(build_groups_menu(purpose=purpose, page=_to_int(parts[3] if len(parts) > 3 else 0)))
        elif kind == "unverified":
            await show(build_unverified_menu(_to_int(parts[2]), _to_int(parts[3])))
        elif kind == "banned":
            cid = _to_int(parts[2])
            page = _to_int(parts[3])
            members, note = await fetch_banned_members(client, cid, int(get_setting("moderation", "banned_fetch_limit", 100)))
            await show(build_banned_menu(cid, members, note, page))
        elif kind == "rep_links":
            await show(build_links_report(parts[2], _to_int(parts[3])))
        elif kind == "rep_adds":
            await show(build_adds_report(parts[2], _to_int(parts[3])))
        elif kind == "pickuser":
            target = await ensure_target(client, 0, _to_int(parts[2]))
            await show(build_group_picker_for_user(target, _to_int(parts[3])))
        else:
            await show(build_main_menu(admin))
        await answer()
        return

    # ------------------------------------------------------------------
    # ۲. منوی اصلی، راهنما و به‌روزرسانی
    # ------------------------------------------------------------------
    if data in ("menu:main", "menu:refresh"):
        pending_admin_input.pop(admin_id, None)
        await show(build_main_menu(admin))
        if data == "menu:refresh":
            await answer("🔄 پنل مدیریت با موفقیت به‌روزرسانی شد.")
        else:
            await answer()
        return

    if data == "menu:help":
        await show(build_help_menu())
        await answer()
        return

    if data == "menu:stats":
        await show(build_groups_menu(purpose="stats"))
        await answer()
        return

    if data.startswith("group:"):
        await show(build_group_dashboard(data.split(":", 1)[1]))
        await answer()
        return

    # ------------------------------------------------------------------
    # ۳. گزارش‌های تفکیکی + بن سریع از داخل گزارش
    # ------------------------------------------------------------------
    if data.startswith("rep_links:"):
        bits = data.split(":")
        await show(build_links_report(bits[1], _to_int(bits[2] if len(bits) > 2 else 0)))
        await answer()
        return

    if data.startswith("rep_adds:"):
        bits = data.split(":")
        await show(build_adds_report(bits[1], _to_int(bits[2] if len(bits) > 2 else 0)))
        await answer()
        return

    if data.startswith("rep_ban:"):
        cid = _to_int(parts[1])
        uid = _to_int(parts[2])
        target = await ensure_target(client, cid, uid)
        status_line = await describe_member_in_group(client, cid, target)
        await show(build_ban_confirm(cid, target, status_line, "تخلف ثبت‌شده در گزارش اد/لینک"))
        await answer("⚠️ پیش از اجرا، بن را تأیید کنید.")
        return

    # ------------------------------------------------------------------
    # ۴. ماژول‌ها و سوئیچ‌ها
    # ------------------------------------------------------------------
    if data == "menu:settings":
        await show(build_modules_settings_menu())
        await answer()
        return

    if data.startswith("toggle:"):
        key = parts[1] if len(parts) > 1 else ""
        origin = parts[2] if len(parts) > 2 else "mods"

        if key == "channel_logs":
            new_state = not bool(get_setting("notifications", "send_logs_to_channel", False))
            set_setting("notifications", "send_logs_to_channel", new_state)
            label = "ارسال لاگ به کانال لاگ"
            await send_owner_log(f"🔔 **تغییر سیاست لاگ:** «{label}» اکنون {_switch(new_state)} شد.")
            if new_state:
                channel = resolve_log_channel()
                if channel and isinstance(channel, int) and is_protected_group(channel):
                    await answer(
                        "⚠️ روشن شد، اما کانال لاگ شما یکی از گروه‌های محافظت‌شده است؛ "
                        "ربات هرگز لاگ را به داخل گروه نمی‌فرستد.",
                        show_alert=True
                    )
                    await show(build_notifications_menu())
                    return
        elif key == "notify_moderation":
            new_state = not bool(get_setting("notifications", "notify_on_moderation", True))
            set_setting("notifications", "notify_on_moderation", new_state)
            label = "گزارش بن/آزادسازی دستی"
            await send_owner_log(f"🔔 **تغییر سیاست لاگ:** «{label}» اکنون {_switch(new_state)} شد.")
        elif key == "status_log":
            new_state = not bool(get_setting("notifications", "status_log_to_owner_pv", True))
            set_setting("notifications", "status_log_to_owner_pv", new_state)
            label = "اعلان وضعیت (آنلاین/آفلاین) در پیوی اونر"
            if new_state:
                await send_status_log("🔔 اعلان وضعیت ربات مجدداً برای پیوی شما فعال شد. این پیام هرگز به گروه ارسال نمی‌شود.")
            else:
                await send_owner_log(f"🔕 **تغییر سیاست لاگ:** «{label}» خاموش شد.")
        else:
            mod_dict = config.setdefault("modules", {})
            new_state = not mod_dict.get(key, True)
            mod_dict[key] = new_state
            save_config_file(config)
            label = key
            await send_owner_log(f"⚙️ **تغییر ماژول:** ماژول `{key}` اکنون {_switch(new_state)} شد.")

        await answer(f"{label}: {_switch(new_state)}")
        await show(build_notifications_menu() if origin == "logs" else build_modules_settings_menu())
        return

    # ------------------------------------------------------------------
    # ۵. 🔔 سیاست لاگ و اعلان‌ها
    # ------------------------------------------------------------------
    if data == "menu:logs":
        await show(build_notifications_menu())
        await answer()
        return

    if data == "logs:test":
        delivered = await send_owner_log(
            "🧪 **تست لاگ:** این پیام فقط و فقط به پیوی شما ارسال شده است.\n"
            "هیچ پیامی در گروه‌ها یا کانال لاگ منتشر نشده است."
        )
        await show(build_notifications_menu())
        if delivered:
            await answer(f"✅ {delivered} لاگ تست در پیوی شما ارسال شد.")
        else:
            await answer("⚠️ ارسال ناموفق بود؛ ابتدا در پیوی ربات /start بفرستید.", show_alert=True)
        return

    if data == "logs:unset":
        previous = config.get("log_channel_id", 0)
        config["log_channel_id"] = 0
        save_config_file(config)
        await send_owner_log(f"🗑️ **کانال لاگ حذف شد** (مقدار قبلی: `{previous}`). از این پس همه لاگ‌ها فقط به پیوی شما می‌روند.")
        await show(build_notifications_menu())
        await answer("🗑️ کانال لاگ حذف شد.")
        return

    if data.startswith("logs:set:"):
        channel_id = _to_int(parts[2])
        if not channel_id:
            await answer("❌ شناسه کانال نامعتبر است.", show_alert=True)
            return
        config["log_channel_id"] = channel_id
        save_config_file(config)

        warning = ""
        if is_protected_group(channel_id):
            warning = (
                "\n\n⚠️ **هشدار:** این شناسه یکی از گروه‌های محافظت‌شده است؛ طبق سیاست ربات\n"
                "هیچ لاگی به داخل گروه ارسال نمی‌شود (فقط پیوی شما)."
            )
        enabled = bool(get_setting("notifications", "send_logs_to_channel", False))
        await send_owner_log(
            f"📢 **کانال لاگ ثبت شد:** `{channel_id}`\n"
            f"🔔 ارسال لاگ به کانال: {_switch(enabled)}{warning}"
        )
        text = (
            f"✅ **کانال لاگ با موفقیت ثبت شد**\n"
            f"📮 شناسه: `{channel_id}`\n"
            f"🔔 ارسال لاگ به کانال: {_switch(enabled)}\n"
            f"{SEP}\n"
            f"🔒 اعلان آنلاین/آفلاین شدن ربات همیشه فقط به پیوی شما ارسال می‌شود."
            f"{warning}"
        )
        toggle_label = "📢 روشن کردن ارسال لاگ به کانال" if not enabled else "🔕 خاموش کردن ارسال لاگ به کانال"
        await safe_edit(query.message, text, InlineKeyboardMarkup([
            [InlineKeyboardButton(toggle_label, callback_data="toggle:channel_logs:logs")],
            [InlineKeyboardButton("🔔 سیاست لاگ‌ها", callback_data="menu:logs")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
        ]))
        await answer("✅ کانال لاگ ثبت شد.")
        return

    # ------------------------------------------------------------------
    # ۶. پارامترها و سقف‌ها
    # ------------------------------------------------------------------
    if data == "menu:params":
        await show(build_params_menu())
        await answer()
        return

    if data == "param:captcha":
        await show(build_captcha_param_menu())
        await answer()
        return

    if data.startswith("set_cap:"):
        curr = int(config.get("captcha", {}).get("timeout_seconds", 60))
        if len(parts) > 2 and parts[1] == "step":
            new_val = max(10, min(600, curr + _to_int(parts[2])))
        else:
            new_val = _to_int(parts[2], curr)
        set_setting("captcha", "timeout_seconds", new_val)
        await send_owner_log(f"⏱️ **تغییر تنظیمات:** مهلت کپچا به `{new_val}` ثانیه تغییر یافت.")
        await answer(f"⏱️ مهلت کپچا: {new_val} ثانیه")
        await show(build_captcha_param_menu())
        return

    if data == "param:addlimit":
        await show(build_addlimit_param_menu())
        await answer()
        return

    if data.startswith("set_limit:"):
        curr = int(config.get("anti_add", {}).get("max_adds_per_day", 3))
        if len(parts) > 2 and parts[1] == "step":
            new_val = max(0, min(100, curr + _to_int(parts[2])))
        else:
            new_val = max(0, _to_int(parts[2], curr))
        set_setting("anti_add", "max_adds_per_day", new_val)
        desc = "⛔ قفل کامل (۰)" if new_val == 0 else f"{new_val} اد در ۲۴ ساعت"
        await send_owner_log(f"👥 **تغییر تنظیمات:** سقف مجاز اد به `{desc}` تغییر یافت.")
        await answer(f"سقف مجاز اد: {desc}")
        await show(build_addlimit_param_menu())
        return

    if data == "param:action":
        await show(build_action_param_menu())
        await answer()
        return

    if data.startswith("set_act:"):
        act_val = parts[1] if len(parts) > 1 else "warn"
        set_setting("anti_add", "violation_action", act_val)
        fa_names = {"warn": "اخطار", "kick": "اخراج", "ban": "مسدودسازی"}
        act_fa = fa_names.get(act_val, act_val)
        await send_owner_log(f"⚡ **تغییر تنظیمات:** اقدام تخلف اد به `{act_fa}` تغییر یافت.")
        await answer(f"اقدام تخلف: {act_fa}")
        await show(build_action_param_menu())
        return

    if data == "param:sweep":
        await show(build_sweep_param_menu())
        await answer()
        return

    if data.startswith("set_swp:"):
        curr = int(config.get("sweep", {}).get("retention_hours", 24))
        if len(parts) > 2 and parts[1] == "step":
            new_val = max(1, min(168, curr + _to_int(parts[2])))
        else:
            new_val = max(1, _to_int(parts[2], curr))
        set_setting("sweep", "retention_hours", new_val)
        await send_owner_log(f"⏳ **تغییر تنظیمات:** بازه Sweep به `{new_val}` ساعت تغییر یافت.")
        await answer(f"بازه زمانی Sweep: {new_val} ساعت")
        await show(build_sweep_param_menu())
        return

    if data == "param:pagesize":
        await show(build_pagesize_param_menu())
        await answer()
        return

    if data.startswith("set_page:"):
        curr = int(get_setting("moderation", "banned_page_size", 5))
        if len(parts) > 2 and parts[1] == "step":
            new_val = max(1, min(20, curr + _to_int(parts[2])))
        else:
            new_val = max(1, min(20, _to_int(parts[2], curr)))
        set_setting("moderation", "banned_page_size", new_val)
        set_setting("moderation", "unverified_page_size", new_val)
        await answer(f"📄 هر صفحه: {new_val} مورد")
        await show(build_pagesize_param_menu())
        return

    # ------------------------------------------------------------------
    # ۷. 🚫 مرکز مدیریت اعضا (بن/آزادسازی از پیوی)
    # ------------------------------------------------------------------
    if data in ("mod:home", "menu:moderation"):
        pending_admin_input.pop(admin_id, None)
        if not moderation_enabled():
            await answer("🛡️ ماژول مدیریت اعضا غیرفعال است؛ از منوی ماژول‌ها فعالش کنید.", show_alert=True)
            await show(build_modules_settings_menu())
            return
        await show(build_groups_menu(purpose="moderation"))
        await answer()
        return

    if data.startswith("mod:group:") and not data.startswith("mod:group_for:"):
        cid = _to_int(parts[2])
        pending_admin_input.pop(admin_id, None)
        await show(build_group_moderation(cid))
        await answer()
        return

    if data.startswith("mod:unverified:"):
        cid = _to_int(parts[2])
        if not moderation_enabled():
            await answer("🛡️ ماژول مدیریت اعضا غیرفعال است.", show_alert=True)
            return
        await show(build_unverified_menu(cid, _to_int(parts[3])))
        await answer()
        return

    if data.startswith("mod:banned:"):
        cid = _to_int(parts[2])
        page = _to_int(parts[3])
        await answer("🔄 در حال دریافت لیست بن‌شده‌ها از تلگرام…")
        members, note = await fetch_banned_members(client, cid, int(get_setting("moderation", "banned_fetch_limit", 100)))
        await show(build_banned_menu(cid, members, note, page))
        return

    if data.startswith("mod:manual:"):
        cid = _to_int(parts[2])
        if not moderation_enabled():
            await answer("🛡️ ماژول مدیریت اعضا غیرفعال است.", show_alert=True)
            return
        pending_admin_input[admin_id] = {"action": "ban", "chat_id": cid, "started_at": time.time()}
        await show(build_manual_ban_prompt(cid, mode="ban"))
        await answer("⌨️ آیدی عددی یا @username را در پیوی بفرستید.")
        return

    if data.startswith("mod:lookup:"):
        cid = _to_int(parts[2])
        pending_admin_input[admin_id] = {"action": "lookup", "chat_id": cid, "started_at": time.time()}
        await show(build_manual_ban_prompt(cid, mode="lookup"))
        await answer("⌨️ آیدی عددی یا @username را در پیوی بفرستید.")
        return

    if data.startswith("mod:group_for:"):
        cid = _to_int(parts[2])
        uid = _to_int(parts[3])
        target = await ensure_target(client, cid, uid)
        status_line = await describe_member_in_group(client, cid, target)
        await show(build_target_actions(cid, target, status_line))
        await answer()
        return

    if data.startswith("mod:info:"):
        cid = _to_int(parts[2])
        uid = _to_int(parts[3])
        target = await ensure_target(client, cid, uid)
        status_line = await describe_member_in_group(client, cid, target)
        record = ban_records.get(member_key(cid, uid))
        extra = ""
        if record:
            when = datetime.fromtimestamp(record.get("time", time.time())).strftime("%Y-%m-%d %H:%M")
            extra = (
                f"\n📝 **سابقه بن توسط ربات:** {when}\n"
                f"   ▫️ مجری: {record.get('by_name', '—')}\n"
                f"   ▫️ دلیل: {record.get('reason') or '—'}"
            )
        await show(build_target_actions(cid, target, status_line + extra))
        await answer()
        return

    if data.startswith("mod:ban_confirm:"):
        cid = _to_int(parts[2])
        uid = _to_int(parts[3])
        target = await ensure_target(client, cid, uid)
        status_line = await describe_member_in_group(client, cid, target)
        reason = pending_ban_reasons.get(reason_key(admin_id, cid, uid), "")
        await show(build_ban_confirm(cid, target, status_line, reason))
        await answer()
        return

    if data.startswith("mod:unban_confirm:"):
        cid = _to_int(parts[2])
        uid = _to_int(parts[3])
        target = await ensure_target(client, cid, uid)
        status_line = await describe_member_in_group(client, cid, target)
        await show(build_unban_confirm(cid, target, status_line))
        await answer()
        return

    if data.startswith("mod:do_ban:"):
        cid = _to_int(parts[2])
        uid = _to_int(parts[3])
        target = await ensure_target(client, cid, uid)
        reason = pop_ban_reason(admin_id, cid, uid)
        success, message_text = await apply_ban(client, cid, target, admin=admin, reason=reason)
        await show(build_moderation_result(cid, target, success, message_text))
        await answer("✅ کاربر بن شد." if success else message_text, show_alert=not success)
        return

    if data.startswith("mod:do_unban:"):
        cid = _to_int(parts[2])
        uid = _to_int(parts[3])
        target = await ensure_target(client, cid, uid)
        success, message_text = await apply_unban(client, cid, target, admin=admin, reason="آزادسازی دستی از پیوی")
        await show(build_moderation_result(cid, target, success, message_text))
        await answer("✅ کاربر آزاد شد." if success else message_text, show_alert=not success)
        return

    # ------------------------------------------------------------------
    # ۸. عملیات اضطراری (Panic & Sweep)
    # ------------------------------------------------------------------
    if data == "menu:emergency":
        await show(build_emergency_menu())
        await answer()
        return

    if data == "emerg:lock_adds":
        set_setting("anti_add", "max_adds_per_day", 0)
        await send_owner_log("⛔ **قفل اضطراری:** افزودن مخاطب در تمام گروه‌ها کاملاً مسدود شد (سقف ۰).")
        await answer("⛔ قابلیت اد کردن مخاطب کاملاً مسدود شد (سقف 0)!", show_alert=True)
        await show(build_emergency_menu())
        return

    if data == "menu:panic":
        if not config.get("modules", {}).get("panic", True):
            await answer("🚨 ماژول Panic غیرفعال است.", show_alert=True)
            return
        await show(build_groups_menu(purpose="panic"))
        await answer()
        return

    if data.startswith("emerg_panic_confirm:"):
        target_cid = _to_int(data.split(":", 1)[1])
        text = (
            f"🚨 **تأییدیه فعال‌سازی وضعیت اضطراری (Panic Mode)**\n"
            f"📍 گروه: **{_trim(group_title(target_cid), 40)}** (`{target_cid}`)\n"
            f"{SEP}\n"
            f"⚠️ با تأیید این عملیات:\n"
            f"۱. لینک دعوت فعلی گروه فوراً باطل (Revoke) می‌شود.\n"
            f"۲. یک لینک دعوت جدید صادر شده و در همینجا به شما تحویل داده می‌شود.\n"
            f"۳. نفوذ بات‌ها و مهاجمان از لینک قبلی متوقف خواهد شد.\n"
            f"۴. گزارش عملیات فقط به پیوی شما ارسال می‌شود (نه در گروه).\n\n"
            f"آیا مطمئن هستید؟"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚨 بله، ابطال و صدور لینک جدید", callback_data=f"exec_panic:{target_cid}")],
            [InlineKeyboardButton("❌ انصراف", callback_data=f"group:{target_cid}"), InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
        ])
        await safe_edit(query.message, text, kb)
        await answer()
        return

    if data.startswith("exec_panic:"):
        target_cid = _to_int(data.split(":", 1)[1])
        g_title = _trim(group_title(target_cid), 40)
        await answer("🚨 در حال ابطال لینک و صدور لینک جدید…")
        try:
            current_link = None
            try:
                chat = await client.get_chat(target_cid)
                current_link = chat.invite_link
            except Exception:
                pass

            if current_link:
                try:
                    await client.revoke_chat_invite_link(target_cid, current_link)
                except Exception as revoke_error:
                    logger.warning(f"ابطال لینک دعوت ناموفق بود: {revoke_error}")

            new_invite = await client.create_chat_invite_link(
                target_cid,
                name=f"Panic Link {datetime.now().strftime('%m-%d %H:%M')}"
            )
            new_link = new_invite.invite_link

            await send_owner_log(
                f"🚨 **فعال‌سازی حالت اضطراری (Panic)**\n"
                f"👤 توسط اونر: **{admin.first_name}** (`{admin.id}`)\n"
                f"💬 گروه: {group_title(target_cid)} (`{target_cid}`)\n"
                f"🔗 لینک دعوت جدید: `{new_link}`",
                header="🚨 عملیات اضطراری"
            )

            result_text = (
                f"🚨 **وضعیت اضطراری فعال شد!**\n"
                f"📍 گروه: **{g_title}** (`{target_cid}`)\n"
                f"{SEP}\n"
                f"✅ لینک دعوت قبلی گروه باطل (Revoke) گردید.\n\n"
                f"🔗 **لینک دعوت جدید گروه:**\n"
                f"`{new_link}`\n\n"
                f"⚠️ مسیر نفوذ مهاجمانی که از لینک قبلی می‌آمدند بسته شد.\n"
                f"🔒 این گزارش فقط در پیوی شما ثبت شد."
            )
            res_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 داشبورد گروه", callback_data=f"group:{target_cid}")],
                [InlineKeyboardButton("🚫 مدیریت اعضا", callback_data=f"mod:group:{target_cid}"), InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
            ])
            await safe_edit(query.message, result_text, res_kb)
        except FloodWait as e:
            logger.error(f"FloodWait in exec_panic: {e}")
            await answer(f"⏳ تلگرام موقتاً محدود کرده است؛ {e.value} ثانیه دیگر تلاش کنید.", show_alert=True)
        except Exception as e:
            logger.error(f"Error in exec_panic: {e}")
            await answer(f"❌ خطا در صدور لینک: {e}", show_alert=True)
        return

    if data == "menu:sweep":
        if not config.get("modules", {}).get("sweep", True):
            await answer("🧹 ماژول Sweep غیرفعال است.", show_alert=True)
            return
        await show(build_groups_menu(purpose="sweep"))
        await answer()
        return

    if data.startswith("emerg_sweep_confirm:"):
        target_cid = _to_int(data.split(":", 1)[1])
        retention_hours = int(config.get("sweep", {}).get("retention_hours", 24))
        cutoff_time = time.time() - (retention_hours * 3600)

        unverified_targets = [
            (int(d.get("user_id", 0)), d)
            for d in unverified_joins.values()
            if d.get("chat_id") == target_cid and d.get("join_time", 0) >= cutoff_time
        ]
        target_count = len(unverified_targets)

        text = (
            f"🧹 **تأییدیه عملیات پاکسازی اعضای تأیید نشده (Sweep)**\n"
            f"📍 گروه: **{_trim(group_title(target_cid), 40)}** (`{target_cid}`)\n"
            f"⏳ بازه زمانی: **{retention_hours} ساعت گذشته**\n"
            f"🎯 تعداد اعضای تأیید نشده در نوبت بن: **{target_count} نفر**\n"
            f"{SEP}\n"
            f"آیا مایلید تمام حساب‌هایی که در این بازه کپچا را حل نکرده‌اند مسدود (Ban) شوند؟"
        )
        buttons = []
        if target_count > 0:
            buttons.append([InlineKeyboardButton(f"🧹 بن کردن {target_count} اکانت", callback_data=f"exec_sweep:{target_cid}")])
        else:
            buttons.append([InlineKeyboardButton("ℹ️ موردی برای پاکسازی نیست", callback_data="noop:empty")])
        buttons.append([InlineKeyboardButton("❌ انصراف", callback_data=f"group:{target_cid}"), InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")])

        await safe_edit(query.message, text, InlineKeyboardMarkup(buttons))
        await answer()
        return

    if data.startswith("exec_sweep:"):
        target_cid = _to_int(data.split(":", 1)[1])
        g_title = _trim(group_title(target_cid), 40)
        retention_hours = int(config.get("sweep", {}).get("retention_hours", 24))
        cutoff_time = time.time() - (retention_hours * 3600)

        unverified_targets = [
            (int(d.get("user_id", 0)), d)
            for d in list(unverified_joins.values())
            if d.get("chat_id") == target_cid and d.get("join_time", 0) >= cutoff_time
        ]

        if not unverified_targets:
            await answer("ℹ️ در حال حاضر حسابی برای پاکسازی وجود ندارد.", show_alert=True)
            return

        await answer("🧹 در حال پاکسازی و بن حساب‌ها…")

        banned_count = 0
        fail_count = 0
        for uid, record in unverified_targets:
            target = TargetUser(
                uid,
                record.get("first_name", ""),
                record.get("username", "")
            )
            cancel_pending_captcha(target_cid, uid)
            success, _msg = await apply_ban(client, target_cid, target, admin=admin, reason="Sweep: عدم حل کپچا", auto=True)
            if success:
                banned_count += 1
            else:
                fail_count += 1
            await asyncio.sleep(0.4)  # کاهش احتمال FloodWait در بن‌های پشت‌سرهم

        save_state()

        await send_owner_log(
            f"🧹 **عملیات پاکسازی گروه (Sweep) پایان یافت**\n"
            f"👤 مجری: **{admin.first_name}** (`{admin.id}`)\n"
            f"💬 گروه: {group_title(target_cid)} (`{target_cid}`)\n"
            f"🚫 بن شده‌ها: {banned_count} نفر\n"
            f"⚠️ ناموفق: {fail_count} نفر\n"
            f"⏳ بازه زمانی: {retention_hours} ساعت گذشته",
            header="🧹 عملیات Sweep"
        )

        res_text = (
            f"🧹 **عملیات پاکسازی (Sweep) انجام شد**\n"
            f"📍 گروه: **{g_title}** (`{target_cid}`)\n"
            f"{SEP}\n"
            f"🚫 حساب‌های مسدود شده: **{banned_count} نفر**\n"
            f"⚠️ موارد ناموفق: **{fail_count} نفر**\n"
            f"⏱️ بازه زمانی: **{retention_hours} ساعت گذشته**\n"
            f"{SEP}\n"
            f"🔒 گزارش کامل فقط به پیوی شما ارسال شد و پیامی در گروه منتشر نشد."
        )
        res_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 لیست بن‌شده‌ها", callback_data=f"mod:banned:{target_cid}:0")],
            [InlineKeyboardButton("🔙 داشبورد گروه", callback_data=f"group:{target_cid}")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
        ])
        await safe_edit(query.message, res_text, res_kb)
        return

    # ------------------------------------------------------------------
    # ۹. اطلاعات سیستم و تست پینگ واقعی
    # ------------------------------------------------------------------
    if data == "menu:info":
        await show(build_system_info_menu())
        await answer()
        return

    if data == "menu:compat":
        await show(build_compat_menu())
        await answer()
        return

    if data == "ping:check":
        start_t = time.time()
        try:
            await client.get_me()
            latency_ms = round((time.time() - start_t) * 1000, 1)
            await answer(f"⚡ پاسخ API تلگرام: {latency_ms}ms | سیستم کاملاً فعال است!", show_alert=True)
        except Exception as e:
            await answer(f"❌ خطا در ارتباط با API تلگرام: {e}", show_alert=True)
        return

    await answer()

# ---------------------------------------------------------------------------
# ۱۳. تسک دوره‌ای پاکسازی داده‌های قدیمی از رم (Hourly Garbage Collector)
# ---------------------------------------------------------------------------
async def periodic_cleanup_task():
    """حذف خودکار رکوردهای منقضی‌شده از حافظه رم هر یک ساعت یک‌بار"""
    while True:
        try:
            await asyncio.sleep(3600)  # هر ۱ ساعت
            now = time.time()
            retention_hours = int(config.get("sweep", {}).get("retention_hours", 24))
            sweep_cutoff = now - (max(retention_hours, 48) * 3600)

            # پاکسازی unverified_joins های قدیمی
            for key in list(unverified_joins.keys()):
                if unverified_joins[key].get("join_time", 0) < sweep_cutoff:
                    del unverified_joins[key]

            # پاکسازی تسک‌های کپچای پایان‌یافته و بی‌سرپرست
            for key in list(pending_verifications.keys()):
                info = pending_verifications.get(key) or {}
                task = info.get("task")
                if task is not None and task.done() and key not in unverified_joins:
                    pending_verifications.pop(key, None)

            # پاکسازی تاریخچه اد کاربران قدیمی‌تر از ۴۸ ساعت
            add_cutoff = now - (48 * 3600)
            for inviter_id in list(user_add_history.keys()):
                entry = user_add_history[inviter_id]
                if isinstance(entry, dict):
                    entry["adds"] = [x for x in entry.get("adds", []) if x.get("time", 0) >= add_cutoff]
                    if not entry["adds"]:
                        del user_add_history[inviter_id]
                elif isinstance(entry, list):
                    user_add_history[inviter_id] = [x for x in entry if x.get("time", 0) >= add_cutoff]
                    if not user_add_history[inviter_id]:
                        del user_add_history[inviter_id]

            # پاکسازی حالت‌های ورودی نیمه‌تمام پیوی (بیش از ۳۰ دقیقه بی‌پاسخ)
            for admin_id in list(pending_admin_input.keys()):
                if now - float(pending_admin_input[admin_id].get("started_at", now)) > 1800:
                    pending_admin_input.pop(admin_id, None)

            # دلیل‌های بن استفاده‌نشده هم پاک می‌شوند (داده موقت و حساس)
            pending_ban_reasons.clear()

            save_state()
            logger.info("تسک دوره‌ای پاکسازی حافظه با موفقیت انجام شد.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"خطا در تسک پاکسازی دوره‌ای: {e}")

# ---------------------------------------------------------------------------
# ۱۴. نقطه شروع و اجرای ربات (Main Entry Point)
# ---------------------------------------------------------------------------
async def warn_log_channel_policy() -> None:
    """
    بررسی پیکربندی لاگ در لحظه شروع به کار و هشدار به اونر در صورت وجود تنظیم خطرناک.
    هدف: اطمینان از اینکه هیچ لاگی (به‌ویژه آنلاین/آفلاین) به داخل گروه نمی‌رود.
    """
    admin_ids = [int(a) for a in config.get("admin_ids", []) if a]
    if not admin_ids:
        logger.warning("⚠️ admin_ids خالی است؛ اعلان آنلاین/آفلاین به هیچ‌کس ارسال نخواهد شد.")
        return

    channel = resolve_log_channel()
    if not channel:
        logger.info("کانال لاگ تنظیم نشده است؛ تمامی لاگ‌ها فقط به پیوی اونر ارسال می‌شوند.")
        return

    if isinstance(channel, int) and is_protected_group(channel):
        await send_status_log(
            f"⚠️ **هشدار پیکربندی لاگ**\n"
            f"📮 مقدار `log_channel_id` (`{channel}`) برابر با یکی از گروه‌های محافظت‌شده است:\n"
            f"   «{group_title(channel)}»\n\n"
            f"🔒 طبق سیاست ربات، هیچ لاگ امنیتی (به‌ویژه آنلاین/آفلاین شدن) به داخل گروه ارسال نمی‌شود.\n"
            f"📌 اگر می‌خواهید لاگ‌ها را در یک کانال مجزا داشته باشید، پیامی از آن کانال را به پیوی\n"
            f"ربات فوروارد کنید یا از منوی «🔔 لاگ و اعلان‌ها» اقدام نمایید."
        )
        return

    if not get_setting("notifications", "send_logs_to_channel", False):
        logger.info("ارسال لاگ به کانال لاگ خاموش است؛ لاگ‌ها فقط به پیوی اونر می‌روند.")


async def main():
    """اجرای ناهمگام ربات و بارگذاری سرویس‌ها"""
    global BOT_ME, BOT_START_TIME

    if not API_ID or not API_HASH or not BOT_TOKEN or API_ID == 0 or "YOUR_" in str(BOT_TOKEN) or "YOUR_" in str(API_HASH):
        print("\n" + "=" * 70)
        print("❌ خطا: مقادیر احراز هویت تلگرام در config.json هنوز تنظیم نشده‌اند!")
        print("لطفاً فایل config.json را باز کرده و api_id, api_hash و bot_token را قرار دهید.")
        print("=" * 70 + "\n")
        return

    load_state()

    logger.info("در حال اتصال به سرورهای تلگرام...")
    await app.start()

    BOT_ME = await app.get_me()
    BOT_START_TIME = time.time()
    logger.info(f"ربات محافظ با نام @{BOT_ME.username} (ID: {BOT_ME.id}) فعال شد!")
    print("\n" + "=" * 60)
    print(f"✅ ربات با موفقیت روشن شد: @{BOT_ME.username} | نسخه {BOT_VERSION}")
    print(f"🐍 پایتون {platform.python_version()} | {TELEGRAM_LIB} {TELEGRAM_LIB_VERSION}"
          f" | رمزنگاری سریع: {'فعال' if CRYPTO_ACCELERATED else 'غیرفعال'}")
    print("آماده دریافت رویدادها و محافظت از سوپرگروه...")
    print("🔒 لاگ آنلاین/آفلاین فقط به پیوی اونر ارسال می‌شود (نه گروه).")
    for warn in compatibility_warnings():
        print(warn)
    print("=" * 60 + "\n")

    # 🔔 اعلان روشن شدن ربات: فقط پیوی اونر — هرگز گروه یا کانال لاگ
    await send_status_log(
        f"🟢 **ربات محافظ گروه آنلاین شد**\n"
        f"🤖 ربات: @{BOT_ME.username} (`{BOT_ME.id}`)\n"
        f"🧩 نسخه: `{BOT_VERSION}`\n"
        f"🐍 پایتون: `{platform.python_version()}` | کتابخانه: `{TELEGRAM_LIB} {TELEGRAM_LIB_VERSION}`\n"
        f"👥 گروه‌های ثبت‌شده: `{len(known_groups)}`\n"
        f"⏳ در انتظار کپچا: `{len(unverified_joins)}` نفر\n"
        f"🚫 سوابق بن: `{len(ban_records)}` مورد\n"
        f"🚀 وضعیت: آماده به کار\n"
        f"🔒 این اعلان فقط در پیوی شما ارسال شده و هیچ پیامی به گروه نرفته است."
    )

    # 🧩 هشدارهای سازگاری محیط اجرا (پایتون ۳.۱۲+/tgcrypto) فقط به پیوی اونر
    compat_warns = compatibility_warnings()
    if compat_warns:
        await send_status_log(
            f"🧩 **گزارش سازگاری محیط اجرا**\n"
            f"🐍 پایتون: `{platform.python_version()}` | کتابخانه: `{TELEGRAM_LIB} {TELEGRAM_LIB_VERSION}`\n"
            f"🔐 شتاب رمزنگاری: {_switch(CRYPTO_ACCELERATED)}\n"
            f"{SEP}\n"
            + "\n".join(compat_warns)
            + f"\n{SEP}\n💡 در پیوی ربات دستور `/compat` را بفرستید تا گزارش کامل و دستور نصب نمایش داده شود."
        )

    # بررسی سیاست لاگ و هشدار در صورت تنظیم خطرناک کانال لاگ
    await warn_log_channel_policy()

    # شروع تسک پس‌زمینه پاکسازی
    cleanup_task = asyncio.create_task(periodic_cleanup_task())

    try:
        # انتظار برای دریافت سیگنال خروج (Ctrl+C یا پایان پروسه)
        await pyrogram.idle()
    except Exception as e:
        logger.critical(f"خطای غیرمنتظره در حلقه اصلی ربات: {e}")
        await send_status_log(
            f"⚠️ **ربات به دلیل خطای غیرمنتظره متوقف شد**\n"
            f"❌ خطا: `{e}`\n"
            f"⏱️ مدت کارکرد پیش از توقف: {format_uptime(time.time() - BOT_START_TIME)}\n"
            f"📌 لطفاً لاگ کنسول را بررسی کرده و ربات را مجدداً اجرا کنید."
        )
    finally:
        # توقف منظم
        logger.info("در حال خاموش‌سازی ربات و بستن اتصالات...")
        cleanup_task.cancel()

        uptime_text = format_uptime(time.time() - BOT_START_TIME)

        # 🔔 اعلان خاموش شدن ربات: فقط پیوی اونر
        await send_status_log(
            f"🔴 **ربات محافظ گروه آفلاین شد**\n"
            f"🤖 ربات: @{BOT_ME.username if BOT_ME else '—'}\n"
            f"⏱️ مدت کارکرد: {uptime_text}\n"
            f"💾 وضعیت و سوابق بن روی دیسک ذخیره شد.\n"
            f"🔒 این اعلان هم فقط در پیوی شما ارسال شد."
        )

        save_state()
        try:
            await app.stop()
        except Exception as e:
            logger.warning(f"خطا در بستن کلاینت تلگرام: {e}")

    logger.info("ربات متوقف شد.")


if __name__ == "__main__":
    try:
        app.run(main())
    except KeyboardInterrupt:
        print("\nخروج توسط کاربر انجام شد.")
    except Exception as e:
        err_msg = str(e).lower()
        if "database is locked" in err_msg:
            print("\n" + "=" * 70)
            print("❌ خطای قفل بودن دیتابیس سشن (database is locked)!")
            print("علت: یک نسخه دیگر از ربات در حال حاضر در پس‌زمینه در حال اجراست و فایل سشن را قفل کرده است.")
            print("\n📌 روش بستن نسخه قبلی و رفع خطا:")
            print("  • در ترموکس (Termux): دستور زیر را بزنید تا پروسه‌های قبلی پایتون بسته شوند:")
            print("    pkill -f python")
            print("    سپس مجدداً 'python bot.py' را اجرا کنید.")
            print("\n  • در ویندوز (Windows): در CMD یا PowerShell دستور زیر را بزنید:")
            print("    taskkill /F /IM python.exe")
            print("    یا از Task Manager پروسه‌های پایتون را ببندید.")
            print("=" * 70 + "\n")
        else:
            logger.critical(f"خطای بحرانی در اجرای ربات: {e}")
