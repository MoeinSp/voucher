import asyncio
import os
import logging

from dotenv import load_dotenv
from rubpy import BotClient
from rubpy.bot import filters
from rubpy.bot.models import Update

load_dotenv()

logging.basicConfig(level=logging.INFO)
logging.getLogger("rubpy").setLevel(logging.ERROR)

TOKEN = os.getenv("BOT_TOKEN")
SUPER_ADMIN = "b0CARTT0mxL0a9061ac5624305798abf"

bot = BotClient(TOKEN)


def is_super(user_id: str) -> bool:
    return str(user_id) == SUPER_ADMIN


def is_admin(user_id: str) -> bool:
    import db
    return str(user_id) in db.get_admins()


async def _dispatch(update: Update, text: str, chat_id: str):
    msg = update.new_message

    if text == "/getid":
        return await bot.send_message(
            chat_id,
            f"chat_id (برای افزودن ادمین از این استفاده کن):\n{chat_id}",
            reply_to_message_id=msg.message_id,
        )

    if is_super(chat_id):
        from handlers_super import handle_super
        result = await handle_super(bot, update, text, chat_id, chat_id)
    elif is_admin(chat_id):
        from handlers_admin import handle_admin
        result = await handle_admin(bot, update, text, chat_id, chat_id)
    else:
        from handlers_user import handle_user
        result = await handle_user(bot, update, text, chat_id, chat_id)

    if isinstance(result, tuple):
        await _notify_admins(result, chat_id, update)


@bot.on_update(filters.text & filters.private)
async def text_handler(client, update: Update):
    msg = update.new_message
    if not msg:
        return
    chat_id = str(update.chat_id)
    text = (msg.text or "").strip()
    await _dispatch(update, text, chat_id)


@bot.on_update(filters.photo & filters.private)
async def photo_handler(client, update: Update):
    msg = update.new_message
    if not msg:
        return
    chat_id = str(update.chat_id)

    import states
    if states.get_step(chat_id) != "waiting_receipt":
        return

    state_data = states.get_state(chat_id) or {}
    order_id = state_data.get("data", {}).get("order_id")
    if order_id:
        states.set_state(chat_id, "waiting_receipt", order_id=order_id, receipt_msg_id=str(msg.message_id))

    await _dispatch(update, "__photo__", chat_id)


async def _notify_admins(result: tuple, user_chat_id: str, update: Update):
    order_id, order, product = result
    from keyboards import kb_admin_order, ChatKeypadTypeEnum
    import db

    u = db.get_user(user_chat_id) or {}
    admins = db.get_admins() | {SUPER_ADMIN}

    receipt_msg_id = order.get("receipt_msg_id")
    is_photo = receipt_msg_id and not order.get("receipt_text")

    for admin_id in admins:
        if not admin_id:
            continue
        try:
            await bot.send_message(
                admin_id,
                f"سفارش جدید\n\n"
                f"شماره: {order_id}\n"
                f"کاربر: {u.get('name', '؟')} - {user_chat_id}\n"
                f"محصول: {product['name']}\n"
                f"قیمت: {product['price']} تومان",
                chat_keypad=kb_admin_order(order_id),
                chat_keypad_type=ChatKeypadTypeEnum.NEW,
            )
            if receipt_msg_id:
                try:
                    await bot.forward_message(user_chat_id, receipt_msg_id, admin_id)
                except Exception as e2:
                    print(f"[notify] forward failed: {e2}")
                    await bot.send_message(admin_id, f"رسید:\n{order.get('receipt', '—')}")
            else:
                await bot.send_message(admin_id, f"رسید:\n{order.get('receipt', '—')}")
        except Exception as e:
            print(f"[notify_admin] error: {e}")


async def main():
    print("⏳ Starting voucher bot...")
    print(f"✅ Bot is ready. Super: {SUPER_ADMIN}")
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
