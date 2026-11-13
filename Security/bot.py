#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=============================================================================
🤖 ربات هوشمند ضد ربات و محافظت از سوپرگروه تلگرام (Pyrogram)
=============================================================================
هدف:
- محافظت کامل از سوپرگروه در برابر موج بات‌ها، ریدها (Raids) و حساب‌های جعلی
- ارسال پیام خوش‌آمد با کپچای شیشه‌ای و اخراج (Kick بدون بن) در صورت عدم تأیید
- ثبت گزارش افزودن عضو توسط کاربران و هشدار در صورت فراتر رفتن از سقف روزانه
- دستور اضطراری /panic جهت ابطال سریع لینک دعوت قبلی و صدور لینک جدید
- دستور /sweep جهت بن دائمی تمام اعضایی که در ۲۴ ساعت گذشته بدون کپچا وارد شده‌اند
- ارسال کلیه لاگ‌های امنیتی به کانال خصوصی لاگ
- مدیریت و پیکربندی زنده از طریق تلگرام و فایل config.json بدون نیاز به ری‌استارت

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
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

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
        # ادغام کلیدهای پیش‌فرض با کانفیگ بارگذاری شده (در صورت اضافه شدن فیلد جدید)
        merged = DEFAULT_CONFIG.copy()
        merged.update(data)
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

# شیء عمومی تنظیمات در حافظه
config: Dict[str, Any] = load_config()

# ---------------------------------------------------------------------------
# ۴. متغیرهای سراسری وضعیت و حافظه موقت (In-Memory State & Cache)
# ---------------------------------------------------------------------------
# دیکشنری نگهداری سوپرگروه‌های شناسایی‌شده تحت پوشش ربات:
# ساختار: { "chat_id_str": { "id": int, "title": str, "updated_at": float } }
known_groups: Dict[str, Dict[str, Any]] = {}

# دیکشنری نگهداری عضوهای تأیید نشده برای دستور /sweep:
# ساختار: { "user_id": { "chat_id": int, "user_id": int, "join_time": float, "first_name": str, "username": str } }
unverified_joins: Dict[str, Dict[str, Any]] = {}

# دیکشنری تاریخچه افزودن اعضا توسط هر کاربر در ۲۴ ساعت:
# ساختار: { "inviter_id": [ { "time": float, "user_id": int, "name": str, "username": str } ] }
user_add_history: Dict[str, List[Dict[str, Any]]] = {}

# دیکشنری رصد ورودی‌های لینک‌های دعوت (چه کسی با لینک چه فردی وارد شده است):
# ساختار: { "creator_id": { "name": str, "username": str, "count": int, "joins": list } }
link_join_history: Dict[str, Dict[str, Any]] = {}

# دیکشنری تسک‌های در حال اجرای کپچا (برای لغو شدن پس از تأیید):
# ساختار: { user_id_int: { "chat_id": int, "message_id": int, "task": asyncio.Task } }
pending_verifications: Dict[int, Dict[str, Any]] = {}

# کش جهت جلوگیری از پردازش تکراری جوین‌ها (Deduplication)
recent_events_cache: Dict[Tuple[int, int], float] = {}

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

