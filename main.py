import os
import asyncio
import logging
from typing import Dict, List
import aiohttp
from dotenv import load_dotenv
from pyrogram import Client, filters, enums
from pyrogram.types import Message

# ─────────────────────────────────────────────────────────────
# 1. SOZLAMALAR VA KONFIGURATSIYA (.env dan yuklash)
# ─────────────────────────────────────────────────────────────
load_dotenv()

API_ID = int(os.getenv("API_ID", "0").strip())
API_HASH = os.getenv("API_HASH", "").strip()
SESSION_NAME = os.getenv("SESSION_NAME", "my_userbot").strip()
SESSION_STRING = os.getenv("SESSION_STRING", "").strip()

# AI Tanlovi: "gemini" yoki "openai"
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower()

# Gemini sozlamalari (Bepul kalit: https://aistudio.google.com/)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

# OpenAI sozlamalari (https://platform.openai.com/)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

# Shaxsiy xabarlarga avtomatik javob berish (True / False)
AUTO_REPLY_ENABLED = os.getenv("AUTO_REPLY_ENABLED", "True").lower() in ("true", "1", "yes")

# AI uchun umumiy yo'riqnoma (System prompt)
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Siz Telegram foydalanuvchisi nomidan javob beruvchi aqlli va xushmuomala sun'iy intellektsiz. "
    "Muloqotni samimiy, lo'nda va tabiiy insondek olib boring. O'zbek tilida javob bering."
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s"
)
logger = logging.getLogger(__name__)

# Suhbatlar xotirasi (Chat ID -> [{"role": "user"|"model", "text": "..."}])
chat_histories: Dict[int, List[dict]] = {}
MAX_HISTORY_LENGTH = 10  # Oxirgi 10 ta xabarni eslab qoladi

# ─────────────────────────────────────────────────────────────
# 2. SUN'IY INTELLEKT (AI) BILAN ISHLASH FUNKSIYALARI
# ─────────────────────────────────────────────────────────────

async def query_gemini(prompt: str, history: List[dict] = None) -> str:
    """Google Gemini API ga so'rov yuborish (aiohttp orqali to'liq asinxron)."""
    if not GEMINI_API_KEY:
        return "❌ Xatolik: GEMINI_API_KEY o'rnatilmagan! .env faylini tekshiring."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    # Gemini formati bo'yicha suhbat tarixi
    contents = []
    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["text"]}]
            })
    # Joriy yangi xabar
    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048
        }
    }

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    err_data = await response.json()
                    err_msg = err_data.get("error", {}).get("message", "Noma'lum xatolik")
                    logger.error(f"Gemini API xatosi ({response.status}): {err_msg}")
                    return f"❌ Gemini API xatosi: {err_msg}"

                result = await response.json()
                candidates = result.get("candidates", [])
                if not candidates:
                    return "Javob olib bo'lmadi (bloklangan yoki bo'sh)."

                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
                return "Bo'sh javob qaytdi."
    except asyncio.TimeoutError:
        return "⏱ Gemini serveri javob berishda kechikdi (Timeout)."
    except Exception as e:
        logger.error(f"Gemini so'rovida kutilmagan xatolik: {e}")
        return f"❌ AI xatosi: {e}"


async def query_openai(prompt: str, history: List[dict] = None) -> str:
    """OpenAI API ga so'rov yuborish (aiohttp orqali to'liq asinxron)."""
    if not OPENAI_API_KEY:
        return "❌ Xatolik: OPENAI_API_KEY o'rnatilmagan! .env faylini tekshiring."

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["text"]})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.7
    }

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    err_data = await response.json()
                    err_msg = err_data.get("error", {}).get("message", "Noma'lum xatolik")
                    logger.error(f"OpenAI API xatosi ({response.status}): {err_msg}")
                    return f"❌ OpenAI API xatosi: {err_msg}"

                result = await response.json()
                choices = result.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
                return "Bo'sh javob qaytdi."
    except asyncio.TimeoutError:
        return "⏱ OpenAI serveri javob berishda kechikdi (Timeout)."
    except Exception as e:
        logger.error(f"OpenAI so'rovida kutilmagan xatolik: {e}")
        return f"❌ AI xatosi: {e}"


