#!/usr/bin/env sh
# =============================================================================
#  اجراکننده ساده ربات NSMC (Termux / Linux / macOS)
#  استفاده:  bash run.sh
#  این اسکریپت مفسر درست پایتون را پیدا می‌کند، در صورت نیاز وابستگی‌ها را
#  نصب می‌کند و سپس ربات را با پایتون (نه bash) اجرا می‌کند.
# =============================================================================
cd "$(dirname "$0")" || exit 1

# --- پیدا کردن مفسر پایتون ---
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "❌ پایتون پیدا نشد."
    echo "   در ترموکس:  pkg update -y && pkg install -y python"
    exit 1
fi

echo "🐍 مفسر: $($PY -V 2>&1)  ($(command -v "$PY"))"

# --- نصب وابستگی‌ها در صورت نیاز ---
if ! "$PY" -c "import pyrogram" >/dev/null 2>&1; then
    echo "📦 کتابخانه تلگرام نصب نیست؛ در حال نصب وابستگی‌ها از requirements.txt ..."
    "$PY" -m pip install --upgrade pip || echo "⚠️  به‌روزرسانی pip ناموفق بود (ادامه می‌دهیم)"
    "$PY" -m pip install -r requirements.txt || {
        echo "❌ نصب وابستگی‌ها ناموفق بود."
        echo "   اگر خطای کامپایل TgCrypto دیدید، فقط کتابخانه اصلی را نصب کنید:"
        echo "     $PY -m pip install kurigram      (پایتون ۳.۱۲ به بالا)"
        echo "     $PY -m pip install Pyrogram==2.0.106   (پایتون ۳.۱۱ و پایین‌تر)"
        exit 1
    }
fi

"$PY" - <<'PYCHECK'
import sys
try:
    import pyrogram
    lib = "pyrogram"
    try:
        from importlib import metadata as m
        for name in ("kurigram", "pyrofork", "Pyrogram", "pyrogram"):
            try:
                lib = f"{name} {m.version(name)}"
                break
            except Exception:
                continue
    except Exception:
        pass
    print(f"📦 کتابخانه فعال: {lib} (ماژول pyrogram {pyrogram.__version__})")
except Exception as e:
    print(f"❌ بررسی کتابخانه ناموفق بود: {e}")
    sys.exit(1)
PYCHECK

echo "🚀 در حال اجرای ربات با پایتون ..."
echo "---------------------------------------------------------------------"
exec "$PY" bot.py "$@"
