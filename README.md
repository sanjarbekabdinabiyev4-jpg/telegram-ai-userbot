# Telegram AI Auto-Reply Userbot 🤖

Ushbu loyiha Pyrogram orqali Telegram profilingiz nomidan ishlaydigan va kelgan shaxsiy xabarlarga **Google Gemini API** (yoki OpenAI API) orqali aqlli avto-javob qaytaruvchi sun'iy intellekt Userbotidir.

## Xususiyatlari
- 🧠 **Google Gemini 3.8 Flash** integratsiyasi.
- 💬 **Suhbat xotirasi (Context Memory):** Oxirgi xabarlarni eslab qoladi.
- ⚡ **Avto-javob va buyruqlar:** `.ai <savol>`, `.ai_on`, `.ai_off`, `.session`.
- 🌐 **Koyeb / Render 24/7 moslashuvchanligi:** `SESSION_STRING` va avtomatik HTTP health check (Port 8000).

## Koyeb.com orqali 24/7 ishga tushirish (Environment Variables)
Koyeb boshqaruv panelida quyidagi o'zgaruvchilarni kiriting:
- `API_ID`
- `API_HASH`
- `SESSION_STRING`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`: `gemini-3.8-flash`
- `AI_PROVIDER`: `gemini`
- `AUTO_REPLY_ENABLED`: `True`
