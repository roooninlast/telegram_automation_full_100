# Telegram AI-Automation Bot — Template-Driven MVP (100 templates)

This repository contains:
- **FastAPI** service to index/search/compose workflows from the template repo.
- **aiogram** Telegram bot that calls the service to generate n8n JSON.
- **100 ready templates** spread across common automations (RSS→Telegram, Webhook→Sheets, HTTP monitor→Telegram).
- A **validator** with guardrails (nodes whitelist, env placeholders, basic structure).
- Render deployment config (`render.yaml`) for a web service + worker.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/index_templates.py
uvicorn server.main:app --reload --port 8000

# in another terminal
export BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
export API_BASE=http://127.0.0.1:8000
python bot/bot.py
```

## Deploy on Render
- Connect this repo, use the included `render.yaml` as a Blueprint.
- After the web service is up, set the **API_BASE** env var in the worker to the web URL.
- Set **BOT_TOKEN** from @BotFather.

Generated at: 2025-09-14T18:42:46.186088Z
