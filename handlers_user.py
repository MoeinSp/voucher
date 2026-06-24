"""
هندلرهای کاربر عادی
"""
import db
import states
from keyboards import kb_main, kb_products, kb_cancel, kb_back, kb_inline_cancel, kb_inline_support_cancel, ChatKeypadTypeEnum


async def handle_user(bot, update, text: str, user_id: str, chat_id: str):
    msg = update.new_message
    name = ""
    try:
        info = await bot.get_chat(chat_id)
        name = info.first_name or ""
    except Exception:
        pass
    db.ensure_user(chat_id, name)

    step = states.get_step(user_id)

    # ── ارسال رسید ───────────────────────────────────────────────────────────
    if step == "waiting_receipt":
        order_id = states.get_state(user_id)["data"].get("order_id")
        if not order_id:
            states.clear_state(user_id)
            return

        if text != "__photo__":
            return await bot.send_message(
                chat_id,
                "📸 لطفاً فقط عکس رسید واریز رو بفرست.",
                inline_keypad=kb_inline_cancel(),
                reply_to_message_id=msg.message_id,
            )

        state_data = states.get_state(user_id) or {}
        receipt_msg_id = state_data.get("data", {}).get("receipt_msg_id")
        db.update_order(
            order_id, status="waiting_confirm", receipt="📸 عکس رسید",
            receipt_msg_id=receipt_msg_id,
        )
        states.clear_state(user_id)

        order = db.get_order(order_id)
        product = db.get_product(order["product_id"])

        await bot.send_message(
            chat_id,
            f"✅ رسید ثبت شد!\n\n"
            f"محصول: {product['name']}\n"
            f"شماره سفارش: {order_id}\n\n"
            f"⏳ منتظر تایید ادمین باش...",
            chat_keypad=kb_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            reply_to_message_id=msg.message_id,
        )
        return order_id, order, product

    # ── منوی اصلی ────────────────────────────────────────────────────────────
    if text in ("/start", "🔙 بازگشت"):
        states.clear_state(user_id)
        return await bot.send_message(
            chat_id,
            f"سلام {name} 👋\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🎟 به فروشگاه ووچر خوش اومدی!\n\n"
            f"از منوی پایین یه گزینه انتخاب کن:",
            chat_keypad=kb_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
        )

    if text == "🛒 خرید ووچر":
        products = db.get_active_products()
        if not products:
            return await bot.send_message(
                chat_id, "⚠️ در حال حاضر محصولی موجود نیست.\nبعداً دوباره چک کن.",
                reply_to_message_id=msg.message_id,
            )
        states.set_state(user_id, "selecting_product", page=0)
        return await bot.send_message(
            chat_id, "🛒 کدوم محصول رو میخوای؟",
            chat_keypad=kb_products(products, 0), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            reply_to_message_id=msg.message_id,
        )

    if step == "selecting_product":
        page = states.get_state(user_id)["data"].get("page", 0)
        products = db.get_active_products()

        if text == "🔙 بازگشت":
            states.clear_state(user_id)
            return await bot.send_message(
                chat_id, "به منوی اصلی برگشتی.",
                chat_keypad=kb_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
                reply_to_message_id=msg.message_id,
            )

        if text == "▶️ بعدی":
            page += 1
            states.set_state(user_id, "selecting_product", page=page)
            return await bot.send_message(
                chat_id, "🛒 کدوم محصول رو میخوای؟",
                chat_keypad=kb_products(products, page), chat_keypad_type=ChatKeypadTypeEnum.NEW,
                reply_to_message_id=msg.message_id,
            )

        if text == "◀️ قبلی":
            page = max(0, page - 1)
            states.set_state(user_id, "selecting_product", page=page)
            return await bot.send_message(
                chat_id, "🛒 کدوم محصول رو میخوای؟",
                chat_keypad=kb_products(products, page), chat_keypad_type=ChatKeypadTypeEnum.NEW,
                reply_to_message_id=msg.message_id,
            )

        selected = None
        for pid, p in products.items():
            if text == f"🔖 {p['name']} — {p['price']:,} تومان":
                selected = (pid, p)
                break
        if not selected:
            return

        pid, p = selected

        order_id = db.create_order(chat_id, pid)
        states.set_state(user_id, "waiting_receipt", order_id=order_id)

        desc = f"\n{p['description']}" if p.get("description") else ""
        card_number = db.get_setting("card_number", "—")
        card_name   = db.get_setting("card_name", "—")

        return await bot.send_message(
            chat_id,
            f"🔖 {p['name']}{desc}\n"
            f"💰 قیمت: {p['price']:,} تومان\n\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"💳 شماره کارت:\n"
            f"{card_number}\n"
            f"به نام: {card_name}\n\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"📸 بعد از واریز، عکس رسید رو اینجا بفرست.",
            inline_keypad=kb_inline_cancel(),
            reply_to_message_id=msg.message_id,
        )

    if text == "📦 سفارش‌های من":
        orders = db.get_user_orders(user_id)
        if not orders:
            return await bot.send_message(
                chat_id, "📦 هنوز هیچ سفارشی ثبت نکردی.",
            )
        status_map = {
            "pending":         ("⏳", "در انتظار رسید"),
            "waiting_confirm": ("🔍", "در حال بررسی"),
            "done":            ("✅", "تحویل داده شده"),
            "rejected":        ("❌", "رد شده"),
            "cancelled":       ("🚫", "لغو شده"),
        }
        recent = list(reversed(orders[-8:]))
        await bot.send_message(
            chat_id,
            f"📦 سفارش‌های اخیر شما ({len(orders)} سفارش)",
        )
        for oid, o in recent:
            p = db.get_product(o["product_id"]) or {}
            icon, label = status_map.get(o["status"], ("•", o["status"]))
            lines = [
                f"{icon} {label}",
                f"━━━━━━━━━━━━",
                f"🔖 {p.get('name', '؟')}",
                f"💰 {p.get('price', 0):,} تومان",
                f"#️⃣ سفارش {oid}",
            ]
            if o.get("voucher_code"):
                lines.append(f"🎟 کد:\n{o['voucher_code']}")
            await bot.send_message(chat_id, "\n".join(lines))
        return

    if text == "💬 پشتیبانی":
        support_id = db.get_setting("support_id")
        hint = f"\n\nیا مستقیم پیام بده:\n{support_id}" if support_id else ""
        states.set_state(user_id, "support_msg")
        return await bot.send_message(
            chat_id,
            f"💬 پیامت رو بنویس، ادمین در اسرع وقت جواب میده.{hint}",
            inline_keypad=kb_inline_support_cancel(),
            reply_to_message_id=msg.message_id,
        )

    if step == "support_msg":
        from bot import SUPER_ADMIN
        admins = set(db.get_admins()) | {SUPER_ADMIN}
        for admin_id in admins:
            if not admin_id:
                continue
            try:
                await bot.send_message(
                    admin_id,
                    f"💬 پیام پشتیبانی\nکاربر: {name} — {chat_id}\n\n{text}",
                )
            except Exception:
                pass
        states.clear_state(user_id)
        return await bot.send_message(
            chat_id, "✅ پیامت ارسال شد. منتظر پاسخ باش.",
            chat_keypad=kb_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            reply_to_message_id=msg.message_id,
        )

    if text == "ℹ️ راهنما":
        return await bot.send_message(
            chat_id,
            "📖 راهنمای خرید:\n\n"
            "1️⃣ روی خرید ووچر بزن\n"
            "2️⃣ محصول دلخواهت رو انتخاب کن\n"
            "3️⃣ مبلغ رو واریز کن\n"
            "4️⃣ رسید رو ارسال کن\n"
            "5️⃣ بعد از تایید ادمین، کد ووچر برات ارسال میشه ✅\n\n"
            "برای پیگیری سفارش روی سفارش‌های من بزن.",
            reply_to_message_id=msg.message_id,
        )


async def handle_user_inline(bot, update, btn_id: str, chat_id: str):
    """هندلر دکمه‌های inline کاربر — btn_id: 'cancel_order' یا 'cancel_support'"""
    import states

    if btn_id in ("cancel_order", "cancel_support"):
        order_id = (states.get_state(chat_id) or {}).get("data", {}).get("order_id")
        if order_id:
            order = db.get_order(order_id)
            if order and order.get("status") in ("pending", "waiting_receipt"):
                db.update_order(order_id, status="cancelled")
        states.clear_state(chat_id)
        return await bot.send_message(
            chat_id, "❌ لغو شد.",
            chat_keypad=kb_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
        )
