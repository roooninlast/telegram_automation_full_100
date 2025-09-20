# server/app.py
import os
import asyncio
from typing import Any, Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command

# ========= Env =========
try:
    BOT_TOKEN = os.environ["BOT_TOKEN"]
except KeyError:
    raise RuntimeError("BOT_TOKEN is required")

BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")
if not BASE_URL:
    raise RuntimeError("BASE_URL is required, e.g. https://your-service.onrender.com")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "change-me")  # غيّرها لقيمة قوية

# ========= FastAPI =========
app = FastAPI(title="AI Automation (Single Web Service)")

@app.get("/")
def root():
    return {"status": "ok", "service": "ai-automation-webhook"}

@app.get("/health")
def health():
    return {"ok": True}

# ========= Aiogram v3 =========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ---- أمثلة هاندلرز؛ اربط منطقك الحقيقي هنا ----
@router.message(Command("start"))
async def on_start(msg: types.Message):
    await msg.answer("✅ البوت شغّال كسيرفيس واحد عبر Webhook على Render.")

@router.message(Command("generate"))
async def on_generate(msg: types.Message):
    # TODO: اربط هنا scoring + اختيار القالب + توليد n8n JSON من كودك
    await msg.answer("📦 استلمت طلب /generate — اربط منطق التوليد هنا.")

# ========= Webhook Endpoint =========
@app.post(f"/tg/{{secret_path}}")
async def telegram_webhook(secret_path: str, request: Request):
    if secret_path != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")

    try:
        data: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")

    try:
        update = types.Update.model_validate(data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Bad update: {e}")

    await dp.feed_update(bot, update)
    return JSONResponse({"ok": True})

# ========= Lifecycle (Webhook setup) =========
@app.on_event("startup")
async def on_startup():
    url = f"{BASE_URL}/tg/{WEBHOOK_SECRET}"
    await bot.set_webhook(url, drop_pending_updates=True)
    print(f"[webhook] set to {url}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()
