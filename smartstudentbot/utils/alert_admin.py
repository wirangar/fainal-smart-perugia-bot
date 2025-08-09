from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import ADMIN_CHAT_IDS
from utils.i18n import get_text

async def alert_admins_for_chat(bot: Bot, user_id: int, user_name: str):
    """
    Sends a notification to all admins about a new live chat request.
    """
    if not ADMIN_CHAT_IDS:
        print("Warning: No ADMIN_CHAT_IDS configured. Cannot alert for live chat.")
        return

    # For simplicity, we assume admins use English.
    lang = "en"
    text = get_text("live_chat_request_to_admins", lang) + f"\n\nUser: {user_name} (ID: {user_id})"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                # The callback data includes the user_id to connect to.
                InlineKeyboardButton(
                    text=get_text("live_chat_accept_button", lang),
                    callback_data=f"accept_chat_{user_id}"
                )
            ]
        ]
    )

    for admin_id in ADMIN_CHAT_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            # This can fail if an admin has blocked the bot, etc.
            print(f"Failed to send chat alert to admin {admin_id}: {e}")
