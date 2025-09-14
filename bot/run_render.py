import os, asyncio, aiohttp, json
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from fastapi import FastAPI
import uvicorn

API_BASE = os.getenv("API_BASE", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# -------- Telegram bot --------
dp = Dispatcher()

@dp.message(F.text.startswith("/start"))
async def start(m: Message):
    await m.answer(
        "👋 أهلا! أرسل وصف المهمة أو استعمل: /generate <وصف>\n"
        "مثال: RSS https://site.com/feed.xml إلى تيليغرام كل ساعة"
    )

@dp.message(F.text.startswith("/generate"))
async def generate_cmd(m: Message):
    desc = m.text[len("/generate"):].strip()
    if not desc:
        await m.answer("اكتب: /generate <وصف المهمة>")
        return
    await compose_and_reply(m, desc)

@dp.message()
async def any_text(m: Message):
    await compose_and_reply(m, m.text)

async def compose_and_reply(m: Message, description: str):
    if not API_BASE:
        await m.answer("⚠️ API_BASE غير مضبوط.")
        return
    await m.answer("⏳ جاري توليد القالب الأنسب...")
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{API_BASE}/compose", json={"description": description}) as r:
            if r.status != 200:
                txt = await r.text()
                await m.answer(f"⚠️ تعذر التوليد: {txt}")
                return
            data = await r.json()
    pretty = json.dumps(data.get("workflow_json", {}), ensure_ascii=False, indent=2)
    if len(pretty) > 3500:
        pretty = pretty[:3500] + "\n... (تم القص)"
    await m.answer(
        f"✅ تم!\n\n{data.get('summary','')}\n\n"
        f"🔐 أسرار: {', '.join(data.get('required_secrets', [])) or 'لا شيء'}\n"
        f"📥 مدخلات: {', '.join(data.get('required_inputs', [])) or 'لا شيء'}\n\n"
        f"```json\n{pretty}\n```",
        parse_mode="Markdown"
    )

async def run_bot():
    if not BOT_TOKEN:
        print("BOT_TOKEN not set"); return
    bot = Bot(BOT_TOKEN)
    # مهم: امسح أي Webhook سابق قبل البدء بالـPolling
    await bot.delete_webhook(drop_pending_updates=True)
    from aiogram import Dispatcher
    await dp.start_polling(bot)

# -------- Tiny FastAPI for Render health --------
app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

# -------- Entry: run FastAPI + bot together --------
async def main():
    asyncio.create_task(run_bot())
    port = int(os.getenv("PORT", "8000"))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
