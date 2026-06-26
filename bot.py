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
logging.getLogger("rubpy").setLevel(logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))
SUPER_ADMIN = "b0CARTT0mxL0a9061ac5624305798abf"
# SUPER_ADMIN = "b0CARTT0nEn086a83b389093604f7527"

BOT_START_TIME = int(time.time())
bot = BotClient(
    token=TOKEN,
    timeout=15.0,
    rate_limit=0.1,
    use_webhook=bool(WEBHOOK_URL),
)

offset_dir = Path(__file__).parent / "data_offset"
offset_dir.mkdir(parents=True, exist_ok=True)
bot._offset_file = offset_dir / "offset_id"
bot.next_offset_id = bot._load_persisted_offset()


# ── میدلور: رد کردن پیام‌های قدیمی ───────────────────────────────────────────
count = 0
done_flag = False


@bot.middleware()
async def skip_old_updates(client, update: Update, call_next):
    from rubpy.bot.models import InlineMessage
    if isinstance(update, InlineMessage):
        return await call_next()

    global count, done_flag
    ut = update.update_time
    if ut is None:
        m = getattr(update, "new_message", None) or getattr(update, "updated_message", None)
        ut = getattr(m, "time", None) if m else None

    if done_flag:
        pass
    elif ut is None:
        return await call_next()
    elif int(ut) < BOT_START_TIME:
        count += 1
        if count % 5 == 0:
            print(f"[skip] {count} old updates skipped")
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


# ── استخراج button_id ────────────────────────────────────────────────────────

def _btn_id(update) -> str:
    from rubpy.bot.models import InlineMessage
    if isinstance(update, InlineMessage):
        aux = getattr(update, "aux_data", None)
    else:
        msg = getattr(update, "new_message", None) or getattr(update, "updated_message", None)
        aux = getattr(msg, "aux_data", None) if msg else None
    if aux is None:
        return ""
    if isinstance(aux, dict):
        return aux.get("button_id", "")
    return getattr(aux, "button_id", "") or ""


def _safe(coro):
    async def _run():
        try:
            await coro
        except Exception as e:
            logging.error("[inline] error: %s", e, exc_info=True)
    return _run()


# ── هندلرهای سفارش ──────────────────────────────────────────────────────────

@bot.on_update(filters.button(r"confirm:.*", regex=True))
async def admin_confirm_handler(client, update):
    chat_id = str(update.chat_id)
    order_id = _btn_id(update).replace("confirm:", "").strip()
    from handlers_admin import handle_admin_inline
    await _safe(handle_admin_inline(bot, update, "confirm", order_id, chat_id))


@bot.on_update(filters.button(r"reject:.*", regex=True))
async def admin_reject_handler(client, update):
    chat_id = str(update.chat_id)
    order_id = _btn_id(update).replace("reject:", "").strip()
    from handlers_admin import handle_admin_inline
    await _safe(handle_admin_inline(bot, update, "reject", order_id, chat_id))


@bot.on_update(filters.button(r"getreceipt:.*", regex=True))
async def get_receipt_handler(client, update):
    chat_id = str(update.chat_id)
    order_id = _btn_id(update).replace("getreceipt:", "").strip()
    async def _do():
        import db
        order = db.get_order(order_id)
        if not order:
            return await bot.send_message(chat_id, "⚠️ سفارش پیدا نشد.")
        receipt_msg_id = order.get("receipt_msg_id")
        user_id = order.get("user_id")
        if receipt_msg_id and user_id:
            try:
                await bot.forward_message(user_id, receipt_msg_id, chat_id)
                return
            except Exception:
                pass
        receipt_text = order.get("receipt", "—")
        await bot.send_message(chat_id, f"🧾 رسید سفارش #{order_id}:\n{receipt_text}")
    await _safe(_do())


# ── هندلرهای محصولات ─────────────────────────────────────────────────────────

