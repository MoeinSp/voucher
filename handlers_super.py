"""
پنل انحصاری سوپر ادمین
"""
import db
import states
from keyboards import kb_super_main, kb_admins_list, kb_admin_rm_confirm, ChatKeypadTypeEnum
from handlers_admin import handle_admin


async def handle_super(bot, update, text: str, user_id: str, chat_id: str):
    msg = update.new_message

    # ── /start سوپر ─────────────────────────────────────────────────────────
    if text == "/start":
        admins = db.get_admins()
        pending = len(db.get_pending_orders())
        badge = f"  •  {pending} سفارش جدید 🔴" if pending else ""
        return await bot.send_message(
            chat_id,
            f"👑 سلام سوپر ادمین!{badge}\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"👥 ادمین‌های فعال: {len(admins)}",
            chat_keypad=kb_super_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
        )

    # ── مدیریت ادمین‌ها ──────────────────────────────────────────────────────
    if text == "👑 مدیریت ادمین‌ها":
        await _show_admin_list(bot, chat_id)
        return

    # ── افزودن ادمین با متن ──────────────────────────────────────────────────
    if text.startswith("ادمین جدید "):
        new_id = text.replace("ادمین جدید ", "").strip()
        if not new_id.startswith("b0"):
            return await bot.send_message(chat_id, "⚠️ آیدی باید با b0 شروع بشه.")
        if new_id in db.get_admins():
            return await bot.send_message(chat_id, "⚠️ این آیدی قبلاً ادمینه.")
        from keyboards import kb_admin_add_confirm
        return await bot.send_message(
            chat_id,
            f"➕ افزودن ادمین:\n{new_id}\n\nمطمئنی؟",
            inline_keypad=kb_admin_add_confirm(new_id),
        )

    step = states.get_step(user_id)

    if step == "add_admin":
        new_id = states.get_state(user_id)["data"].get("admin_id", "")
        if db.add_admin(new_id):
            states.clear_state(user_id)
            try:
                await bot.send_message(new_id, "✅ شما به عنوان ادمین ربات اضافه شدید.\n/start بزن.")
            except Exception:
                pass
            await _show_admin_list(bot, chat_id)
        return

    # ── بقیه دستورات مثل ادمین عادی ─────────────────────────────────────────
    return await handle_admin(bot, update, text, user_id, chat_id)


async def _show_admin_list(bot, chat_id: str):
    admins = list(db.get_admins())
    if not admins:
        return await bot.send_message(
            chat_id,
            "👥 هیچ ادمینی اضافه نکردی.\n\n"
            "برای افزودن بنویس:\nادمین جدید [b0xxx...]",
        )
    lines = [f"#{i+1}  {a}" for i, a in enumerate(admins)]
    await bot.send_message(
        chat_id,
        f"👑 ادمین‌های فعال ({len(admins)} نفر)\n"
        f"━━━━━━━━━━━━━━━━━\n"
        + "\n".join(lines) +
        "\n━━━━━━━━━━━━━━━━━\n"
        "برای افزودن بنویس:\nادمین جدید [b0xxx...]",
        inline_keypad=kb_admins_list(admins),
    )


async def handle_super_inline(bot, update, action: str, payload: str, chat_id: str):
    """هندلر دکمه‌های inline سوپر ادمین"""

    if action == "arm":  # ask confirmation
        uid = payload
        admins = db.get_admins()
        if uid not in admins:
            return await bot.send_message(chat_id, "⚠️ این ادمین دیگه توی لیست نیست.")
        return await bot.send_message(
            chat_id,
            f"❌ حذف ادمین:\n{uid}\n\nمطمئنی؟",
            inline_keypad=kb_admin_rm_confirm(uid),
        )

    if action == "armc":  # confirmed remove
        uid = payload
        if db.remove_admin(uid):
            try:
                await bot.send_message(uid, "❌ دسترسی ادمین شما لغو شد.")
            except Exception:
                pass
            await bot.send_message(chat_id, f"✅ ادمین حذف شد.")
        else:
            await bot.send_message(chat_id, "⚠️ این آیدی توی لیست ادمین‌ها نیست.")
        await _show_admin_list(bot, chat_id)
        return

    if action == "adm:list":
        await _show_admin_list(bot, chat_id)
        return
