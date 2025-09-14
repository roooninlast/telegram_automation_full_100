\
import os, asyncio, aiohttp, json
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

dp = Dispatcher()

@dp.message(F.text.startswith("/start"))
async def start(m: Message):
    text = (
        "👋 أهلا! أرسل وصف المهمة وسأرجّع لك n8n JSON.\n"
        "أو استعمل: /generate <وصف المهمة>\n\n"
        "أمثلة:\n"
        "- RSS إلى تيليغرام كل ساعة\n"
        "- Webhook يستقبل بيانات ويرسلها إلى Google Sheets\n"
        "- فحص HTTP كل 10 د و تنبيه في تيليغرام عند شرط"
    )
    await m.answer(text)

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
    await m.answer("⏳ جاري توليد القالب الأنسب...")
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{API_BASE}/compose", json={"description": description}) as r:
            if r.status != 200:
                err = await r.text()
                await m.answer(f"⚠️ تعذر التوليد: {err}")
                return
            data = await r.json()
    summary = data.get("summary","")
    wf = data.get("workflow_json", {})
    secrets = data.get("required_secrets", [])
    inputs = data.get("required_inputs", [])
    pretty = json.dumps(wf, ensure_ascii=False, indent=2)
    if len(pretty) > 3500:
        pretty = pretty[:3500] + "\\n... (تم القص)"
    await m.answer(
        f"✅ تم!\n\n{summary}\n\n"
        f"🔐 أسرار مطلوبة: {', '.join(secrets) if secrets else 'لا شيء'}\n"
        f"📥 مدخلات مطلوبة: {', '.join(inputs) if inputs else 'لا شيء'}\n\n"
        f"```json\n{pretty}\n```",
        parse_mode="Markdown"
    )

async def main():
    if not BOT_TOKEN:
        print("Set BOT_TOKEN env var")
        return
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