@bot.on_update(filters.button(r"pt:.*", regex=True))
async def product_toggle_handler(client, update):
    pid = _btn_id(update).replace("pt:", "").strip()
    chat_id = str(update.chat_id)
    async def _do():
        import db
        from keyboards import kb_product_card
        products = db.get_all_products() or {}
        p = products.get(pid)
        if not p:
            return await bot.send_message(chat_id, "⚠️ محصول پیدا نشد.")
        new_state = db.toggle_product(pid)
        icon = "🟢" if new_state else "🔴"
        label = "فعال ✅" if new_state else "غیرفعال ❌"
        await bot.send_message(
            chat_id,
            f"{icon} {p['name']} — {label}\n💰 {p['price']:,} تومان",
            inline_keypad=kb_product_card(pid, new_state),
        )
    await _safe(_do())


@bot.on_update(filters.button(r"pd:.*", regex=True))
async def product_del_handler(client, update):
    pid = _btn_id(update).replace("pd:", "").strip()
    chat_id = str(update.chat_id)
    async def _do():
        import db
        from keyboards import kb_product_del_confirm
        p = (db.get_all_products() or {}).get(pid)
        if not p:
            return await bot.send_message(chat_id, "⚠️ محصول پیدا نشد.")
        await bot.send_message(
            chat_id,
            f"⚠️ حذف محصول\n━━━━━━━━━━━━\n"
            f"🔖 {p['name']}\n💰 {p['price']:,} تومان\n\n"
            f"مطمئنی؟",
            inline_keypad=kb_product_del_confirm(pid),
        )
    await _safe(_do())


@bot.on_update(filters.button(r"pdc:.*", regex=True))
async def product_del_confirm_handler(client, update):
    pid = _btn_id(update).replace("pdc:", "").strip()
    chat_id = str(update.chat_id)
    async def _do():
        import db
        from handlers_admin import _send_products_page
        p = (db.get_all_products() or {}).get(pid)
        name = p["name"] if p else pid
        db.delete_product(pid)
        await bot.send_message(chat_id, f"✅ محصول «{name}» حذف شد.")
        await _send_products_page(bot, chat_id, 0)
    await _safe(_do())


@bot.on_update(filters.button(r"pp:.*", regex=True))
async def products_page_handler(client, update):
    try:
        page = int(_btn_id(update).replace("pp:", "").strip())
    except ValueError:
        page = 0
    chat_id = str(update.chat_id)
    from handlers_admin import _send_products_page
    await _safe(_send_products_page(bot, chat_id, page))


# ── هندلرهای کاربران ─────────────────────────────────────────────────────────

@bot.on_update(filters.button(r"up:.*", regex=True))
async def users_page_handler(client, update):
    try:
        page = int(_btn_id(update).replace("up:", "").strip())
    except ValueError:
        page = 0
    chat_id = str(update.chat_id)
    from handlers_admin import _send_users_page
    await _safe(_send_users_page(bot, chat_id, page))


# ── هندلرهای سوپر ادمین ──────────────────────────────────────────────────────

@bot.on_update(filters.button(r"arm:.*", regex=True))
async def admin_rm_handler(client, update):
    chat_id = str(update.chat_id)
    if not is_super(chat_id):
        return
    uid = _btn_id(update).replace("arm:", "").strip()
    from handlers_super import handle_super_inline
    await _safe(handle_super_inline(bot, update, "arm", uid, chat_id))


@bot.on_update(filters.button(r"armc:.*", regex=True))
async def admin_rm_confirm_handler(client, update):
    chat_id = str(update.chat_id)
    if not is_super(chat_id):
        return
    uid = _btn_id(update).replace("armc:", "").strip()
    from handlers_super import handle_super_inline
    await _safe(handle_super_inline(bot, update, "armc", uid, chat_id))