async def get_ai_response(chat_id: int, user_prompt: str) -> str:
    """Belgilangan AI provayderi (Gemini yoki OpenAI) orqali javob olish va xotirani saqlash."""
    # Chat tarixini olish
    history = chat_histories.get(chat_id, [])

    if AI_PROVIDER == "openai":
        reply = await query_openai(user_prompt, history)
    else:
        reply = await query_gemini(user_prompt, history)

    # Agar javob muvaffaqiyatli bo'lsa (xatolik bo'lmasa), tarixga qo'shamiz
    if not reply.startswith("❌") and not reply.startswith("⏱"):
        history.append({"role": "user", "text": user_prompt})
        history.append({"role": "model", "text": reply})
        if len(history) > MAX_HISTORY_LENGTH * 2:
            history = history[-(MAX_HISTORY_LENGTH * 2):]
        chat_histories[chat_id] = history

    return reply


async def send_chunked_message(client: Client, chat_id: int, text: str, reply_to_message_id: int = None):
    """Telegramning 4096 belgilik cheklovini aylanib o'tish uchun xabarni bo'lib yuborish."""
    MAX_CHUNK = 4000
    if len(text) <= MAX_CHUNK:
        await client.send_message(chat_id=chat_id, text=text, reply_to_message_id=reply_to_message_id)
        return

    # Uzun matnni bo'laklarga bo'lib yuborish
    chunks = [text[i:i + MAX_CHUNK] for i in range(0, len(text), MAX_CHUNK)]
    for chunk in chunks:
        try:
            await client.send_message(chat_id=chat_id, text=chunk, reply_to_message_id=reply_to_message_id)
        except Exception:
            await client.send_message(chat_id=chat_id, text=chunk, reply_to_message_id=reply_to_message_id, parse_mode=enums.ParseMode.DISABLED)
        reply_to_message_id = None  # Keyingi qismlarni reply qilmasdan ketma-ket yuborish


# ─────────────────────────────────────────────────────────────
# 3. PYROGRAM USERBOT MIJOZI VA HANDLERLAR
# ─────────────────────────────────────────────────────────────
app = Client(
    name=SESSION_NAME,
    session_string=SESSION_STRING if SESSION_STRING else None,
    api_id=API_ID,
    api_hash=API_HASH,
    device_model="Desktop",
    system_version="Windows 11",
    app_version="5.6.3 x64",
    lang_code="en"
)


# 1) AVTO-JAVOBNI BOSHQARISH BUYRUQLARI (Faqat userbot egasi yozganda ishlaydi)
@app.on_message(filters.me & filters.command("ai_on", prefixes=[".", "!", "/"]))
async def enable_auto_reply(client: Client, message: Message):
    global AUTO_REPLY_ENABLED
    AUTO_REPLY_ENABLED = True
    await message.edit_text("✅ **AI Avto-javob yoqildi!** Endi shaxsiy xabarlarga AI javob beradi.")


@app.on_message(filters.me & filters.command("ai_off", prefixes=[".", "!", "/"]))
async def disable_auto_reply(client: Client, message: Message):
    global AUTO_REPLY_ENABLED
    AUTO_REPLY_ENABLED = False
    await message.edit_text("⏸ **AI Avto-javob o'chirildi!**")


@app.on_message(filters.me & filters.command("ai_clear", prefixes=[".", "!", "/"]))
async def clear_history(client: Client, message: Message):
    chat_id = message.chat.id
    if chat_id in chat_histories:
        chat_histories[chat_id] = []
        await message.edit_text("🧹 Ushbu chatdagi AI xotirasi tozalandi.")
    else:
        await message.edit_text("ℹ️ Ushbu chat uchun xotira mavjud emas.")


@app.on_message(filters.me & filters.command("session", prefixes=[".", "!", "/"]))
async def export_session_cmd(client: Client, message: Message):
    try:
        s = await client.export_session_string()
        await message.reply_text(
            f"🔑 **Sizning SESSION_STRING (Koyeb / Cloud uchun):**\n\n`{s}`\n\n⚠️ *Diqqat: Ushbu kalitni hech kimga bermang!*"
        )
    except Exception as e:
        await message.reply_text(f"❌ Xatolik: {e}")


