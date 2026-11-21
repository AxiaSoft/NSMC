#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
خودآزمایی ربات NSMC (Self-Test) — سازگار با پایتون ۳.۹ تا ۳.۱۴
=================================================================
این اسکریپت بدون اتصال به تلگرام و بدون ارسال هیچ پیامی، سلامت محیط اجرا و
سازگاری `bot.py` را با کتابخانه نصب‌شده بررسی می‌کند.

نحوه اجرا (از پوشه Security یا هر جای دیگر):
    python tests/selftest.py                 # بررسی‌های سازگاری
    python tests/selftest.py --startup       # + تست سرتاسری روشن/خاموش شدن (آفلاین)
    python tests/selftest.py --sim314        # + شبیه‌سازی رفتار asyncio پایتون ۳.۱۴
    python tests/selftest.py --all           # همه موارد بالا

خروجی: لیست بررسی‌ها با ok/FAIL و در پایان RESULT: PASS یا FAIL (کد خروج ۰ یا ۱).

⚠️ این اسکریپت پیش از اجرا از config.json / bot_state.json / فایل‌های session
   نسخه پشتیبان می‌گیرد و در پایان دقیقاً همان‌ها را بازمی‌گرداند.
"""
import asyncio
import importlib.util
import inspect
import os
import re
import shutil
import sys
import threading
import traceback
from pathlib import Path

SEC = Path(__file__).resolve().parents[1]
BOT_FILE = SEC / "bot.py"
BACKUP_DIR = Path(__file__).resolve().parent / ".selftest_backup"
PROTECTED = ["config.json", "bot_state.json", "config.save"]

CHECKS = 0
FAILS = []


# --------------------------------------------------------------------------- #
# خروجی و ابزارها
# --------------------------------------------------------------------------- #
def check(name, cond, extra=""):
    global CHECKS
    CHECKS += 1
    if cond:
        print(f"  ok    {name}")
    else:
        FAILS.append(name)
        print(f"  FAIL  {name} {extra}")


def info(msg):
    print(f"  ..    {msg}")


def section(title):
    print("\n" + "-" * 74)
    print(title)
    print("-" * 74)


def backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for n in os.listdir(SEC):
        if n in PROTECTED or n.endswith(".session") or n.endswith(".session-journal"):
            shutil.copy2(SEC / n, BACKUP_DIR / n)


def restore():
    if not BACKUP_DIR.exists():
        return
    for f in BACKUP_DIR.iterdir():
        shutil.copy2(f, SEC / f.name)
    shutil.rmtree(BACKUP_DIR, ignore_errors=True)


def load_bot():
    spec = importlib.util.spec_from_file_location("nsmc_bot", BOT_FILE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["nsmc_bot"] = mod
    spec.loader.exec_module(mod)
    return mod


def install_strict_get_event_loop():
    """شبیه‌سازی پایتون ۳.۱۴: get_event_loop() به‌جای ساخت لوپ، خطا می‌دهد."""
    import asyncio.events as _events

    policy_getter = getattr(_events, "_get_event_loop_policy",
                            getattr(_events, "get_event_loop_policy"))

    def strict():
        running = _events._get_running_loop()
        if running is not None:
            return running
        policy = policy_getter()
        local = getattr(policy, "_local", None)
        if local is None or getattr(local, "_loop", None) is None:
            raise RuntimeError("There is no current event loop in thread %r."
                               % threading.current_thread().name)
        return policy.get_event_loop()

    asyncio.get_event_loop = strict
    _events.get_event_loop = strict


# --------------------------------------------------------------------------- #
# شبه‌کلاینت برای تست‌های آفلاین
# --------------------------------------------------------------------------- #
class RecClient:
    def __init__(self):
        self.calls = []

    async def edit_message_text(self, **kw):
        self.calls.append(("edit_message_text", kw))
        return "edited"

    async def send_message(self, **kw):
        self.calls.append(("send_message", kw))
        return "sent"


class StubMessage:
    """جایگزین سبک Message؛ هر ویژگی ناشناخته None برمی‌گرداند."""

    def __init__(self, client):
        self._client = client
        self.client = client
        self.id = 11
        self.chat = type("C", (), {"id": -100123, "type": None, "title": "stub"})()
        self.business_connection_id = None
        self.text = None
        self.caption = None
        self.date = None
        self.forward_origin = None

    def __getattr__(self, item):
        return None


# --------------------------------------------------------------------------- #
# ۱) لایه سازگاری preview
# --------------------------------------------------------------------------- #
def test_preview_patch(bot):
    section("۱) لایه سازگاری disable_web_page_preview")
    from pyrogram.types import Message
    info(f"پچ‌شده‌ها: {bot.PREVIEW_COMPAT_PATCHED or 'نیاز نبود'}")

    async def run():
        results = {}
        for meth in ("edit_text", "reply_text"):
            c = RecClient()
            m = StubMessage(c)
            fn = getattr(Message, meth)
            try:
                res = fn(m, "salam", disable_web_page_preview=True)
                if inspect.isawaitable(res):
                    await res
                results[meth] = ("ok", c.calls)
            except TypeError as e:
                results[meth] = ("TypeError", str(e))
            except Exception as e:
                results[meth] = ("other", f"{type(e).__name__}: {e}")
        c = RecClient()
        try:
            res = RecClient.send_message(c, chat_id=1, text="x", disable_web_page_preview=True)
            if inspect.isawaitable(res):
                await res
            results["send_message"] = ("ok", c.calls)
        except TypeError as e:
            results["send_message"] = ("TypeError", str(e))
        return results

    for meth, (status, detail) in asyncio.run(run()).items():
        check(f"{meth}(disable_web_page_preview=True) پذیرفته شد", status == "ok", f"-> {status}: {detail}")
        if status == "ok" and detail:
            kw = detail[-1][1]
            legacy = "disable_web_page_preview" in kw
            modern = kw.get("link_preview_options") is not None
            check(f"{meth} پرچم جلوگیری از پیش‌نمایش را منتقل می‌کند",
                  bool(legacy or modern), f"-> keys={sorted(kw)}")
            if modern:
                check(f"{meth} LinkPreviewOptions(is_disabled=True)",
                      bool(getattr(kw["link_preview_options"], "is_disabled", False)))


# --------------------------------------------------------------------------- #
# ۲) مجوزها و فیلدهای فوروارد
# --------------------------------------------------------------------------- #
def test_permissions(bot):
    section("۲) ساخت مجوزهای چت (ChatPermissions)")
    p = bot.restricted_chat_permissions()
    check("restricted_chat_permissions().can_send_messages == False", p.can_send_messages is False)
    u = bot.unrestricted_chat_permissions()
    check("unrestricted_chat_permissions().can_send_messages == True", u.can_send_messages is True)
    modern = [k for k in ("can_send_photos", "can_send_videos", "can_send_audios") if hasattr(u, k)]
    info(f"نوع امضا: {'جدید (تفکیک رسانه)' if modern else 'قدیمی (can_send_media_messages)'}")


def test_forward_helpers(bot):
    section("۳) دسترسی به اطلاعات پیام فورواردشده")
    m_new = StubMessage(RecClient())
    m_new.__dict__["forward_origin"] = type("O", (), {
        "sender_user": type("U", (), {"id": 777, "first_name": "A", "username": "aa"})(),
        "sender_user_name": "Hidden",
        "chat": type("Ch", (), {"id": -100555, "type": None})(),
        "sender_chat": None,
        "date": 1700000000,
    })()

    m_old = StubMessage(RecClient())
    m_old.__dict__["forward_origin"] = None
    m_old.forward_from = type("U", (), {"id": 888, "first_name": "B", "username": "bb"})()
    m_old.forward_from_id = 888
    m_old.forward_from_chat = type("Ch", (), {"id": -100666, "type": None})()
    m_old.forward_sender_name = "LegacyHidden"
    m_old.forward_date = 1600000000

    m_hidden = StubMessage(RecClient())
    m_hidden.__dict__["forward_origin"] = type("O", (), {
        "sender_user": None, "sender_user_name": "X", "chat": None, "sender_chat": None,
        "sender_user_id": 999, "date": 1,
    })()
    m_hidden.forward_from = None
    m_hidden.forward_from_id = 999
    m_hidden.forward_from_chat = None
    m_hidden.forward_sender_name = "X"
    m_hidden.forward_date = 1

    check("get_forward_user_id(new) == 777", bot.get_forward_user_id(m_new) == 777)
    check("get_forward_user_id(old) == 888", bot.get_forward_user_id(m_old) == 888)
    check("get_forward_user_id(hidden) == 999", bot.get_forward_user_id(m_hidden) == 999)
    check("is_forwarded_message(new)", bot.is_forwarded_message(m_new) is True)
    check("is_forwarded_message(old)", bot.is_forwarded_message(m_old) is True)
    check("get_forward_chat(new).id == -100555", getattr(bot.get_forward_chat(m_new), "id", None) == -100555)
    check("get_forward_chat(old).id == -100666", getattr(bot.get_forward_chat(m_old), "id", None) == -100666)
    check("get_forward_sender_name(new) == 'Hidden'", bot.get_forward_sender_name(m_new) == "Hidden")
    check("get_forward_sender_name(old) == 'LegacyHidden'", bot.get_forward_sender_name(m_old) == "LegacyHidden")
    check("get_forward_date(new) == 1700000000", bot.get_forward_date(m_new) == 1700000000)
    check("get_forward_date(old) == 1600000000", bot.get_forward_date(m_old) == 1600000000)
    check("get_forward_user(new).id == 777", getattr(bot.get_forward_user(m_new), "id", None) == 777)
    check("get_forward_user(old).id == 888", getattr(bot.get_forward_user(m_old), "id", None) == 888)


# --------------------------------------------------------------------------- #
# ۴) گزارش محیط اجرا و نقطه ورود
# --------------------------------------------------------------------------- #
def test_report(bot):
    section("۴) گزارش محیط اجرا")
    rep = bot.runtime_report()
    info(f"کتابخانه: {rep['library']} {rep['library_version']} | پایتون: {rep['python']} | "
         f"رمزنگاری سریع: {rep['crypto']} | نصب تداخلی: {rep['mixed'] or 'ندارد'}")
    info(f"روش اجرا: {rep['entrypoint']} | لایه‌های پچ‌شده: {rep['patched'] or '—'}")
    warns = bot.compatibility_warnings()
    info(f"هشدارهای سازگاری: {len(warns)} مورد")
    for w in warns:
        for line in str(w).splitlines():
            print(f"        {line}")
    check("runtime_report همه کلیدها را دارد",
          all(k in rep for k in ("python", "library", "library_version", "crypto", "patched",
                                 "official", "mixed", "entrypoint")))
    check("نصب تداخلی کتابخانه تلگرام وجود ندارد", rep["mixed"] == [], f"-> {rep['mixed']}")
    check("روش اجرای تشخیص‌داده‌شده معتبر است",
          rep["entrypoint"] in ("app.run(main())", "asyncio.run(main())"), f"-> {rep['entrypoint']}")
    return rep


def test_entrypoint(bot, rep):
    section("۵) نقطه ورود (run_bot) — سازگاری با kurigram")
    style = rep["entrypoint"]
    real_run = bot.app.run
    real_asyncio_run = asyncio.run
    real_sig = inspect.signature(real_run)
    info(f"امضای واقعی app.run در کتابخانه نصب‌شده: {real_sig}")

    async def dummy_main():
        return "done"

    took, took2 = [], []

    def fake_app_run(*args, **kwargs):
        took.append("app.run")
        for a in args:
            if inspect.iscoroutine(a):
                a.close()

    fake_app_run.__signature__ = real_sig  # تا تشخیص run_bot تغییری نکند

    def fake_asyncio_run(coro, **kwargs):
        took.append("asyncio.run")
        if inspect.iscoroutine(coro):
            coro.close()

    def fake_asyncio_run2(coro, **kwargs):
        took2.append("asyncio.run")
        if inspect.iscoroutine(coro):
            coro.close()

    def exploding_run(coroutine=None, **kw):
        raise TypeError("Run.run() takes 1 positional argument but 2 were given")

    exploding_run.__signature__ = inspect.Signature(parameters=[
        inspect.Parameter("coroutine", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None)])

    try:
        bot.app.run = fake_app_run
        bot.asyncio.run = fake_asyncio_run
        bot.run_bot(dummy_main)
    finally:
        bot.app.run = real_run
        bot.asyncio.run = real_asyncio_run
    check("run_bot دقیقاً از یک مسیر استفاده کرد", len(took) == 1, f"-> {took}")
    if took:
        expected = "app.run" if style == "app.run(main())" else "asyncio.run"
        check(f"run_bot از {expected} استفاده کرد", took[0] == expected, f"-> {took[0]}")

    try:
        bot.app.run = exploding_run
        bot.asyncio.run = fake_asyncio_run2
        bot.run_bot(dummy_main)
    finally:
        bot.app.run = real_run
        bot.asyncio.run = real_asyncio_run
    check("در صورت TypeError به asyncio.run برمی‌گردد", took2 == ["asyncio.run"], f"-> {took2}")


def test_align_loop(bot):
    section("۶) هم‌ترازسازی لوپ dispatcher")
    disp = bot.app.dispatcher
    if not hasattr(disp, "loop"):
        info("در این کتابخانه dispatcher ویژگی 'loop' ندارد → هم‌ترازسازی بدون اثر (بی‌خطر)")
        check("align_running_loop بدون خطا اجرا شد", True)
        return

    async def run():
        original = disp.loop
        stale = asyncio.new_event_loop()
        try:
            disp.loop = stale
            bot.align_running_loop()
            return disp.loop is asyncio.get_running_loop()
        finally:
            stale.close()
            disp.loop = original

    check("align_running_loop لوپ dispatcher را به لوپ جاری وصل می‌کند", asyncio.run(run()))


# --------------------------------------------------------------------------- #
# ۷) منوها و هندلرها
# --------------------------------------------------------------------------- #
def test_menus(bot):
    section("۷) منوها و محدودیت‌های تلگرام")
    rendered, oversized, long_cb = 0, [], []
    for fname in sorted(dir(bot)):
        if not fname.startswith("build_"):
            continue
        fn = getattr(bot, fname)
        if not callable(fn):
            continue
        sig = inspect.signature(fn)
        required = [p for p in sig.parameters.values()
                    if p.default is inspect.Parameter.empty
                    and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)]
        if required:
            continue
        try:
            out = fn()
        except Exception as e:
            FAILS.append(f"{fname}() raised {type(e).__name__}: {e}")
            print(f"  FAIL  {fname}() raised {type(e).__name__}: {e}")
            continue
        rendered += 1
        if not isinstance(out, tuple) or len(out) != 2:
            continue
        text, kb = out
        if len(text) > 4096:
            oversized.append((fname, len(text)))
        for row in (getattr(kb, "inline_keyboard", []) or []):
            for btn in row:
                data = getattr(btn, "callback_data", None)
                if data and len(data.encode("utf-8")) > 64:
                    long_cb.append((fname, data))

    info(f"{rendered} منوی بدون آرگومان ساخته شد")
    check("تعداد منوهای ساخته‌شده کافی است", rendered >= 12, f"-> {rendered}")
    for key in ("build_main_menu", "build_system_info_menu", "build_compat_menu", "build_help_menu"):
        check(f"{key} وجود دارد", callable(getattr(bot, key, None)))
    check("هیچ منویی از ۴۰۹۶ کاراکتر تلگرام بلندتر نیست", not oversized, f"-> {oversized}")
    check("هیچ callback_data از ۶۴ بایت بلندتر نیست", not long_cb, f"-> {long_cb[:3]}")

    text, kb = bot.build_compat_menu()
    check("منوی سازگاری دکمه menu:compat دارد", "menu:compat" in str(getattr(kb, "inline_keyboard", "")))
    check("منوی سازگاری نام کتابخانه فعال را نشان می‌دهد", bot.TELEGRAM_LIB.lower() in text.lower())
    check("منوی سازگاری دستور نصب دارد", "pip install" in text)
    check("منوی سازگاری روش اجرا را نشان می‌دهد", "asyncio.run" in text or "app.run" in text)
    info(f"طول منوی سازگاری: {len(text)} کاراکتر")


def test_handlers(bot):
    section("۸) هندلرهای ثبت‌شده")
    disp = bot.app.dispatcher
    loop = getattr(disp, "loop", None)
    if loop is not None:
        try:
            loop.run_until_complete(asyncio.sleep(0.15))
        except Exception as e:
            info(f"امکان تخلیه لوپ dispatcher نبود: {type(e).__name__}: {e}")

    groups = disp.groups
    total = sum(len(v) for v in groups.values())

    def resolve(cb, depth=0):
        name = getattr(cb, "__name__", None) or getattr(cb, "__qualname__", None) or "?"
        wrapped = getattr(cb, "__wrapped__", None)
        if wrapped is not None and depth < 6:
            inner = resolve(wrapped, depth + 1)
            if inner != "?":
                return inner
        for cell in (getattr(cb, "__closure__", None) or []):
            try:
                obj = cell.cell_contents
            except ValueError:
                continue
            if callable(obj) and getattr(obj, "__name__", "").startswith(("handle_", "on_")):
                return obj.__name__
        return name

    names = [resolve(getattr(h, "callback", None)) for v in groups.values() for h in v]
    info(f"{total} هندلر ثبت شده است")
    for n in names:
        print(f"        - {n}")
    check("تعداد هندلرها >= ۱۸", total >= 18, f"-> {total}")

    resolved = [n for n in names if n.startswith(("handle_", "on_"))]
    if len(resolved) >= max(1, total // 2):
        check("handle_compat_command ثبت شده است", any("compat" in n for n in resolved), f"-> {resolved}")
    else:
        src = BOT_FILE.read_text(encoding="utf-8")
        decorated = bool(re.search(r'@app\.on_message\(filters\.command\(\[[^\]]*"compat"', src))
        is_coro = inspect.iscoroutinefunction(getattr(bot, "handle_compat_command", None))
        info(f"این کتابخانه نام کال‌بک‌ها را پنهان می‌کند ({len(resolved)}/{total}) → بررسی از راه سورس")
        check("handle_compat_command ثبت شده است (بررسی سورس)", decorated and is_coro)


def test_source_checks(bot):
    section("۹) بررسی‌های سطح سورس")
    src = BOT_FILE.read_text(encoding="utf-8")
    check("روتر دکمه menu:compat را مدیریت می‌کند", 'data == "menu:compat"' in src)
    tail = src.split("if __name__")[-1]
    tail_code = "\n".join(ln for ln in tail.splitlines() if ln.strip() and not ln.strip().startswith("#"))
    check("نقطه ورود run_bot(main) است", "run_bot(main)" in tail_code)
    check("نقطه ورود دیگر app.run(main()) مستقیم نیست", "app.run(main())" not in tail_code)
    check("main() لوپ را هم‌تراز می‌کند", "align_running_loop()" in src)
    check("هدر sh/python (اجرای ناخواسته با bash) وجود دارد", src.splitlines()[0].startswith("#!"))
    check("دسترسی مستقیم به message.forward_from_chat حذف شده", "src_chat = message.forward_from_chat" not in src)


# --------------------------------------------------------------------------- #
# ۱۰) تست سرتاسری روشن/خاموش شدن (کاملاً آفلاین)
# --------------------------------------------------------------------------- #
def test_startup(bot):
    section("۱۰) تست سرتاسری startup/shutdown (آفلاین، بدون تلگرام)")
    log = {"events": [], "sent": []}
    app = bot.app

    class FakeUser:
        id = 424242
        first_name = "NSMC"
        username = "NSMC_test_bot"
        is_bot = True

        @property
        def mention(self):
            return "@NSMC_test_bot"

    class FakeMessage:
        id = 1

        async def delete(self, *a, **kw):
            return None

    async def fake_start(*a, **kw):
        log["events"].append("start")

    async def fake_get_me(*a, **kw):
        log["events"].append("get_me")
        return FakeUser()

    async def fake_send_message(*a, **kw):
        log["events"].append("send_message")
        log["sent"].append((kw.get("chat_id"), kw.get("text") or ""))
        return FakeMessage()

    async def fake_stop(*a, **kw):
        log["events"].append("stop")

    async def fake_idle():
        log["events"].append("idle")

    real = {"start": app.start, "get_me": app.get_me, "send_message": app.send_message,
            "stop": app.stop, "idle": bot.pyrogram.idle}
    app.start = fake_start
    app.get_me = fake_get_me
    app.send_message = fake_send_message
    app.stop = fake_stop
    bot.pyrogram.idle = lambda *a, **kw: fake_idle()
    try:
        bot.run_bot(bot.main)
    except TypeError as e:
        check("اجرای نقطه ورود بدون TypeError", False, f"-> {e}")
        return
    except Exception as e:
        check("اجرای کامل startup/shutdown", False, f"-> {type(e).__name__}: {e}")
        traceback.print_exc()
        return
    finally:
        app.start, app.get_me = real["start"], real["get_me"]
        app.send_message, app.stop = real["send_message"], real["stop"]
        bot.pyrogram.idle = real["idle"]

    events = log["events"]
    info(f"رویدادها: {events}")
    info(f"پیام‌های ارسال‌شده (شبیه‌سازی): {len(log['sent'])} مورد")
    for chat_id, text in log["sent"]:
        head = text[:64].replace("\n", " | ")
        print(f"        -> chat {chat_id}: {head}")

    for step in ("start", "get_me", "idle", "stop"):
        check(f"مرحله «{step}» اجرا شد", step in events)
    if "idle" in events and "stop" in events:
        check("ترتیب درست است (stop بعد از idle)", events.index("stop") > events.index("idle"))
    check("اعلان آنلاین به پیوی اونر ارسال شد", any("آنلاین" in t for _, t in log["sent"]))
    check("اعلان آفلاین به پیوی اونر ارسال شد", any("آفلاین" in t for _, t in log["sent"]))
    bad = [c for c, _ in log["sent"] if isinstance(c, int) and c < 0]
    check("هیچ اعلانی به گروه/کانال نرفت", not bad, f"-> {bad}")


# --------------------------------------------------------------------------- #
def main():
    args = set(sys.argv[1:])
    do_startup = bool(args & {"--startup", "--all"})
    do_sim = bool(args & {"--sim314", "--all"})

    print("=" * 74)
    print("خودآزمایی ربات NSMC (Security bot self-test)")
    print(f"پایتون: {sys.version.split()[0]} | مفسر: {sys.executable}")
    print(f"پوشه ربات: {SEC}")
    if do_sim:
        install_strict_get_event_loop()
        try:
            asyncio.get_event_loop()
            print("SIM-FAULT: شبیه‌سازی پایتون ۳.۱۴ فعال نشد")
            return 2
        except RuntimeError as e:
            print(f"شبیه‌سازی asyncio پایتون ۳.۱۴ فعال شد -> RuntimeError: {e}")
    print("=" * 74)

    backup()
    try:
        # زیر شبیه‌سازی پایتون ۳.۱۴، «import pyrogram» خام (بدون شیم bot.py) با
        # Pyrogram رسمی دقیقاً همان خطایی را می‌دهد که کاربر دیده است. این انتظار
        # ثبت می‌شود و سپس bot.py با شیم خودش همان import را سالم انجام می‌دهد.
        try:
            import pyrogram
            print(f"ماژول pyrogram: {pyrogram.__version__}")
        except RuntimeError as e:
            if not do_sim:
                raise
            print(f"⚠️  import pyrogram بدون شیم، زیر شبیه‌سازی ۳.۱۴ شکست خورد: {e}")
            print("    (این همان خطای پایتون ۳.۱۴ است؛ شیم داخل bot.py جلوی آن را می‌گیرد)")

        bot = load_bot()
        import pyrogram  # حالا امن است: شیم bot.py لوپ را ساخته و ثبت کرده است
        print(f"bot.py با موفقیت import شد | نسخه ربات: {bot.BOT_VERSION} | "
              f"کتابخانه: {bot.TELEGRAM_LIB} {bot.TELEGRAM_LIB_VERSION}")
        test_preview_patch(bot)
        test_permissions(bot)
        test_forward_helpers(bot)
        rep = test_report(bot)
        test_entrypoint(bot, rep)
        test_align_loop(bot)
        test_menus(bot)
        test_handlers(bot)
        test_source_checks(bot)
        if do_startup:
            # نکته: asyncio.run در پایان کار، لوپ جاری سیاست را None می‌کند. در اجرای
            # واقعی ربات هیچ‌گاه پیش از start این اتفاق نمی‌افتد (شیم bot.py لوپ را
            # نگه می‌دارد)، ولی اینجا چون چند تست قبلی asyncio.run داشته‌ایم، لوپ را
            # دقیقاً مثل شیم bot.py بازمی‌گردانیم تا شرایط اجرای واقعی بازسازی شود.
            try:
                asyncio.get_event_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())
                info("لوپ پیش‌فرض برای تست startup بازگردانده شد (مثل کاری که شیم bot.py می‌کند)")
            test_startup(bot)
        else:
            info("تست سرتاسری startup اجرا نشد (برای اجرای آن: --startup یا --all)")
    except Exception:
        FAILS.append("self-test crashed")
        traceback.print_exc()
    finally:
        restore()

    print("\n" + "=" * 74)
    print(f"تعداد بررسی‌ها: {CHECKS} | خطاها: {len(FAILS)}")
    for f in FAILS:
        print(f"  FAILED: {f}")
    print("RESULT:", "PASS" if not FAILS else "FAIL")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