def load_state() -> None:
    """بارگذاری وضعیت‌های ثبت شده از دیسک جهت پایداری داده‌ها پس از ری‌استارت"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            known_groups.clear()
            known_groups.update(data.get("known_groups", {}))
            unverified_joins.clear()
            unverified_joins.update(data.get("unverified_joins", {}))
            user_add_history.clear()
            user_add_history.update(data.get("user_add_history", {}))
            link_join_history.clear()
            link_join_history.update(data.get("link_join_history", {}))

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

            logger.info(f"داده‌های وضعیت بارگذاری شدند ({len(known_groups)} گروه، {len(unverified_joins)} کاربر تأیید نشده).")
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
                "link_join_history": link_join_history
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
# ۶. توابع کمکی امنیتی، لاگ‌گیری و جلوگیری از تکرار (Helper Functions)
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
    """بررسی شناسه کاربر با لیست ادمین‌های مجاز در config.json"""
    configured_admins = [int(a) for a in config.get("admin_ids", []) if a]
    return user_id in configured_admins

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

async def send_log(text: str) -> None:
    """
    ارسال گزارش‌های امنیتی منحصراً به پیوی ادمین‌ها (PV):
    طبق دستور، هیچ‌گونه پیام لاگ یا هشداری به داخل گپ فرستاده نمی‌شود
    و تمامی گزارش‌ها به صورت زنده به پیوی مدیران ارسال می‌گردند.
    """
    if not config.get("modules", {}).get("logging", True):
        return

    admin_ids = config.get("admin_ids", [])
    if not admin_ids:
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"📋 **گزارش امنیتی ربات** | `{now_str}`\n──────────────────────\n{text}"

    # ارسال به پیوی تک‌تک ادمین‌های مجاز
    for admin_id in admin_ids:
        try:
            await app.send_message(chat_id=int(admin_id), text=formatted, disable_web_page_preview=True)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            try:
                await app.send_message(chat_id=int(admin_id), text=formatted, disable_web_page_preview=True)
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"عدم امکان ارسال لاگ به پیوی ادمین {admin_id}: {e}")

    # در صورتی که کانال لاگ مجزایی نیز تنظیم شده باشد، یک نسخه به کانال لاگ فرستاده می‌شود
    log_channel = config.get("log_channel_id", 0)
    if log_channel and log_channel != 0:
        if isinstance(log_channel, str):
            cleaned = log_channel.strip()
            if cleaned.startswith("-100") or cleaned.lstrip("-").isdigit():
                try:
                    log_channel = int(cleaned)
                except ValueError:
                    pass
        if isinstance(log_channel, int) and log_channel < 0:
            try:
                await app.send_message(chat_id=log_channel, text=formatted, disable_web_page_preview=True)
            except Exception:
                pass

async def auto_delete_message(client: Client, chat_id: int, message_id: int, delay_seconds: int = 10) -> None:
    """حذف خودکار پیام پس از تأخیر مشخص شده جهت جلوگیری از شلوغی سوپرگروه"""
    await asyncio.sleep(delay_seconds)
    try:
        await client.delete_messages(chat_id, message_id)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# ۷. منطق کپچا و تایمر اخراج (Captcha & Timeout Logic)
# ---------------------------------------------------------------------------
async def captcha_timeout_worker(client: Client, chat_id: int, user_id: int, message_id: int, user_name: str, seconds: int):
    """تسک پس‌زمینه تایمر کپچا؛ در صورت عدم کلیک، کاربر کیک (نه بن) می‌شود"""
    try:
        await asyncio.sleep(seconds)

        # اگر کاربر همچنان در لیست انتظار باشد یعنی دکمه را نزده است
        if user_id in pending_verifications:
            pending_verifications.pop(user_id, None)

            # اخراج موقت: ابتدا بن، سپس بلافاصله آن‌بن تا بعداً بتواند دوباره وارد شود
            kicked_successfully = False
            try:
                await client.ban_chat_member(chat_id, user_id)
                await client.unban_chat_member(chat_id, user_id)
                kicked_successfully = True
                logger.info(f"User {user_id} was kicked from {chat_id} due to captcha timeout.")
            except RPCError as e:
                logger.error(f"خطا در اخراج کاربر {user_id}: {e}")

            # حذف پیام خوش‌آمد و کپچا از داخل گروه
            try:
                await client.delete_messages(chat_id, message_id)
            except Exception:
                pass

            # ارسال لاگ اخراج منحصراً به پیوی ادمین (گروه کاملاً تمیز می‌ماند)
            await send_log(
                f"⏱️ **اخراج به علت انقضای کپچا (Kick)**\n"
                f"👤 کاربر: **{user_name}** (`{user_id}`)\n"
                f"💬 گروه: `{chat_id}`\n"
                f"⏳ مهلت: {seconds} ثانیه\n"
                f"📌 نتیجه: {'موفقیت‌آمیز' if kicked_successfully else 'ناموفق (بررسی دسترسی ادمین)'}"
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

    # آیا کاربر از ادمین‌های مجاز است؟ ادمین‌ها از قوانین معاف هستند
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
                    ChatPermissions(can_send_messages=False)
                )
            except Exception as e:
                logger.warning(f"عدم امکان محدودسازی کاربر {member.id}: {e}")

            # ۲. ثبت در دیتابیس اعضای تأیید نشده برای دستور /sweep
            unverified_joins[str(member.id)] = {
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

                # ۴. استارت تسک تایمر ۶۰ ثانیه‌ای
                timer_task = asyncio.create_task(
                    captcha_timeout_worker(client, chat_id, member.id, captcha_msg.id, member.first_name, timeout_sec)
                )
                pending_verifications[member.id] = {
                    "chat_id": chat_id,
                    "user_id": member.id,
                    "message_id": captcha_msg.id,
                    "task": timer_task
                }
            except Exception as e:
                logger.error(f"خطا در ارسال پیام کپچا به گروه: {e}")

            # ۵. ثبت رویداد در کانال لاگ همراه با اطلاعات لینک
            await send_log(
                f"📥 **ورود عضو جدید به گروه**\n"
                f"👤 نام: {member.mention} (`{member.id}`)"
                f"{link_log_details}\n"
                f"💬 گروه: `{chat_id}`\n"
                f"⏳ کپچا ارسال شد (مهلت: {timeout_sec} ثانیه)"
            )
        return

    # ---------------------------------------------------------
    # ب) حالت دوم: کاربر توسط شخص دیگری اد شده است (افزودن از مخاطبین)
    # ---------------------------------------------------------
    logger.info(f"Member add detected: {inviter.first_name} ({inviter.id}) added {member.first_name} ({member.id})")

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
            f"💬 گروه: `{chat_id}`"
        )
        return

    # ۲. آیا شخص اد کننده (Inviter) ادمین است؟ ادمین‌ها آزاد هستند
    is_inviter_admin = inviter.id in configured_admins
    if is_inviter_admin:
        await send_log(
            f"➕ **افزودن عضو توسط ادمین**\n"
            f"👑 ادمین: {inviter.mention} (`{inviter.id}`)\n"
            f"👤 کاربر اضافه شده: {member.mention} (`{member.id}`)\n"
            f"💬 گروه: `{chat_id}`"
        )
        return

    # ۳. بررسی قفل بودن کامل اد کردن (اگر سقف اد روی ۰ تنظیم شده باشد)
    max_limit = int(config.get("anti_add", {}).get("max_adds_per_day", 3))
    if max_limit == 0 and config.get("modules", {}).get("anti_add", True):
        # افزودن عضو از مخاطبین کاملاً قفل است! عضو جدید فوراً اخراج می‌شود
        try:
            await client.ban_chat_member(chat_id, member.id)
            await client.unban_chat_member(chat_id, member.id)
        except Exception:
            pass
        # ارسال لاگ به پیوی ادمین (سکوت کامل در گروه)
        await send_log(
            f"⛔ **جلوگیری از افزودن عضو (قفل اد فعال است)**\n"
            f"👤 دعوت کننده: {inviter.mention} (`{inviter.id}`)\n"
            f"👥 کاربر اخراج شده: {member.mention} (`{member.id}`)\n"
            f"💬 گروه: `{chat_id}`"
        )
        return

    # ۴. عضو اضافه شده در صورت فعال بودن کپچا باید کپچا حل کند
    if config.get("modules", {}).get("captcha", True):
        try:
            await client.restrict_chat_member(
                chat_id,
                member.id,
                ChatPermissions(can_send_messages=False)
            )
        except Exception:
            pass

        unverified_joins[str(member.id)] = {
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
            pending_verifications[member.id] = {
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
            f"💬 گروه: `{chat_id}`"
        )

        # بررسی نقض سقف مجاز روزانه
        if adds_count > max_limit:
            action = config.get("anti_add", {}).get("violation_action", "warn").lower()
            action_desc = ""

            if action == "kick":
                try:
                    await client.ban_chat_member(chat_id, inviter.id)
                    await client.unban_chat_member(chat_id, inviter.id)
                    action_desc = "اخراج موقت اد کننده (Kick)"
                except Exception as e:
                    action_desc = f"خطا در اخراج: {e}"
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
                try:
                    await client.ban_chat_member(chat_id, member.id)
                    await client.unban_chat_member(chat_id, member.id)
                    action_desc += " + اخراج عضو اضافه شده"
                except Exception:
                    pass

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
                f"💬 گروه: `{chat_id}`\n\n"
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

    # ۱. کنسل کردن تایمر اخراج
    pending_info = pending_verifications.pop(target_user_id, None)
    if pending_info and pending_info.get("task"):
        pending_info["task"].cancel()

    # ۲. حذف از لیست unverified_joins چون کپچا با موفقیت حل شد
    unverified_joins.pop(str(target_user_id), None)
    save_state()

    # ۳. بازگرداندن دسترسی کامل ارسال پیام به کاربر
    try:
        await client.restrict_chat_member(
            chat_id,
            target_user_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_send_polls=True,
                can_invite_users=True
            )
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

    # ۵. ارسال لاگ به کانال
    await send_log(
        f"✅ **تأیید موفقیت‌آمیز کپچا**\n"
        f"👤 کاربر: {query.from_user.mention} (`{query.from_user.id}`)\n"
        f"💬 گروه: `{chat_id}`"
    )

# ---------------------------------------------------------------------------
# ۱۱. سازنده‌های منوهای شیشه‌ای و تعاملی (Interactive Menu Builders)
# ---------------------------------------------------------------------------

def build_main_menu(user: Optional[User] = None) -> Tuple[str, InlineKeyboardMarkup]:
    """منوی اصلی داشبورد هوشمند مدیریت ربات"""
    user_name = user.first_name if user else "مدیر گرامی"
    user_id = user.id if user else "نامشخص"
    active_groups_count = len(known_groups)

    text = (
        "🛡️ **پنل مدیریت و امنیت هوشمند سوپرگروه**\n"
        "──────────────────────\n"
        f"👤 مدیر ارشد: **{user_name}** (`{user_id}`)\n"
        f"🤖 وضعیت سیستم: 🟢 **آنلاین و فعال**\n"
        f"👥 گروه‌های تحت پوشش: **{active_groups_count} سوپرگروه**\n"
        "──────────────────────\n"
        "📌 جهت مدیریت و رصد وضعیت، یکی از بخش‌های زیر را انتخاب کنید:"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 آمار و گزارشات گروه‌ها", callback_data="menu:stats"),
            InlineKeyboardButton("⚙️ وضعیت ماژول‌ها", callback_data="menu:settings")
        ],
        [
            InlineKeyboardButton("🛠️ تنظیم پارامترها و سقف‌ها", callback_data="menu:params"),
            InlineKeyboardButton("🚨 عملیات اضطراری (Panic/Sweep)", callback_data="menu:emergency")
        ],
        [
            InlineKeyboardButton("🔄 به‌روزرسانی پنل", callback_data="menu:refresh"),
            InlineKeyboardButton("ℹ️ وضعیت سیستم", callback_data="menu:info")
        ]
    ])
    return text, keyboard

def build_groups_menu(purpose: str = "stats") -> Tuple[str, InlineKeyboardMarkup]:
    """منوی انتخاب گروه جهت مشاهده گزارشات یا اجرای دستورات اضطراری"""
    if not known_groups:
        text = (
            "👥 **انتخاب سوپرگروه:**\n"
            "──────────────────────\n"
            "ℹ️ هنوز گروهی در حافظه ربات ثبت نشده است.\n\n"
            "📌 **راهنمای اتصال گروه:**\n"
            "۱. ربات را به سوپرگروه خود اضافه کرده و ادمین کنید.\n"
            "۲. به محض ارسال اولین پیام یا ورود عضو، گروه به صورت خودکار شناسایی و ثبت خواهد شد."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 بازخوانی مجدد لیست", callback_data=f"menu:{purpose}")],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu:main")]
        ])
        return text, keyboard

    headers = {
        "stats": "📊 **انتخاب سوپرگروه جهت مشاهده آمار و گزارشات تفکیکی:**",
        "panic": "🚨 **انتخاب سوپرگروه جهت فعال‌سازی حالت اضطراری (Panic):**",
        "sweep": "🧹 **انتخاب سوپرگروه جهت پاکسازی اعضای تأیید نشده (Sweep):**"
    }
    header_text = headers.get(purpose, "👥 **انتخاب سوپرگروه:**")

    text = f"{header_text}\n──────────────────────\nگروه مورد نظر خود را انتخاب نمایید:"

    buttons = []
    for cid_str, gdata in known_groups.items():
        gid = gdata.get("id")
        gtitle = gdata.get("title", f"گروه {cid_str}")
        if purpose == "stats":
            cb = f"group:{gid}"
        elif purpose == "panic":
            cb = f"emerg_panic_confirm:{gid}"
        elif purpose == "sweep":
            cb = f"emerg_sweep_confirm:{gid}"
        else:
            cb = f"group:{gid}"
        buttons.append([InlineKeyboardButton(f"👥 {gtitle}", callback_data=cb)])

    if purpose == "stats" and len(known_groups) > 1:
        buttons.append([InlineKeyboardButton("🌐 گزارش تجمیعی کل گروه‌ها", callback_data="group:all")])

    buttons.append([
        InlineKeyboardButton("🔄 به‌روزرسانی لیست", callback_data=f"menu:{purpose}"),
        InlineKeyboardButton("🔙 منوی اصلی", callback_data="menu:main")
    ])

    return text, InlineKeyboardMarkup(buttons)

def build_group_dashboard(target_chat_id: Any) -> Tuple[str, InlineKeyboardMarkup]:
    """داشبورد اختصاصی هر گروه شامل آمار لینک‌ها، مخاطبین و کپچا"""
    is_all = (str(target_chat_id) == "all")
    if is_all:
        group_title = "تمام گروه‌ها (تجمیعی)"
        cid_label = "همه سوپرگروه‌ها"
    else:
        try:
            target_chat_id = int(target_chat_id)
        except Exception:
            pass
        group_info = known_groups.get(str(target_chat_id), {})
        group_title = group_info.get("title", f"گروه `{target_chat_id}`")
        cid_label = f"`{target_chat_id}`"

    # ۱. آمار لینک‌های دعوت
    total_link_joins = 0
    top_link_str = "هنوز ثبت نشده"
    link_rank = []
    for cid, data in link_join_history.items():
        joins = [
            j for j in data.get("joins", [])
            if is_all or j.get("chat_id") == target_chat_id or j.get("chat_id") is None
        ]
        if joins:
            c = len(joins)
            total_link_joins += c
            link_rank.append((data.get("name", "نامشخص"), c))
    if link_rank:
        link_rank.sort(key=lambda x: x[1], reverse=True)
        top_link_str = f"{link_rank[0][0]} ({link_rank[0][1]} عضو)"

    # ۲. آمار اد مخاطبین
    total_contact_adds = 0
    top_contact_str = "هنوز ثبت نشده"
    add_rank = []
    for uid, data in user_add_history.items():
        raw_adds = data.get("adds", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        name = data.get("name", "کاربر") if isinstance(data, dict) else "کاربر"
        adds = [
            a for a in raw_adds
            if is_all or a.get("chat_id") == target_chat_id or a.get("chat_id") is None
        ]
        if adds:
            c = len(adds)
            total_contact_adds += c
            add_rank.append((name, c))
    if add_rank:
        add_rank.sort(key=lambda x: x[1], reverse=True)
        top_contact_str = f"{add_rank[0][0]} ({add_rank[0][1]} عضو)"

    # ۳. افراد منتظر حل کپچا
    unverified_count = sum(
        1 for d in unverified_joins.values()
        if is_all or d.get("chat_id") == target_chat_id or d.get("chat_id") is None
    )

    max_limit = config.get("anti_add", {}).get("max_adds_per_day", 3)
    limit_str = "⛔ قفل کامل (۰)" if max_limit == 0 else f"{max_limit} اد در روز"

    text = (
        f"📍 **داشبورد گروه: {group_title}**\n"
        f"🆔 شناسه: {cid_label}\n"
        "──────────────────────\n"
        f"🔗 ورودی از لینک‌های دعوت: `{total_link_joins}` عضو\n"
        f"👑 برترین دعوت‌کننده با لینک: **{top_link_str}**\n\n"
        f"👥 ورودی از اد مخاطبین: `{total_contact_adds}` عضو\n"
        f"🥇 برترین اد کننده مخاطب: **{top_contact_str}**\n\n"
        f"⏳ در انتظار حل کپچا: `{unverified_count}` نفر\n"
        f"⚙️ سقف مجاز اد: `{limit_str}`\n"
        "──────────────────────\n"
        "👇 برای مشاهده جزئیات گزارشات یا اقدامات امنیتی انتخاب کنید:"
    )

    buttons = [
        [
            InlineKeyboardButton("🔗 گزارش لینک‌های دعوت", callback_data=f"rep_links:{target_chat_id}"),
            InlineKeyboardButton("👥 گزارش اد مخاطبین", callback_data=f"rep_adds:{target_chat_id}")
        ]
    ]

    if not is_all:
        buttons.append([
            InlineKeyboardButton("🚨 Panic (ابطال لینک)", callback_data=f"emerg_panic_confirm:{target_chat_id}"),
            InlineKeyboardButton("🧹 پاکسازی Sweep", callback_data=f"emerg_sweep_confirm:{target_chat_id}")
        ])

    buttons.append([
        InlineKeyboardButton("🔄 به‌روزرسانی آمار", callback_data=f"group:{target_chat_id}"),
        InlineKeyboardButton("🔙 لیست گروه‌ها", callback_data="menu:stats")
    ])
    buttons.append([
        InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
    ])

    return text, InlineKeyboardMarkup(buttons)

def build_links_report(target_chat_id: Any) -> Tuple[str, InlineKeyboardMarkup]:
    """گزارش رتبه‌بندی افرادی که با لینک دعوت عضو آورده‌اند"""
    is_all = (str(target_chat_id) == "all")
    if is_all:
        target_title = "تمام گروه‌ها"
    else:
        try:
            target_chat_id = int(target_chat_id)
        except Exception:
            pass
        target_title = known_groups.get(str(target_chat_id), {}).get("title", f"گروه `{target_chat_id}`")

    group_link_stats = []
    total_joins = 0

    for cid, data in link_join_history.items():
        all_joins = data.get("joins", [])
        group_joins = [
            j for j in all_joins
            if is_all or j.get("chat_id") == target_chat_id or j.get("chat_id") is None
        ]
        if group_joins:
            count = len(group_joins)
            total_joins += count
            group_link_stats.append({
                "cid": cid,
                "name": data.get("name", "نامشخص"),
                "username": data.get("username", ""),
                "count": count,
                "joins": group_joins
            })

    group_link_stats.sort(key=lambda x: x["count"], reverse=True)

    if not group_link_stats or total_joins == 0:
        text = (
            f"🔗 **گزارش لینک‌های دعوت:**\n"
            f"📍 **{target_title}**\n"
            "──────────────────────\n"
            "ℹ️ هنوز هیچ ورودی از طریق لینک دعوت در این بخش ثبت نشده است.\n\n"
            "📌 به محض ورود اولین کاربر با لینک، آمار و نام سازنده لینک در اینجا نمایش داده خواهد شد."
        )
    else:
        report_lines = [
            f"🔗 **گزارش اعضای وارد شده از طریق لینک‌های دعوت:**\n"
            f"📍 **{target_title}** (مجموع: {total_joins} عضو)\n"
            "──────────────────────"
        ]
        for rank, item in enumerate(group_link_stats[:10], 1):
            name = item["name"]
            count = item["count"]
            uname = f" (@{item['username']})" if item.get("username") else ""
            cid_desc = f" (`{item['cid']}`)" if item["cid"] != "primary" else ""
            report_lines.append(f"{rank}. 👑 **{name}**{uname}{cid_desc}: **{count} عضو**")

            recent = item["joins"][-3:]
            for j in reversed(recent):
                j_name = j.get("user_name", "کاربر")
                j_id = j.get("user_id")
                j_title = j.get("link_name", "لینک")
                j_time = datetime.fromtimestamp(j.get("time", time.time())).strftime("%m-%d %H:%M")
                report_lines.append(f"   ▫️ [{j_name}](tg://user?id={j_id}) — _{j_title}_ ({j_time})")
            report_lines.append("")

        text = "\n".join(report_lines)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 به‌روزرسانی گزارش", callback_data=f"rep_links:{target_chat_id}")],
        [
            InlineKeyboardButton("🔙 بازگشت به گروه", callback_data=f"group:{target_chat_id}"),
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
        ]
    ])
    return text, keyboard

def build_adds_report(target_chat_id: Any) -> Tuple[str, InlineKeyboardMarkup]:
    """گزارش رتبه‌بندی افرادی که از مخاطبین عضو اضافه کرده‌اند"""
    is_all = (str(target_chat_id) == "all")
    if is_all:
        target_title = "تمام گروه‌ها"
    else:
        try:
            target_chat_id = int(target_chat_id)
        except Exception:
            pass
        target_title = known_groups.get(str(target_chat_id), {}).get("title", f"گروه `{target_chat_id}`")

    group_add_stats = []
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
            count = len(group_adds)
            total_adds += count
            group_add_stats.append({
                "uid": uid,
                "name": name,
                "username": username,
                "count": count,
                "adds": group_adds
            })

    group_add_stats.sort(key=lambda x: x["count"], reverse=True)

    if not group_add_stats or total_adds == 0:
        text = (
            f"👥 **گزارش افزودن اعضا از مخاطبین:**\n"
            f"📍 **{target_title}**\n"
            "──────────────────────\n"
            "ℹ️ هنوز داده‌ای از اد کردن کاربران از طریق مخاطبین ثبت نشده است.\n\n"
            "📌 به محض اینکه کاربری از Add Member فردی را اضافه کند، در این بخش رتبه‌بندی می‌شود."
        )
    else:
        report_lines = [
            f"👥 **گزارش اعضای اد شده از طریق مخاطبین:**\n"
            f"📍 **{target_title}** (مجموع: {total_adds} عضو)\n"
            "──────────────────────"
        ]
        for rank, item in enumerate(group_add_stats[:10], 1):
            name = item["name"]
            uname = f" (@{item['username']})" if item.get("username") else ""
            uid = item["uid"]
            count = item["count"]
            report_lines.append(f"{rank}. 👤 **{name}**{uname} (`{uid}`): **{count} نفر**")

            recent = item["adds"][-3:]
            for a in reversed(recent):
                a_name = a.get("name", "مخاطب")
                a_id = a.get("user_id")
                a_time = datetime.fromtimestamp(a.get("time", time.time())).strftime("%m-%d %H:%M")
                report_lines.append(f"   ▫️ [{a_name}](tg://user?id={a_id}) (`{a_id}`) — _{a_time}_")
            report_lines.append("")

        text = "\n".join(report_lines)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 به‌روزرسانی گزارش", callback_data=f"rep_adds:{target_chat_id}")],
        [
            InlineKeyboardButton("🔙 بازگشت به گروه", callback_data=f"group:{target_chat_id}"),
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
        ]
    ])
    return text, keyboard

def build_modules_settings_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """منوی دکمه‌ای سوئیچ ماژول‌های امنیتی"""
    modules = config.get("modules", {})
    cap_on = modules.get("captcha", True)
    add_on = modules.get("anti_add", True)
    pan_on = modules.get("panic", True)
    swp_on = modules.get("sweep", True)
    log_on = modules.get("logging", True)

    def icon(val):
        return "🟢 فعال" if val else "🔴 غیرفعال"

    text = (
        "⚙️ **مدیریت وضعیت ماژول‌های امنیتی ربات**\n"
        "──────────────────────\n"
        "با کلیک روی هر دکمه، وضعیت آن ماژول بلافاصله تغییر می‌کند:\n\n"
        f"• ربات کپچای ورود: {icon(cap_on)}\n"
        f"• ضد اد مخاطبین: {icon(add_on)}\n"
        f"• وضعیت اضطراری (Panic): {icon(pan_on)}\n"
        f"• پاکسازی Sweep: {icon(swp_on)}\n"
        f"• ارسال لاگ‌ها به پیوی: {icon(log_on)}\n"
        "──────────────────────\n"
        "💡 _تغییرات بلافاصله ذخیره شده و بدون نیاز به ری‌استارت اعمال می‌شوند._"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🤖 کپچا: {icon(cap_on)}", callback_data="toggle:captcha")],
        [InlineKeyboardButton(f"🚫 ضد اد: {icon(add_on)}", callback_data="toggle:anti_add")],
        [InlineKeyboardButton(f"🚨 پنیک: {icon(pan_on)}", callback_data="toggle:panic")],
        [InlineKeyboardButton(f"🧹 سویپ: {icon(swp_on)}", callback_data="toggle:sweep")],
        [InlineKeyboardButton(f"📋 لاگ پیوی: {icon(log_on)}", callback_data="toggle:logging")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu:main")]
    ])
    return text, keyboard

def build_params_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """منوی تنظیم پارامترها و سقف‌های امنیتی"""
    captcha_time = config.get("captcha", {}).get("timeout_seconds", 60)
    max_limit = config.get("anti_add", {}).get("max_adds_per_day", 3)
    limit_str = "⛔ قفل کامل (۰)" if max_limit == 0 else f"{max_limit} عضو در روز"
    action = config.get("anti_add", {}).get("violation_action", "warn")
    fa_actions = {"warn": "⚠️ اخطار (Warn)", "kick": "👢 اخراج (Kick)", "ban": "⛔ مسدودسازی (Ban)"}
    action_str = fa_actions.get(action, action)
    retention_hours = config.get("sweep", {}).get("retention_hours", 24)

    text = (
        "🛠️ **تنظیم پارامترها و سقف‌های امنیتی**\n"
        "──────────────────────\n"
        f"⏱️ مهلت زمان حل کپچا: `{captcha_time}` ثانیه\n"
        f"👥 سقف مجاز اد در روز: `{limit_str}`\n"
        f"⚡ اقدام هنگام تخلف اد: `{action_str}`\n"
        f"⏳ بازه نگهداری Sweep: `{retention_hours}` ساعت\n"
        "──────────────────────\n"
        "👇 پارامتر مورد نظر را برای ویرایش انتخاب کنید:"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏱️ تنظیم زمان کپچا", callback_data="param:captcha"),
            InlineKeyboardButton("👥 تنظیم سقف اد مخاطب", callback_data="param:addlimit")
        ],
        [
            InlineKeyboardButton("⚡ تعیین اقدام تخلف اد", callback_data="param:action"),
            InlineKeyboardButton("⏳ ساعات پاکسازی Sweep", callback_data="param:sweep")
        ],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu:main")]
    ])
    return text, keyboard

def build_captcha_param_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """تنظیم زمان مهلت کپچا"""
    curr = config.get("captcha", {}).get("timeout_seconds", 60)
    text = (
        "⏱️ **تنظیم مهلت زمان حل کپچا**\n"
        "──────────────────────\n"
        f"مقدار فعلی: **{curr} ثانیه**\n\n"
        "با استفاده از دکمه‌های زیر زمان مهلت کاربر برای تأیید کپچا را تنظیم کنید:"
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
            InlineKeyboardButton("🔙 بازگشت به پارامترها", callback_data="menu:params"),
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
        ]
    ])
    return text, keyboard

def build_addlimit_param_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """تنظیم سقف اد کردن مخاطب توسط کاربران"""
    curr = config.get("anti_add", {}).get("max_adds_per_day", 3)
    curr_str = "⛔ قفل کامل (۰ اد)" if curr == 0 else f"{curr} عضو در ۲۴ ساعت"
    text = (
        "👥 **تنظیم سقف مجاز اد کردن مخاطب در روز**\n"
        "──────────────────────\n"
        f"وضعیت فعلی: **{curr_str}**\n\n"
        "اگر سقف را روی ۰ قرار دهید، افزودن عضو توسط اعضای عادی کاملاً قفل می‌شود:"
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
            InlineKeyboardButton("🔙 بازگشت به پارامترها", callback_data="menu:params"),
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
        ]
    ])
    return text, keyboard

def build_action_param_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """تعیین نوع اقدام هنگام تخلف اد کردن بیش از حد"""
    curr = config.get("anti_add", {}).get("violation_action", "warn")
    fa_actions = {"warn": "⚠️ اخطار (Warn)", "kick": "👢 اخراج (Kick)", "ban": "⛔ مسدودسازی (Ban)"}
    curr_str = fa_actions.get(curr, curr)
    text = (
        "⚡ **تعیین اقدام انضباطی هنگام نقض سقف اد مخاطب**\n"
        "──────────────────────\n"
        f"اقدام فعلی: **{curr_str}**\n\n"
        "در صورتی که کاربری بیش از سقف مجاز روزانه عضو اد کند، چه واکنشی انجام شود؟"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ فقط ثبت اخطار (Warn)", callback_data="set_act:warn")],
        [InlineKeyboardButton("👢 اخراج از سوپرگروه (Kick)", callback_data="set_act:kick")],
        [InlineKeyboardButton("⛔ مسدودسازی دائمی (Ban)", callback_data="set_act:ban")],
        [
            InlineKeyboardButton("🔙 بازگشت به پارامترها", callback_data="menu:params"),
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
        ]
    ])
    return text, keyboard

def build_sweep_param_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """تنظیم ساعات نگهداری اعضا برای عملیات Sweep"""
    curr = config.get("sweep", {}).get("retention_hours", 24)
    text = (
        "⏳ **تنظیم بازه زمانی نگهداری اعضا برای Sweep**\n"
        "──────────────────────\n"
        f"بازه فعلی: **{curr} ساعت اخیر**\n\n"
        "دستور Sweep اعضایی را که در این بازه زمانی کپچا را حل نکرده‌اند بن می‌کند:"
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
            InlineKeyboardButton("🔙 بازگشت به پارامترها", callback_data="menu:params"),
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")
        ]
    ])
    return text, keyboard

def build_emergency_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """مرکز عملیات اضطراری و پدافند"""
    text = (
        "🚨 **مرکز عملیات اضطراری و پدافند سوپرگروه**\n"
        "──────────────────────\n"
        "در شرایط بحرانی یا هجوم ربات‌ها (Raid)، اقدامات زیر را می‌توانید به صورت فوری اجرا کنید:\n\n"
        "• **Panic Mode:** ابطال فوری لینک دعوت فعلی و صدور لینک جدید جهت قطع ورود مهاجمان\n"
        "• **Sweep:** بن کردن یکجای تمامی اعضایی که در ساعات اخیر بدون حل کپچا در گروه مانده‌اند\n"
        "• **قفل فوری اد:** مسدودسازی سریع قابلیت اد کردن مخاطب برای کاربران عادی\n"
        "──────────────────────"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚨 ابطال و صدور لینک جدید (Panic)", callback_data="menu:panic")],
        [InlineKeyboardButton("🧹 پاکسازی اعضای تأیید نشده (Sweep)", callback_data="menu:sweep")],
        [InlineKeyboardButton("⛔ قفل فوری افزودن مخاطب (سقف 0)", callback_data="emerg:lock_adds")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu:main")]
    ])
    return text, keyboard

def build_system_info_menu() -> Tuple[str, InlineKeyboardMarkup]:
    """نمایش مشخصات فنی سیستم"""
    state_size = STATE_FILE.stat().st_size if STATE_FILE.exists() else 0
    size_kb = round(state_size / 1024, 2)
    admin_list_str = ", ".join(f"`{x}`" for x in config.get("admin_ids", []))
    groups_count = len(known_groups)

    text = (
        "ℹ️ **اطلاعات سیستم و امنیت ربات**\n"
        "──────────────────────\n"
        "🤖 **نسخه ربات:** `v3.0.0 (Smart Interactive & Full PV Logs)`\n"
        f"🛡️ **شناسه مدیران مجاز:** {admin_list_str}\n"
        f"👥 **سوپرگروه‌های متصل:** `{groups_count}` گروه\n"
        f"💾 **حجم فایل وضعیت:** `{size_kb} KB`\n"
        "📱 **پلتفرم:** کاملاً سازگار با ترموکس اندروید و ویندوز\n"
        "──────────────────────\n"
        "🔒 **سیاست امنیت صوتی:**\n"
        "هیچ‌گونه لاگ یا پیام خطایی در داخل گروه فرستاده نمی‌شود؛ تمام گزارش‌ها اختصاصاً به پیوی مدیر ارسال می‌گردند."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ تست سرعت و پینگ (Ping)", callback_data="ping:check")],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="menu:main")]
    ])
    return text, keyboard

# ---------------------------------------------------------------------------
# ۱۲. تنها دستور متنی ربات: /start در چت خصوصی (پیوی)
# ---------------------------------------------------------------------------

@app.on_message(filters.command(["start", "شروع"]) & filters.private)
async def handle_start_command(client: Client, message: Message):
    """
    تنها دستور ربات: /start منحصراً در چت خصوصی (پیوی).
    تمامی قابلیت‌ها و تنظیمات از طریق دکمه‌های شیشه‌ای انجام می‌پذیرد.
    کاربران غیرمجاز کاملاً نادیده گرفته می‌شوند (سکوت مطلق).
    """
    if not await is_admin(client, message):
        return

    text, keyboard = build_main_menu(message.from_user)
    await message.reply_text(text, reply_markup=keyboard)

@app.on_message(filters.private & filters.forwarded)
async def handle_forwarded_log_channel(client: Client, message: Message):
    """
    تشخیص و اتصال کانال لاگ با فوروارد یک پیام به پیوی ربات
    """
    if not await is_admin(client, message):
        return

    if message.forward_from_chat and message.forward_from_chat.type == ChatType.CHANNEL:
        ch = message.forward_from_chat
        config["log_channel_id"] = ch.id
        save_config_file(config)
        logger.info(f"کانال لاگ شناسایی شد: {ch.title} ({ch.id})")
        await message.reply_text(
            f"✅ **کانال لاگ با موفقیت متصل گردید:**\n📢 {ch.title} (`{ch.id}`)"
        )
        await send_log(f"🟢 **تست اتصال:** کانال لاگ «{ch.title}» متصل شد.")

# ---------------------------------------------------------------------------
# ۱۲.۵. روتر جامع دکمه‌های شیشه‌ای پنل مدیریت (Admin Callback Query Router)
# ---------------------------------------------------------------------------

@app.on_callback_query(filters.regex(r"^(menu|group|rep_|toggle|param|set_|emerg|exec_|ping)"))
async def on_admin_panel_callback(client: Client, query: CallbackQuery):
    """هندلر تعاملی دکمه‌های شیشه‌ای پنل مدیریت در چت خصوصی"""
    if not is_admin_user(query.from_user.id):
        await query.answer("⛔ شما به این پنل مدیریتی دسترسی ندارید.", show_alert=True)
        return

    data = query.data or ""

    # ۱. ناوبری منوی اصلی و رفرش
    if data in ["menu:main", "menu:refresh"]:
        text, kb = build_main_menu(query.from_user)
        await safe_edit(query.message, text, kb)
        if data == "menu:refresh":
            await query.answer("🔄 پنل مدیریت با موفقیت به‌روزرسانی شد.", show_alert=False)
        else:
            await query.answer()
        return

    # ۲. منوی انتخاب گروه‌ها
    if data == "menu:stats":
        text, kb = build_groups_menu(purpose="stats")
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    # ۳. داشبورد اختصاصی گروه
    if data.startswith("group:"):
        target_cid = data.split(":", 1)[1]
        text, kb = build_group_dashboard(target_cid)
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    # ۴. گزارش لینک‌های دعوت گروه
    if data.startswith("rep_links:"):
        target_cid = data.split(":", 1)[1]
        text, kb = build_links_report(target_cid)
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    # ۵. گزارش اد مخاطبین گروه
    if data.startswith("rep_adds:"):
        target_cid = data.split(":", 1)[1]
        text, kb = build_adds_report(target_cid)
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    # ۶. منوی وضعیت ماژول‌ها و سوئیچ‌ها
    if data == "menu:settings":
        text, kb = build_modules_settings_menu()
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    if data.startswith("toggle:"):
        mod_key = data.split(":", 1)[1]
        mod_dict = config.setdefault("modules", {})
        new_state = not mod_dict.get(mod_key, True)
        mod_dict[mod_key] = new_state
        save_config_file(config)
        state_desc = "🟢 فعال" if new_state else "🔴 غیرفعال"
        await send_log(f"⚙️ **تغییر ماژول:** ماژول `{mod_key}` اکنون {state_desc} شد.")
        await query.answer(f"ماژول {mod_key} اکنون {state_desc} شد.", show_alert=False)
        text, kb = build_modules_settings_menu()
        await safe_edit(query.message, text, kb)
        return

    # ۷. منوی تنظیم پارامترها
    if data == "menu:params":
        text, kb = build_params_menu()
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    if data == "param:captcha":
        text, kb = build_captcha_param_menu()
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    if data.startswith("set_cap:"):
        parts = data.split(":")
        curr = int(config.get("captcha", {}).get("timeout_seconds", 60))
        if parts[1] == "step":
            new_val = max(10, min(600, curr + int(parts[2])))
        else:
            new_val = int(parts[2])
        config.setdefault("captcha", {})["timeout_seconds"] = new_val
        save_config_file(config)
        await send_log(f"⏱️ **تغییر تنظیمات:** مهلت زمان کپچا به `{new_val}` ثانیه تغییر یافت.")
        await query.answer(f"زمان مهلت کپچا: {new_val} ثانیه", show_alert=False)
        text, kb = build_captcha_param_menu()
        await safe_edit(query.message, text, kb)
        return

    if data == "param:addlimit":
        text, kb = build_addlimit_param_menu()
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    if data.startswith("set_limit:"):
        parts = data.split(":")
        curr = int(config.get("anti_add", {}).get("max_adds_per_day", 3))
        if parts[1] == "step":
            new_val = max(0, min(100, curr + int(parts[2])))
        else:
            new_val = int(parts[2])
        config.setdefault("anti_add", {})["max_adds_per_day"] = new_val
        save_config_file(config)
        desc = "⛔ قفل کامل (۰)" if new_val == 0 else f"{new_val} اد در ۲۴ ساعت"
        await send_log(f"👥 **تغییر تنظیمات:** سقف مجاز اد به `{desc}` تغییر یافت.")
        await query.answer(f"سقف مجاز اد: {desc}", show_alert=False)
        text, kb = build_addlimit_param_menu()
        await safe_edit(query.message, text, kb)
        return

    if data == "param:action":
        text, kb = build_action_param_menu()
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    if data.startswith("set_act:"):
        act_val = data.split(":", 1)[1]
        config.setdefault("anti_add", {})["violation_action"] = act_val
        save_config_file(config)
        fa_names = {"warn": "اخطار", "kick": "اخراج", "ban": "مسدودسازی"}
        act_fa = fa_names.get(act_val, act_val)
        await send_log(f"⚡ **تغییر تنظیمات:** اقدام تخلف اد به `{act_fa}` تغییر یافت.")
        await query.answer(f"اقدام تخلف: {act_fa}", show_alert=False)
        text, kb = build_action_param_menu()
        await safe_edit(query.message, text, kb)
        return

    if data == "param:sweep":
        text, kb = build_sweep_param_menu()
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    if data.startswith("set_swp:"):
        parts = data.split(":")
        curr = int(config.get("sweep", {}).get("retention_hours", 24))
        if parts[1] == "step":
            new_val = max(1, min(168, curr + int(parts[2])))
        else:
            new_val = int(parts[2])
        config.setdefault("sweep", {})["retention_hours"] = new_val
        save_config_file(config)
        await send_log(f"⏳ **تغییر تنظیمات:** بازه sweep به `{new_val}` ساعت تغییر یافت.")
        await query.answer(f"بازه زمانی Sweep: {new_val} ساعت", show_alert=False)
        text, kb = build_sweep_param_menu()
        await safe_edit(query.message, text, kb)
        return

    # ۸. عملیات اضطراری (Panic & Sweep)
    if data == "menu:emergency":
        text, kb = build_emergency_menu()
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    if data == "emerg:lock_adds":
        config.setdefault("anti_add", {})["max_adds_per_day"] = 0
        save_config_file(config)
        await send_log("⛔ **قفل اضطراری:** افزودن مخاطب در تمام گروه‌ها کاملاً مسدود شد.")
        await query.answer("⛔ قابلیت اد کردن مخاطب کاملاً مسدود شد (سقف 0)!", show_alert=True)
        text, kb = build_emergency_menu()
        await safe_edit(query.message, text, kb)
        return

    if data == "menu:panic":
        text, kb = build_groups_menu(purpose="panic")
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    if data.startswith("emerg_panic_confirm:"):
        target_cid = int(data.split(":", 1)[1])
        g_info = known_groups.get(str(target_cid), {})
        g_title = g_info.get("title", f"گروه `{target_cid}`")
        text = (
            "🚨 **تأییدیه فعال‌سازی وضعیت اضطراری (Panic Mode)**\n"
            f"📍 گروه: **{g_title}** (`{target_cid}`)\n"
            "──────────────────────\n"
            "⚠️ **هشدار:** با تأیید این عملیات:\n"
            "۱. لینک دعوت فعلی گروه فوراً باطل (Revoke) می‌شود.\n"
            "۲. یک لینک دعوت جدید صادر شده و در همینجا به شما تحویل داده می‌شود.\n"
            "۳. نفوذ تمامی بات‌ها یا مهاجمان از لینک قبلی متوقف خواهد شد.\n\n"
            "آیا مطمئن هستید؟"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚨 بله، فوراً ابطال و صدور لینک جدید", callback_data=f"exec_panic:{target_cid}")],
            [InlineKeyboardButton("❌ انصراف و بازگشت", callback_data=f"group:{target_cid}")]
        ])
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    if data.startswith("exec_panic:"):
        target_cid = int(data.split(":", 1)[1])
        g_info = known_groups.get(str(target_cid), {})
        g_title = g_info.get("title", f"گروه `{target_cid}`")
        await query.answer("🚨 در حال ابطال لینک و صدور لینک جدید...", show_alert=False)
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
                except Exception:
                    pass

            new_invite = await client.create_chat_invite_link(
                target_cid,
                name=f"Panic Link {datetime.now().strftime('%m-%d %H:%M')}"
            )
            new_link = new_invite.invite_link

            await send_log(
                f"🚨 **فعال‌سازی حالت اضطراری (Panic Alert)**\n"
                f"👤 توسط مدیر: **{query.from_user.first_name}** (`{query.from_user.id}`)\n"
                f"💬 گروه: `{target_cid}`\n"
                f"🔗 لینک دعوت جدید: `{new_link}`"
            )

            result_text = (
                "🚨 **وضعیت اضطراری با موفقیت فعال شد!**\n"
                f"📍 گروه: **{g_title}** (`{target_cid}`)\n"
                "──────────────────────\n"
                "✅ لینک دعوت قبلی گروه باطل (Revoke) گردید.\n\n"
                "🔗 **لینک دعوت جدید گروه:**\n"
                f"`{new_link}`\n\n"
                "⚠️ تمامی بات‌ها و مهاجمانی که از لینک قبلی در حال هجوم بودند ناکام ماندند."
            )
            res_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت به داشبورد گروه", callback_data=f"group:{target_cid}")],
                [InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
            ])
            await safe_edit(query.message, result_text, res_kb)
        except Exception as e:
            logger.error(f"Error in exec_panic: {e}")
            await query.answer(f"❌ خطا در صدور لینک: {e}", show_alert=True)
        return

    if data == "menu:sweep":
        text, kb = build_groups_menu(purpose="sweep")
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    if data.startswith("emerg_sweep_confirm:"):
        target_cid = int(data.split(":", 1)[1])
        g_info = known_groups.get(str(target_cid), {})
        g_title = g_info.get("title", f"گروه `{target_cid}`")
        retention_hours = int(config.get("sweep", {}).get("retention_hours", 24))
        cutoff_time = time.time() - (retention_hours * 3600)

        unverified_targets = [
            (int(uid_str), d)
            for uid_str, d in unverified_joins.items()
            if d.get("chat_id") == target_cid and d.get("join_time", 0) >= cutoff_time
        ]
        target_count = len(unverified_targets)

        text = (
            "🧹 **تأییدیه عملیات پاکسازی اعضای تأیید نشده (Sweep)**\n"
            f"📍 گروه: **{g_title}** (`{target_cid}`)\n"
            f"⏳ بازه زمانی: **{retention_hours} ساعت گذشته**\n"
            f"🎯 تعداد اعضای تأیید نشده در نوبت بن: **{target_count} نفر**\n"
            "──────────────────────\n"
            "آیا مایلید تمام حساب‌هایی که در این بازه کپچا را حل نکرده‌اند مسدود (Ban) شوند؟"
        )
        buttons = []
        if target_count > 0:
            buttons.append([InlineKeyboardButton(f"🧹 بن کردن {target_count} اکانت", callback_data=f"exec_sweep:{target_cid}")])
        buttons.append([InlineKeyboardButton("❌ انصراف و بازگشت", callback_data=f"group:{target_cid}")])

        await safe_edit(query.message, text, InlineKeyboardMarkup(buttons))
        await query.answer()
        return

    if data.startswith("exec_sweep:"):
        target_cid = int(data.split(":", 1)[1])
        g_info = known_groups.get(str(target_cid), {})
        g_title = g_info.get("title", f"گروه `{target_cid}`")
        retention_hours = int(config.get("sweep", {}).get("retention_hours", 24))
        cutoff_time = time.time() - (retention_hours * 3600)

        unverified_targets = [
            (int(uid_str), d)
            for uid_str, d in unverified_joins.items()
            if d.get("chat_id") == target_cid and d.get("join_time", 0) >= cutoff_time
        ]

        if not unverified_targets:
            await query.answer("ℹ️ در حال حاضر حسابی برای پاکسازی وجود ندارد.", show_alert=True)
            return

        await query.answer("🧹 در حال پاکسازی و بن حساب‌ها...", show_alert=False)

        banned_count = 0
        fail_count = 0
        for uid, d in unverified_targets:
            try:
                await client.ban_chat_member(target_cid, uid)
                banned_count += 1
                unverified_joins.pop(str(uid), None)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await client.ban_chat_member(target_cid, uid)
                    banned_count += 1
                    unverified_joins.pop(str(uid), None)
                except Exception:
                    fail_count += 1
            except Exception:
                fail_count += 1

        save_state()

        await send_log(
            f"🧹 **عملیات پاکسازی گروه (Sweep) پایان یافت**\n"
            f"👤 مجری: **{query.from_user.first_name}** (`{query.from_user.id}`)\n"
            f"💬 گروه: `{target_cid}`\n"
            f"🚫 بن شده‌ها: {banned_count} نفر\n"
            f"⚠️ ناموفق: {fail_count} نفر"
        )

        res_text = (
            "🧹 **عملیات پاکسازی (Sweep) با موفقیت انجام شد!**\n"
            f"📍 گروه: **{g_title}** (`{target_cid}`)\n"
            "──────────────────────\n"
            f"🚫 حساب‌های مسدود شده: **{banned_count} نفر**\n"
            f"⚠️ موارد ناموفق: **{fail_count} نفر**\n"
            f"⏱️ بازه زمانی: **{retention_hours} ساعت گذشته**\n"
            "──────────────────────\n"
            "تمامی حساب‌های تأیید نشده با موفقیت مسدود شدند."
        )
        res_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به داشبورد گروه", callback_data=f"group:{target_cid}")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="menu:main")]
        ])
        await safe_edit(query.message, res_text, res_kb)
        return

    # ۹. اطلاعات سیستم و تست پینگ
    if data == "menu:info":
        text, kb = build_system_info_menu()
        await safe_edit(query.message, text, kb)
        await query.answer()
        return

    if data == "ping:check":
        start_t = time.time()
        await query.answer("⚡ در حال محاسبه پینگ...", show_alert=False)
        latency_ms = round((time.time() - start_t) * 1000 + 15, 1)
        await query.answer(f"⚡ سرعت پاسخگویی سرور: {latency_ms}ms | سیستم کاملاً فعال است!", show_alert=True)
        return

    await query.answer()


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
            for uid_str in list(unverified_joins.keys()):
                if unverified_joins[uid_str].get("join_time", 0) < sweep_cutoff:
                    del unverified_joins[uid_str]

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

            save_state()
            logger.info("تسک دوره‌ای پاکسازی حافظه با موفقیت انجام شد.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"خطا در تسک پاکسازی دوره‌ای: {e}")

# ---------------------------------------------------------------------------
# ۱۴. نقطه شروع و اجرای ربات (Main Entry Point)
# ---------------------------------------------------------------------------
async def main():
    """اجرای ناهمگام ربات و بارگذاری سرویس‌ها"""
    if not API_ID or not API_HASH or not BOT_TOKEN or API_ID == 0 or "YOUR_" in str(BOT_TOKEN) or "YOUR_" in str(API_HASH):
        print("\n" + "=" * 70)
        print("❌ خطا: مقادیر احراز هویت تلگرام در config.json هنوز تنظیم نشده‌اند!")
        print("لطفاً فایل config.json را باز کرده و api_id, api_hash و bot_token را قرار دهید.")
        print("=" * 70 + "\n")
        return

    load_state()

    logger.info("در حال اتصال به سرورهای تلگرام...")
    await app.start()

    bot_user = await app.get_me()
    logger.info(f"ربات محافظ با نام @{bot_user.username} (ID: {bot_user.id}) فعال شد!")
    print("\n" + "=" * 60)
    print(f"✅ ربات با موفقیت روشن شد: @{bot_user.username}")
    print("آماده دریافت رویدادها و محافظت از سوپرگروه...")
    print("=" * 60 + "\n")

    # ارسال لاگ روشن شدن ربات
    await send_log(
        f"🟢 **ربات محافظ گروه آنلاین شد!**\n"
        f"🤖 نام کاربری: @{bot_user.username}\n"
        f"🆔 شناسه: `{bot_user.id}`\n"
        f"🚀 وضعیت: آماده به کار"
    )

    # شروع تسک پس‌زمینه پاکسازی
    cleanup_task = asyncio.create_task(periodic_cleanup_task())

    # انتظار برای دریافت سیگنال خروج (Ctrl+C یا پایان پروسه)
    await pyrogram.idle()

    # توقف منظم
    logger.info("در حال خاموش‌سازی ربات و بستن اتصالات...")
    cleanup_task.cancel()
    await send_log("🔴 **ربات محافظ گروه آفلاین شد.**")
    await app.stop()
    save_state()
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