# 2) MANUAL SO'ROV BUYRUG'I (.ai <savol> yoki biror xabarga reply qilib .ai)
@app.on_message(filters.me & filters.command("ai", prefixes=[".", "!", "/"]))
@app.on_edited_message(filters.me & filters.command("ai", prefixes=[".", "!", "/"]))
async def manual_ai_command(client: Client, message: Message):
    prompt = ""
    # Agar buyruqdan keyin matn yozilgan bo'lsa
    if len(message.command) > 1:
        prompt = message.text.split(maxsplit=1)[1]
    # Agar biror xabarga javoban '.ai' yozilgan bo'lsa
    elif message.reply_to_message and message.reply_to_message.text:
        prompt = message.reply_to_message.text

    if not prompt:
        await message.edit_text("⚠️ Foydalanish: `.ai <savol>` yoki xabarga reply qilib `.ai` deb yozing.")
        return

    await message.edit_text(f"💭 *AI o'ylamoqda ({AI_PROVIDER.capitalize()})...*")
    await client.send_chat_action(chat_id=message.chat.id, action=enums.ChatAction.TYPING)

    response = await get_ai_response(message.chat.id, prompt)
    try:
        await message.edit_text(response)
    except Exception:
        try:
            await message.edit_text(response, parse_mode=enums.ParseMode.DISABLED)
        except Exception:
            await client.send_message(message.chat.id, response, parse_mode=enums.ParseMode.DISABLED)


# 3) KELGAN SHAXSIY XABARLARGA AVTOMATIK JAVOB BERISH
@app.on_message(filters.private & ~filters.me & ~filters.bot & filters.text)
async def incoming_private_message(client: Client, message: Message):
    # Agar avto-javob o'chirilgan bo'lsa, javob bermaymiz
    if not AUTO_REPLY_ENABLED:
        return

    user_text = message.text
    chat_id = message.chat.id

    logger.info(f"Yangi xabar keldi [{chat_id} - @{message.from_user.username or message.from_user.first_name}]: {user_text}")

    # Telegramda 'yozmoqda...' (typing) statusini yoqamiz
    await client.send_chat_action(chat_id=chat_id, action=enums.ChatAction.TYPING)

    # AI dan javob olish
    ai_reply = await get_ai_response(chat_id, user_text)

    # Javobni yuborish
    await send_chunked_message(client, chat_id=chat_id, text=ai_reply, reply_to_message_id=message.id)


async def run_web_healthcheck(port: int):
    """Hugging Face / Cloud uchun HTTP health-check server."""
    from aiohttp import web
    async def health(request):
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Telegram AI Userbot</title></head>
        <body style="font-family:sans-serif; text-align:center; padding:50px; background:#f4f7f6;">
            <h2>🤖 Telegram AI Userbot (Gemini 3.8 Flash)</h2>
            <p style="color:green; font-weight:bold; font-size:18px;">✅ Status: Active & Running 24/7</p>
        </body>
        </html>
        """
        return web.Response(text=html_content, content_type="text/html")

    web_app = web.Application()
    web_app.router.add_get("/", health)
    web_app.router.add_get("/health", health)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    try:
        await site.start()
        logger.info(f"🌐 Web Health-Check server port {port} da ishga tushdi.")
    except Exception as e:
        logger.warning(f"Web server ishga tushmadi: {e}")


async def start_all():
    port_env = os.getenv("PORT", "7860")
    if port_env and port_env.isdigit():
        await run_web_healthcheck(int(port_env))
    await app.start()
    logger.info("🚀 Userbot muvaffaqiyatli ishga tushdi!")
    from pyrogram import idle
    await idle()
    await app.stop()


# ─────────────────────────────────────────────────────────────
# 4. ISHGA TUSHIRISH
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not API_ID or not API_HASH:
        print("❌ XATOLIK: API_ID yoki API_HASH topilmadi! .env faylini to'ldiring.")
        exit(1)

    print("🚀 Pyrogram AI Userbot ishga tushirilmoqda...")
    print(f"🤖 Tanlangan AI provayderi: {AI_PROVIDER.upper()}")
    try:
        app.run(start_all())
    except errors.PhoneNumberInvalid:
        print("\n❌ XATOLIK: Telefon raqam noto'g'ri kiritildi!")
        print("💡 Maslahat: Telefon raqamingizni xalqaro formatda, probellarsiz kiriting. Masalan: +998901234567\n")
    except errors.ApiIdInvalid:
        print("\n❌ XATOLIK: API_ID yoki API_HASH noto'g'ri!")
        print("💡 Maslahat: https://my.telegram.org dagi API_ID va API_HASH qiymatlarini .env fayliga to'g'ri ko'chirganingizni tekshiring.\n")
    except errors.FloodWait as e:
        print(f"\n❌ XATOLIK: Telegram cheklov qo'ydi (FloodWait)! {e.value} soniya kutishingiz kerak.\n")
    except errors.PhoneNumberBanned:
        print("\n❌ XATOLIK: Bu telefon raqam Telegram tomonidan bloklangan (Banned)!\n")
    except Exception as e:
        print(f"\n❌ Xatolik yuz berdi: {e}\n")
