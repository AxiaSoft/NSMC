# 📦 راهنمای نصب و راه‌اندازی (پایتون ۳.۹ تا ۳.۱۴)

این ربات روی **پایتون ۳.۹ تا ۳.۱۴** در ویندوز، لینوکس، macOS و ترموکس (اندروید) اجرا می‌شود.
از نسخه ۴.۱.۰ به بعد، فایل `requirements.txt` خودش کتابخانه درست را بر اساس نسخه پایتون شما
انتخاب می‌کند (با environment markers)، بنابراین در اکثر موارد فقط یک دستور لازم دارید.

---

## ۰) پیش‌نیاز مشترک

```powershell
python -m pip install --upgrade pip
```

> در ویندوز اگر چند پایتون نصب است، به جای `python` مسیر کامل مفسر را بنویسید، مثلاً:
> `C:\Python314\python.exe`

---

## ۱) 🪟 ویندوز + پایتون ۳.۱۴ (حالت پیشنهادی و تست‌شده)

```powershell
# ۱. حذف نسخه قدیمی/تداخلی Pyrogram (اگر قبلاً نصب شده)
C:\Python314\python.exe -m pip uninstall -y pyrogram Pyrogram

# ۲. نصب خودکار وابستگی‌ها (kurigram + tgcrypto2 انتخاب می‌شوند)
cd D:\Security
C:\Python314\python.exe -m pip install -r requirements.txt

# ۳. بررسی نصب
C:\Python314\python.exe -c "import sys, pyrogram; print(sys.version.split()[0], pyrogram.__version__)"

# ۴. اجرای ربات
C:\Python314\python.exe bot.py
```

خروجی مرحله ۳ باید چیزی شبیه این باشد: `3.14.0 2.2.27`

---

## ۲) 🪟 ویندوز + پایتون ۳.۱۰ / ۳.۱۱

```powershell
cd D:\Security
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r requirements.txt
py -3.11 bot.py
```

در این حالت `Pyrogram==2.0.106` و `TgCrypto==1.2.5` نصب می‌شوند (wheel آماده دارند).

---

## ۳) 🤖 ترموکس (اندروید)

```bash
pkg update -y && pkg install -y python clang libjpeg-turbo zlib openssl
cd ~/Security
pip install --upgrade pip
pip install -r requirements.txt
python bot.py
```

> اگر نصب `TgCrypto`/`tgcrypto2` به دلیل نبود کامپایلر شکست خورد، **ربات بدون آن هم کار می‌کند**؛
> فقط کتابخانه اصلی را نصب کنید:
> `pip install "Pyrogram==2.0.106"` (پایتون ≤ ۳.۱۱) یا `pip install kurigram` (پایتون ≥ ۳.۱۲)

---

## ۴) 🐧 لینوکس / 🍎 macOS

```bash
cd ~/Security
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python bot.py
```

---

## ۵) نصب کتابخانه‌ها به‌صورت جداگانه (بدون requirements.txt)

| کتابخانه | نقش | دستور نصب |
| --- | --- | --- |
| `Pyrogram==2.0.106` | کتابخانه اصلی تلگرام — فقط پایتون ۳.۹ تا ۳.۱۱ | `python -m pip install Pyrogram==2.0.106` |
| `kurigram>=2.2.27` | فورک به‌روز Pyrogram — پایتون ۳.۱۲ / ۳.۱۳ / ۳.۱۴ | `python -m pip install kurigram` |
| `TgCrypto==1.2.5` | شتاب رمزنگاری — فقط پایتون ≤ ۳.۱۱ (wheel آماده) | `python -m pip install TgCrypto==1.2.5` |
| `tgcrypto2>=1.3.6` | شتاب رمزنگاری — پایتون ≥ ۳.۱۲ (wheel تا cp314، شامل ویندوز) | `python -m pip install tgcrypto2` |
| `pyrofork` | جایگزین اختیاری (توصیه نمی‌شود؛ در پایتون ۳.۱۴ هنوز `asyncio.get_event_loop()` خام صدا می‌زند) | `python -m pip install pyrofork` |

وابستگی‌های غیرمستقیم که pip خودش نصب می‌کند: `pyaes==1.6.1` و `pysocks==1.7.1`.

> ⚠️ **هرگز `Pyrogram` و `kurigram` را هم‌زمان نصب نکنید.** هر دو پوشه‌ای به نام `pyrogram`
> در `site-packages` می‌سازند و نصب هم‌زمان، فایل‌ها را خراب می‌کند. پیش از نصب فورک:
> `python -m pip uninstall -y pyrogram`
> ربات در لحظه شروع کار این تداخل را تشخیص می‌دهد و دستور اصلاح را در پیوی شما نمایش می‌دهد.

---

## ۶) عیب‌یابی

| خطا / نشانه | علت | راه‌حل |
| --- | --- | --- |
| `RuntimeError: There is no current event loop in thread 'MainThread'` | Pyrogram رسمی روی پایتون ۳.۱۲+ | ربات از نسخه ۴.۱.۰ یک شیم داخلی دارد؛ با این حال توصیه می‌شود `kurigram` نصب کنید |
| `TgCrypto is missing! Pyrogram will work the same, but at a much slower speed` | شتاب‌دهنده رمزنگاری نصب نیست | پایتون ≥ ۳.۱۲: `pip install tgcrypto2` — پایتون ≤ ۳.۱۱: `pip install TgCrypto==1.2.5` |
| `Microsoft Visual C++ 14.0 or greater is required` | `TgCrypto` روی پایتون ≥ ۳.۱۲ wheel ندارد | به جای آن `pip install tgcrypto2` (wheel آماده cp314 دارد) یا کلاً نصب نکنید |
| `ChatPermissions.__init__() got an unexpected keyword argument` | تفاوت امضای مجوزها بین نسخه‌ها | ربات از تابع `unrestricted_chat_permissions()` استفاده می‌کند که هر دو امضا را امتحان می‌کند — فایل `bot.py` را به‌روز بگیرید |
| `edit_text() got an unexpected keyword argument 'disable_web_page_preview'` | kurigram این پارامتر را حذف کرده | لایه سازگاری ربات آن را خودکار به `link_preview_options` تبدیل می‌کند — فایل `bot.py` را به‌روز بگیرید |
| رفتار عجیب پس از نصب چند کتابخانه | نصب تداخلی Pyrogram + kurigram | `pip uninstall -y pyrogram kurigram pyrofork` و سپس نصب فقط یکی |

### بررسی سلامت محیط از داخل ربات

در پیوی ربات یکی از این دستورهای متنی را بفرستید:

```
/compat      /سازگاری      /پایتون      /نصب
```

گزارش کامل شامل نسخه پایتون، کتابخانه فعال، وضعیت شتاب رمزنگاری، هشدارهای سازگاری
و دستورهای نصب آماده‌کپی نمایش داده می‌شود. همین اطلاعات در منوی
«ℹ️ وضعیت سیستم ← 🧩 سازگاری پایتون و کتابخانه» هم در دسترس است و در لحظه روشن شدن ربات
به پیوی اونر ارسال می‌شود.
