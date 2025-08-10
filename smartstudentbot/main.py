import uvicorn
import os
import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException

# Import configurations from config.py
from config import (
    DEV_MODE, DISABLE_EXTERNAL_CALLS,
    STARTUP_SET_WEBHOOK, STARTUP_CONNECT_DB, STARTUP_CONNECT_REDIS,
    TELEGRAM_BOT_TOKEN, BASE_URL, WEBHOOK_SECRET, BOT_ID, ADMIN_CHAT_IDS
)

# A basic logger. Will be replaced by the advanced logger from utils later.
logging.basicConfig(level=logging.INFO if not DEV_MODE else logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# --- Conditional Bot Initialization ---
bot = None
dp = None

# Only initialize the bot and dispatcher if external calls are enabled
# and a token is provided. This allows the app to start even without a token.
if not DISABLE_EXTERNAL_CALLS and TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_TOKEN != "dummy_token":
    from aiogram import Bot, Dispatcher, types
    from aiogram.fsm.storage.memory import MemoryStorage
    from utils.db_utils import DbSessionMiddleware

    storage = MemoryStorage()
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=storage)

    # Register middleware to pass DB session to handlers
    dp.update.middleware(DbSessionMiddleware())

    # --- Router Imports ---
    from handlers import (
        cmd_start, admin_handler, ai_handler, group_handler, news_handler,
        cost_handler, info_handler, weather_handler, isee_handler, live_chat_handler,
        guide_handler, success_story_handler, roommate_handler, feedback_handler,
        gamification_handler
    )
    dp.include_router(cmd_start.router)
    dp.include_router(guide_handler.router)
    dp.include_router(gamification_handler.router)
    dp.include_router(feedback_handler.router)
    dp.include_router(roommate_handler.router)
    dp.include_router(success_story_handler.router)
    dp.include_router(live_chat_handler.router)
    dp.include_router(cost_handler.router)
    dp.include_router(info_handler.router)
    dp.include_router(weather_handler.router)
    dp.include_router(isee_handler.router)
    dp.include_router(admin_handler.router)
    dp.include_router(ai_handler.router)
    dp.include_router(group_handler.router)
    dp.include_router(news_handler.router)

else:
    logger.warning("Bot is DISABLED due to DISABLE_EXTERNAL_CALLS or missing token.")
    # If the bot is disabled, we still need a dispatcher object for the webhook endpoint
    # but it won't have any handlers.
    from aiogram import Dispatcher, Bot, types
    from aiogram.fsm.storage.memory import MemoryStorage
from utils.db_utils import DbSessionMiddleware
    bot = None # No bot instance
    dp = Dispatcher(storage=MemoryStorage())
# Register middleware even if bot is disabled, for consistency
dp.update.middleware(DbSessionMiddleware())


# --- Webhook Endpoint ---
WEBHOOK_PATH = f"/{BOT_ID}/{WEBHOOK_SECRET}"

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    if not dp or not bot:
        logger.error("Webhook called but bot is not initialized.")
        raise HTTPException(status_code=503, detail="Bot is not running")

    update_data = await request.json()
    update = types.Update.model_validate(update_data, context={"bot": bot})
    await dp.feed_update(bot=bot, update=update)
    return {"status": "ok"}


# --- Health Check Endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/ready")
async def readiness_check():
    # In a real scenario, this would check DB, Redis, etc.
    # For now, it just checks if the bot object exists.
    if bot:
        return {"status": "ready"}
    return {"status": "ready (bot disabled)"}


from models_db import create_db_and_tables

# --- Placeholder connection functions ---
async def _connect_db():
    logger.info("Connecting to Database and creating tables...")
    await create_db_and_tables()
    logger.info("Database setup complete.")
    return True

async def _connect_redis():
    logger.info("Connecting to Redis...")
    await asyncio.sleep(0.1) # Placeholder for real Redis connection
    logger.info("Redis connection successful (mock).")
    return True


# --- Startup and Shutdown Events ---
@app.on_event("startup")
async def on_startup():
    logger.info(f"Starting up... DEV_MODE={DEV_MODE}, DISABLE_EXTERNAL_CALLS={DISABLE_EXTERNAL_CALLS}")

    if STARTUP_CONNECT_DB:
        try:
            await asyncio.wait_for(_connect_db(), timeout=5)
        except asyncio.TimeoutError:
            logger.warning("Database connection timed out.")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")

    if STARTUP_CONNECT_REDIS:
        try:
            await asyncio.wait_for(_connect_redis(), timeout=5)
        except asyncio.TimeoutError:
            logger.warning("Redis connection timed out.")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")

    if STARTUP_SET_WEBHOOK and bot:
        webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
        try:
            logger.info(f"Setting webhook to {webhook_url}")
            await asyncio.wait_for(
                bot.set_webhook(
                    url=webhook_url,
                    allowed_updates=["message", "callback_query", "chat_member"],
                    secret_token=WEBHOOK_SECRET
                ),
                timeout=5.0
            )
            logger.info("Webhook set successfully.")
        except asyncio.TimeoutError:
            logger.warning(f"Webhook setup timed out.")
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
    else:
        logger.info("Skipping webhook setup on startup.")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down...")
    if bot and bot.session:
        await bot.session.close()
    logger.info("Shutdown complete.")


# --- Main execution ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # Use the app string for uvicorn to support reloading
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=DEV_MODE)
