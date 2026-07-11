"""
هندلرهای کاربر عادی
"""
import db
import states
from keyboards import kb_main, kb_products, kb_cancel, kb_back, kb_inline_cancel, kb_inline_support_cancel, ChatKeypadTypeEnum


def _sell_summary(order: dict, product: dict) -> str:
    return (
        f"🔖 {product.get('name', '؟')}\n"
        f"💰 {product.get('price', 0):,} تومان\n"
        f"🎟 کد ووچر:\n{order.get('voucher_code', '—')}\n\n"
        f"💳 شماره کارت:\n{order.get('seller_card', '—')}\n"
        f"👤 {order.get('seller_first_name', '')} {order.get('seller_last_name', '')}"
    )


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

    # ── ارسال رسید (خرید) ────────────────────────────────────────────────────
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
        products = db.get_active_products("buy")
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

    if text == "💸 فروش ووچر":
        products = db.get_active_products("sell")
        if not products:
            return await bot.send_message(
                chat_id, "⚠️ در حال حاضر محصولی برای فروش موجود نیست.\nبعداً دوباره چک کن.",
                reply_to_message_id=msg.message_id,
            )
        states.set_state(user_id, "selecting_sell_product", page=0)
        return await bot.send_message(
            chat_id, "💸 کدوم ووچر رو میخوای بفروشی؟",
            chat_keypad=kb_products(products, 0), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            reply_to_message_id=msg.message_id,
        )

    if step == "selecting_product":
        page = states.get_state(user_id)["data"].get("page", 0)
        products = db.get_active_products("buy")

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

        order_id = db.create_order(chat_id, pid, order_type="buy")
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

    # ── انتخاب محصول برای فروش ───────────────────────────────────────────────
    if step == "selecting_sell_product":
        page = states.get_state(user_id)["data"].get("page", 0)
        products = db.get_active_products("sell")

        if text == "🔙 بازگشت":
            states.clear_state(user_id)
            return await bot.send_message(
                chat_id, "به منوی اصلی برگشتی.",
                chat_keypad=kb_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
                reply_to_message_id=msg.message_id,
            )

        if text == "▶️ بعدی":
            page += 1
            states.set_state(user_id, "selecting_sell_product", page=page)
            return await bot.send_message(
                chat_id, "💸 کدوم ووچر رو میخوای بفروشی؟",
                chat_keypad=kb_products(products, page), chat_keypad_type=ChatKeypadTypeEnum.NEW,
                reply_to_message_id=msg.message_id,
            )

        if text == "◀️ قبلی":
            page = max(0, page - 1)
            states.set_state(user_id, "selecting_sell_product", page=page)
            return await bot.send_message(
                chat_id, "💸 کدوم ووچر رو میخوای بفروشی؟",
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
        order_id = db.create_order(chat_id, pid, order_type="sell")
        states.set_state(user_id, "sell_voucher_code", order_id=order_id)

        desc = f"\n{p['description']}" if p.get("description") else ""
        return await bot.send_message(
            chat_id,
            f"💸 فروش ووچر\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"🔖 {p['name']}{desc}\n"
            f"💰 مبلغ دریافتی: {p['price']:,} تومان\n\n"
            f"🎟 کد ووچر خودت رو بفرست:",
            inline_keypad=kb_inline_cancel(),
            reply_to_message_id=msg.message_id,
        )

    if step == "sell_voucher_code":
        order_id = states.get_state(user_id)["data"].get("order_id")
        if not order_id:
            states.clear_state(user_id)
            return
        code = text.strip()
        if not code or code == "__photo__":
            return await bot.send_message(
                chat_id, "⚠️ کد ووچر رو به صورت متن بفرست.",
                inline_keypad=kb_inline_cancel(),
                reply_to_message_id=msg.message_id,
            )
        db.update_order(order_id, voucher_code=code)
        states.set_state(user_id, "sell_card_number", order_id=order_id)
        return await bot.send_message(
            chat_id,
            "💳 شماره کارت بانکی‌ات رو بفرست:\n"
            "(۱۶ رقم، بدون فاصله یا با فاصله)",
            inline_keypad=kb_inline_cancel(),
            reply_to_message_id=msg.message_id,
        )

    if step == "sell_card_number":
        order_id = states.get_state(user_id)["data"].get("order_id")
        if not order_id:
            states.clear_state(user_id)
            return
        card = text.strip().replace(" ", "").replace("-", "")
        if text == "__photo__" or not card.isdigit() or len(card) < 16:
            return await bot.send_message(
                chat_id, "⚠️ شماره کارت معتبر وارد کن (حداقل ۱۶ رقم).",
                inline_keypad=kb_inline_cancel(),
                reply_to_message_id=msg.message_id,
            )
        db.update_order(order_id, seller_card=card)
        states.set_state(user_id, "sell_first_name", order_id=order_id)
        return await bot.send_message(
            chat_id, "👤 نام صاحب کارت رو بنویس:",
            inline_keypad=kb_inline_cancel(),
            reply_to_message_id=msg.message_id,
        )

    if step == "sell_first_name":
        order_id = states.get_state(user_id)["data"].get("order_id")
        if not order_id:
            states.clear_state(user_id)
            return
        first = text.strip()
        if not first or text == "__photo__":
            return await bot.send_message(
                chat_id, "⚠️ نام رو به صورت متن بفرست.",
                inline_keypad=kb_inline_cancel(),
                reply_to_message_id=msg.message_id,
            )
        db.update_order(order_id, seller_first_name=first)
        states.set_state(user_id, "sell_last_name", order_id=order_id, first_name=first)
        return await bot.send_message(
            chat_id, "👤 نام خانوادگی صاحب کارت رو بنویس:",
            inline_keypad=kb_inline_cancel(),
            reply_to_message_id=msg.message_id,
        )

    if step == "sell_last_name":
        order_id = states.get_state(user_id)["data"].get("order_id")
        if not order_id:
            states.clear_state(user_id)
            return
        last = text.strip()
        if not last or text == "__photo__":
            return await bot.send_message(
                chat_id, "⚠️ نام خانوادگی رو به صورت متن بفرست.",
                inline_keypad=kb_inline_cancel(),
                reply_to_message_id=msg.message_id,
            )
        db.update_order(order_id, seller_last_name=last, status="waiting_confirm")
        states.clear_state(user_id)

        order = db.get_order(order_id)
        product = db.get_product(order["product_id"]) or {}

        await bot.send_message(
            chat_id,
            f"✅ درخواست فروش ثبت شد!\n\n"
            f"{_sell_summary(order, product)}\n\n"
            f"#️⃣ سفارش: {order_id}\n"
            f"⏳ منتظر تایید ادمین باش...",
            chat_keypad=kb_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            reply_to_message_id=msg.message_id,
        )
        return order_id, order, product

    if text == "📦 سفارش‌های من":
        orders = db.get_user_orders(user_id)
        if not orders:
            return await bot.send_message(
                chat_id, "📦 هنوز هیچ سفارشی ثبت نکردی.",
            )
        status_map = {
            "pending":         ("⏳", "در انتظار تکمیل"),
            "waiting_confirm": ("🔍", "در حال بررسی"),
            "done":            ("✅", "انجام شده"),
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
            otype = db.get_order_type(o)
            kind = "🛒 خرید" if otype == "buy" else "💸 فروش"
            lines = [
                f"{icon} {label}  •  {kind}",
                f"━━━━━━━━━━━━",
                f"🔖 {p.get('name', '؟')}",
                f"💰 {p.get('price', 0):,} تومان",
                f"#️⃣ سفارش {oid}",
            ]
            if otype == "buy" and o.get("voucher_code"):
                lines.append(f"🎟 کد:\n{o['voucher_code']}")
            if otype == "sell":
                if o.get("voucher_code"):
                    lines.append(f"🎟 کد ارسالی:\n{o['voucher_code']}")
                if o.get("seller_card"):
                    lines.append(f"💳 {o['seller_card']}")
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
            "📖 راهنما\n"
            "━━━━━━━━━━━━━━━━━\n"
            "🛒 خرید ووچر:\n"
            "۱. محصول رو انتخاب کن\n"
            "۲. مبلغ رو واریز کن\n"
            "۳. عکس رسید رو بفرست\n"
            "۴. بعد از تایید، کد ووچر برات میاد\n\n"
            "💸 فروش ووچر:\n"
            "۱. نوع ووچر رو انتخاب کن\n"
            "۲. کد ووچر رو بفرست\n"
            "۳. شماره کارت و نام و نام‌خانوادگی صاحب کارت رو بده\n"
            "۴. بعد از تایید، رسید واریز برات ارسال میشه\n\n"
            "برای پیگیری روی سفارش‌های من بزن.",
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
