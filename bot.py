import asyncio
import os
import time
import logging
from pathlib import Path

from dotenv import load_dotenv
from rubpy import BotClient
from rubpy.bot import filters
from rubpy.bot.models import Update

load_dotenv()

logging.basicConfig(level=logging.INFO)
logging.getLogger("rubpy").setLevel(logging.ERROR)

TOKEN = os.getenv("BOT_TOKEN")
# SUPER_ADMIN = "b0CARTT0mxL0a9061ac5624305798abf"
SUPER_ADMIN = "b0CARTT0nEn086a83b389093604f7527"

BOT_START_TIME = int(time.time())
bot = BotClient(
    token=TOKEN,
    timeout=15.0,
    rate_limit=0.1,
)

offset_dir = Path(__file__).parent / "data_offset"
offset_dir.mkdir(parents=True, exist_ok=True)
bot._offset_file = offset_dir / "offset_id"
bot.next_offset_id = bot._load_persisted_offset()


# ── میدلور: رد کردن پیام‌های قدیمی ───────────────────────────────────────────
# اگه افست ریست شه، روبیکا کل بک‌لاگ قدیمی رو دوباره می‌فرسته. این میدلور
# هر آپدیتی که زمانش قبل از روشن‌شدن ربات باشه رو رد می‌کنه تا ربات به
# پیام‌های کهنه جواب نده. به محض دیدن اولین پیام تازه، چک خاموش می‌شه.
count = 0
done_flag = False


@bot.middleware()
async def skip_old_updates(client, update: Update, call_next):
    from rubpy.bot.models import InlineMessage
    if isinstance(update, InlineMessage):
        return await call_next()

    global count
    global done_flag

    # توی polling زمان توی new_message.time هست نه update_time
    ut = update.update_time
    if ut is None:
        m = getattr(update, "new_message", None) or getattr(update, "updated_message", None)
        ut = getattr(m, "time", None) if m else None

    if done_flag:
        pass
    elif ut is None:
        return await call_next()
    elif int(ut) < BOT_START_TIME:
        # پیام قدیمی است
        count += 1
        if count % 2 == 0:
            print(count)
        return
    else:
        print("DONE ✅")
        done_flag = True

    return await call_next()


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


async def _run_polling():
    """حلقه‌ی polling ساده بدون backoff."""
    await bot.start()
    while bot.running:
        try:
            updates = await bot.updater(limit=100, poll_timeout=30)
        except Exception as e:
            logging.error("polling error: %s", e)
            updates = []

        if updates:
            results = await asyncio.gather(
                *(bot.process_update(u) for u in updates),
                return_exceptions=True,
            )
            for r in results:
                if isinstance(r, Exception):
                    logging.error("update processing failed: %s", r)

        await asyncio.sleep(0.5)


async def main():
    print("⏳ Starting voucher bot...")
    print(f"✅ Bot is ready. Super: {SUPER_ADMIN}")
    await _run_polling()


if __name__ == "__main__":
    asyncio.run(main())