@bot.on_update(filters.button(r"adda:.*", regex=True))
async def admin_add_confirm_handler(client, update):
    chat_id = str(update.chat_id)
    if not is_super(chat_id):
        return
    uid = _btn_id(update).replace("adda:", "").strip()
    async def _do():
        import db
        if db.add_admin(uid):
            try:
                await bot.send_message(uid, "✅ شما به عنوان ادمین ربات اضافه شدید.\n/start بزن.")
            except Exception:
                pass
            await bot.send_message(chat_id, f"✅ ادمین {uid} اضافه شد.")
        else:
            await bot.send_message(chat_id, "⚠️ این آیدی قبلاً ادمینه.")
        from handlers_super import _show_admin_list
        await _show_admin_list(bot, chat_id)
    await _safe(_do())


@bot.on_update(filters.button(r"adm:.*", regex=True))
async def admin_nav_handler(client, update):
    chat_id = str(update.chat_id)
    if not is_super(chat_id):
        return
    from handlers_super import handle_super_inline
    await _safe(handle_super_inline(bot, update, "adm:list", "", chat_id))


# ── هندلر لغو کاربر ──────────────────────────────────────────────────────────

@bot.on_update(filters.button(r"cancel_.*", regex=True))
async def user_cancel_handler(client, update):
    chat_id = str(update.chat_id)
    btn_id = _btn_id(update)
    from handlers_user import handle_user_inline
    await _safe(handle_user_inline(bot, update, btn_id, chat_id))


# ── هندلر متن ────────────────────────────────────────────────────────────────

async def _dispatch(update: Update, text: str, chat_id: str):
    msg = update.new_message

    if text == "/getsuper":
        match = "✅ تطابق دارد" if chat_id == SUPER_ADMIN else "❌ تطابق ندارد"
        return await bot.send_message(
            chat_id,
            f"SUPER_ADMIN در کد:\n`{SUPER_ADMIN}`\n\n"
            f"chat_id شما:\n`{chat_id}`\n\n"
            f"{match}",
        )

    if text == "/getid":
        return await bot.send_message(
            chat_id,
            f"🆔 آیدی چت:\n`{chat_id}`",
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
    from rubpy.bot.models import InlineMessage
    if isinstance(update, InlineMessage):
        return
    msg = update.new_message
    if not msg:
        return
    chat_id = str(update.chat_id)
    text = (msg.text or "").strip()
    await _dispatch(update, text, chat_id)


@bot.on_update(filters.photo & filters.private)
async def photo_handler(client, update: Update):
    from rubpy.bot.models import InlineMessage
    if isinstance(update, InlineMessage):
        return
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


# ── اطلاع‌رسانی به ادمین‌ها ──────────────────────────────────────────────────

async def _notify_admins(result: tuple, user_chat_id: str, update: Update):
    order_id, order, product = result
    from keyboards import kb_admin_order
    import db

    u = db.get_user(user_chat_id) or {}
    admins = db.get_admins() | {SUPER_ADMIN}
    receipt_msg_id = order.get("receipt_msg_id")

    for admin_id in admins:
        if not admin_id:
            continue
        try:
            await bot.send_message(
                admin_id,
                f"📦 سفارش جدید #{order_id}\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"👤 {u.get('name', 'ناشناس')}\n"
                f"🔖 {product['name']}\n"
                f"💰 {product['price']:,} تومان",
                inline_keypad=kb_admin_order(order_id),
            )
            if receipt_msg_id:
                try:
                    await bot.forward_message(user_chat_id, receipt_msg_id, admin_id)
                except Exception:
                    await bot.send_message(admin_id, f"🧾 رسید:\n{order.get('receipt', '—')}")
            else:
                await bot.send_message(admin_id, f"🧾 رسید:\n{order.get('receipt', '—')}")
        except Exception as e:
            print(f"[notify_admin] error for {admin_id}: {e}")


# ── اجرا ─────────────────────────────────────────────────────────────────────

async def _run_polling():
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
    print(f"✅ Super: {SUPER_ADMIN}")
    if WEBHOOK_URL:
        print(f"🌐 Webhook: {WEBHOOK_URL} port {WEBHOOK_PORT}")
        await bot.run(webhook_url=WEBHOOK_URL, port=WEBHOOK_PORT)
    else:
        print("📡 Polling mode")
        await _run_polling()


if __name__ == "__main__":
    asyncio.run(main())
