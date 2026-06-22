"""
پنل انحصاری سوپر ادمین — فقط u0CARTT00c63658e48028f34fd06b2cb
"""
import db
import states
from keyboards import kb_admin_main, kb_admin_order, ChatKeypadTypeEnum
from handlers_admin import handle_admin


async def handle_super(bot, update, text: str, user_id: str, chat_id: str):
    msg = update.new_message
    step = states.get_step(user_id)

    # ── مدیریت ادمین‌ها ───────────────────────────────────────────────────────

    if text == "👑 مدیریت ادمین‌ها":
        admins = db.get_admins()
        lines = [f"• {a}" for a in admins] if admins else ["— هیچ ادمینی نداری"]
        states.clear_state(user_id)
        return await bot.send_message(
            chat_id,
            f"👑 ادمین‌های فعلی:\n\n" + "\n".join(lines) +
            "\n\n➕ افزودن: ادمین جدید [sender_id]"
            "\n❌ حذف: حذف ادمین [sender_id]",
            reply_to_message_id=msg.message_id,
        )

    if text.startswith("ادمین جدید "):
        new_admin = text.replace("ادمین جدید ", "").strip()
        if db.add_admin(new_admin):
            try:
                await bot.send_message(
                    new_admin,
                    "✅ شما به عنوان ادمین ربات ووچر اضافه شدید.\n/start بزن.",
                )
            except Exception:
                pass
            return await bot.send_message(
                chat_id, f"✅ ادمین {new_admin} اضافه شد.",
                reply_to_message_id=msg.message_id,
            )
        return await bot.send_message(
            chat_id, "⚠️ این آیدی قبلاً ادمینه.",
            reply_to_message_id=msg.message_id,
        )

    if text.startswith("حذف ادمین "):
        rem = text.replace("حذف ادمین ", "").strip()
        if db.remove_admin(rem):
            try:
                await bot.send_message(rem, "❌ دسترسی ادمین شما لغو شد.")
            except Exception:
                pass
            return await bot.send_message(
                chat_id, f"✅ ادمین {rem} حذف شد.",
                reply_to_message_id=msg.message_id,
            )
        return await bot.send_message(
            chat_id, "❌ این آیدی توی لیست ادمین‌ها نیست.",
            reply_to_message_id=msg.message_id,
        )

    # ── /start سوپر ادمین ────────────────────────────────────────────────────
    if text == "/start":
        admins = db.get_admins()
        return await bot.send_message(
            chat_id,
            f"👑 سلام سوپر ادمین!\n\n"
            f"👥 ادمین‌های فعال: {len(admins)}\n\n"
            f"برای مدیریت ادمین‌ها بنویس: 👑 مدیریت ادمین‌ها",
            chat_keypad=_super_kb(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            reply_to_message_id=msg.message_id,
        )

    # ── بقیه دستورات مثل ادمین عادی ─────────────────────────────────────────
    return await handle_admin(bot, update, text, chat_id, chat_id)


def _super_kb():
    import hashlib
    from rubpy.bot.models import Keypad, KeypadRow, Button, ButtonTypeEnum
    def _b(t):
        bid = hashlib.md5(t.encode()).hexdigest()[:8]
        return Button(id=bid, type=ButtonTypeEnum.SIMPLE, button_text=t)
    def _r(*t): return KeypadRow(buttons=[_b(x) for x in t])
    return Keypad(rows=[
        _r("👑 مدیریت ادمین‌ها"),
        _r("📋 سفارش‌های در انتظار", "📊 آمار"),
        _r("➕ افزودن محصول", "📦 مدیریت محصولات"),
        _r("🎟 افزودن ووچر", "📜 لیست ووچرها"),
        _r("👥 کاربران"),
    ])
