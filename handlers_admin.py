import uuid
import db
import states
from keyboards import kb_admin_main, kb_admin_order, kb_main, kb_products_admin, ChatKeypadTypeEnum


async def handle_admin(bot, update, text: str, user_id: str, chat_id: str):
    msg = update.new_message
    step = states.get_step(user_id)

    # ── پنل اصلی ─────────────────────────────────────────────────────────────
    if text in ("/start", "/admin", "🔙 بازگشت به پنل"):
        states.clear_state(user_id)
        pending = len(db.get_pending_orders())
        badge = f" — {pending} سفارش جدید 🔴" if pending else ""
        return await bot.send_message(
            chat_id, f"👑 پنل ادمین{badge}",
            chat_keypad=kb_admin_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            reply_to_message_id=msg.message_id,
        )

    # ── سفارش‌های در انتظار ───────────────────────────────────────────────────
    if text == "📋 سفارش‌های در انتظار":
        orders = db.get_pending_orders()
        if not orders:
            return await bot.send_message(chat_id, "✅ سفارش در انتظاری نداری.", reply_to_message_id=msg.message_id)
        for oid, o in orders:
            p = db.get_product(o["product_id"]) or {}
            u = db.get_user(o["user_id"]) or {}
            await bot.send_message(
                chat_id,
                f"📦 سفارش جدید\n\n"
                f"شماره: {oid}\n"
                f"کاربر: {u.get('name', '؟')} — {o['user_id']}\n"
                f"محصول: {p.get('name', '؟')} — {p.get('price', 0):,} تومان\n\n"
                f"رسید:\n{o.get('receipt', '—')}",
                chat_keypad=kb_admin_order(oid),
                chat_keypad_type=ChatKeypadTypeEnum.NEW,
                reply_to_message_id=msg.message_id,
            )
        return

    # ── تایید → ادمین کد ووچر تایپ میکنه ─────────────────────────────────────
    if text.startswith("✅ تایید — "):
        order_id = text.replace("✅ تایید — ", "").strip()
        order = db.get_order(order_id)
        if not order or order["status"] != "waiting_confirm":
            return await bot.send_message(chat_id, "⚠️ سفارش معتبر نیست.", reply_to_message_id=msg.message_id)
        states.set_state(user_id, "enter_voucher_code", order_id=order_id)
        return await bot.send_message(
            chat_id, "🎟 کد ووچر رو بنویس:",
            reply_to_message_id=msg.message_id,
        )

    if step == "enter_voucher_code":
        order_id = states.get_state(user_id)["data"]["order_id"]
        order = db.get_order(order_id)
        voucher_code = text.strip()
        product = db.get_product(order["product_id"]) or {}
        db.update_order(order_id, status="done", voucher_code=voucher_code)
        states.clear_state(user_id)
        sent = False
        try:
            await bot.send_message(
                order["user_id"],
                f"🎉 سفارش شما تایید شد!\n\n"
                f"محصول: {product.get('name', '')}\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"کد ووچر شما:\n\n"
                f"{voucher_code}\n\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"ممنون از خریدت 🙏",
                chat_keypad=kb_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            )
            sent = True
        except Exception as e:
            print(f"[send_voucher] error: {e}")
        status_msg = f"✅ کد ارسال شد — {voucher_code}" if sent else f"⚠️ ارسال به کاربر ناموفق بود!\nکد: {voucher_code}\nآیدی کاربر: {order['user_id']}"
        return await bot.send_message(
            chat_id, status_msg,
            chat_keypad=kb_admin_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            reply_to_message_id=msg.message_id,
        )

    # ── رد سفارش ─────────────────────────────────────────────────────────────
    if text.startswith("❌ رد — "):
        order_id = text.replace("❌ رد — ", "").strip()
        order = db.get_order(order_id)
        if not order or order["status"] != "waiting_confirm":
            return await bot.send_message(chat_id, "⚠️ سفارش معتبر نیست.", reply_to_message_id=msg.message_id)
        states.set_state(user_id, "reject_reason", order_id=order_id)
        return await bot.send_message(chat_id, "📝 دلیل رد (یا - برای بدون دلیل):", reply_to_message_id=msg.message_id)

    if step == "reject_reason":
        order_id = states.get_state(user_id)["data"]["order_id"]
        order = db.get_order(order_id)
        reason = "" if text.strip() == "-" else text.strip()
        db.update_order(order_id, status="rejected")
        states.clear_state(user_id)
        msg_user = "❌ سفارش شما رد شد."
        if reason:
            msg_user += f"\n\nدلیل: {reason}"
        try:
            await bot.send_message(order["user_id"], msg_user, chat_keypad=kb_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW)
        except Exception:
            pass
        return await bot.send_message(
            chat_id, "❌ سفارش رد شد.",
            chat_keypad=kb_admin_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            reply_to_message_id=msg.message_id,
        )

    # ── محصولات (فعال/غیرفعال/حذف) ──────────────────────────────────────────
    if text == "📦 محصولات":
        products = db.get_all_products()
        if not products:
            return await bot.send_message(chat_id, "⚠️ محصولی نداری.", reply_to_message_id=msg.message_id)
        states.set_state(user_id, "managing_products")
        return await bot.send_message(
            chat_id,
            "📦 محصولات:\nبرای فعال/غیرفعال کردن روی نام محصول بزن\nبرای حذف روی 🗑 بزن",
            chat_keypad=kb_products_admin(products), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            reply_to_message_id=msg.message_id,
        )

    if step == "managing_products":
        if text == "🔙 بازگشت به پنل":
            states.clear_state(user_id)
            return await bot.send_message(
                chat_id, "👑 پنل ادمین",
                chat_keypad=kb_admin_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
                reply_to_message_id=msg.message_id,
            )
        products = db.get_all_products()

        # حذف با دکمه 🗑
        for pid, p in products.items():
            if text == f"🗑 {p['name']}":
                db.delete_product(pid)
                products = db.get_all_products()
                return await bot.send_message(
                    chat_id, f"✅ {p['name']} حذف شد.",
                    chat_keypad=kb_products_admin(products) if products else kb_admin_main(),
                    chat_keypad_type=ChatKeypadTypeEnum.NEW,
                    reply_to_message_id=msg.message_id,
                )

        # toggle فعال/غیرفعال
        for pid, p in products.items():
            status = "✅" if p.get("active", True) else "❌"
            if text == f"{status} {p['name']}":
                new_state = db.toggle_product(pid)
                label = "فعال ✅" if new_state else "غیرفعال ❌"
                return await bot.send_message(
                    chat_id, f"{p['name']} — {label}",
                    chat_keypad=kb_products_admin(db.get_all_products()),
                    chat_keypad_type=ChatKeypadTypeEnum.NEW,
                    reply_to_message_id=msg.message_id,
                )

    # ── افزودن محصول ─────────────────────────────────────────────────────────
    if text == "➕ افزودن محصول":
        states.set_state(user_id, "add_product_name")
        return await bot.send_message(chat_id, "📝 اسم محصول:", reply_to_message_id=msg.message_id)

    if step == "add_product_name":
        states.set_state(user_id, "add_product_price", name=text)
        return await bot.send_message(chat_id, "💰 قیمت (تومان):", reply_to_message_id=msg.message_id)

    if step == "add_product_price":
        try:
            price = int(text.replace(",", "").replace("،", "").strip())
        except ValueError:
            return await bot.send_message(chat_id, "⚠️ عدد صحیح وارد کن.", reply_to_message_id=msg.message_id)
        data = states.get_state(user_id)["data"]
        states.set_state(user_id, "add_product_desc", name=data["name"], price=price)
        return await bot.send_message(chat_id, "📄 توضیحات (یا - برای رد):", reply_to_message_id=msg.message_id)

    if step == "add_product_desc":
        data = states.get_state(user_id)["data"]
        desc = "" if text.strip() == "-" else text.strip()
        pid = str(uuid.uuid4())[:8]
        db.add_product(pid, data["name"], data["price"], desc)
        states.clear_state(user_id)
        return await bot.send_message(
            chat_id, f"✅ محصول اضافه شد\nID: {pid} | {data['name']} | {data['price']:,} تومان",
            chat_keypad=kb_admin_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            reply_to_message_id=msg.message_id,
        )

    # ── تنظیم کارت ───────────────────────────────────────────────────────────
    if text == "💳 تنظیم کارت":
        card_number = db.get_setting("card_number", "تنظیم نشده")
        card_name   = db.get_setting("card_name",   "تنظیم نشده")
        states.set_state(user_id, "set_card_number")
        return await bot.send_message(
            chat_id,
            f"💳 کارت فعلی:\n{card_number}\nبه نام: {card_name}\n\nشماره کارت جدید:",
            reply_to_message_id=msg.message_id,
        )

    if step == "set_card_number":
        states.set_state(user_id, "set_card_name", card_number=text.strip())
        return await bot.send_message(chat_id, "👤 اسم صاحب کارت:", reply_to_message_id=msg.message_id)

    if step == "set_card_name":
        data = states.get_state(user_id)["data"]
        db.set_setting("card_number", data["card_number"])
        db.set_setting("card_name", text.strip())
        states.clear_state(user_id)
        return await bot.send_message(
            chat_id, f"✅ کارت ذخیره شد\n{data['card_number']}\nبه نام: {text.strip()}",
            chat_keypad=kb_admin_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            reply_to_message_id=msg.message_id,
        )

    # ── ID پشتیبانی ──────────────────────────────────────────────────────────
    if text == "💬 تنظیم پشتیبانی":
        cur = db.get_setting("support_id", "تنظیم نشده")
        states.set_state(user_id, "set_support_id")
        return await bot.send_message(
            chat_id,
            f"آیدی پشتیبانی فعلی:\n{cur}\n\nآیدی یا یوزرنیم جدید (یا - برای حذف):",
            reply_to_message_id=msg.message_id,
        )

    if step == "set_support_id":
        val = None if text.strip() == "-" else text.strip()
        db.set_setting("support_id", val)
        states.clear_state(user_id)
        msg_text = "✅ آیدی پشتیبانی حذف شد." if not val else f"✅ آیدی پشتیبانی ذخیره شد:\n{val}"
        return await bot.send_message(
            chat_id, msg_text,
            chat_keypad=kb_admin_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            reply_to_message_id=msg.message_id,
        )

    # ── آمار ─────────────────────────────────────────────────────────────────
    if text == "📊 آمار":
        orders = db.get("orders")
        users = db.get_all_users()
        done    = sum(1 for o in orders.values() if o["status"] == "done")
        pending = sum(1 for o in orders.values() if o["status"] == "waiting_confirm")
        rejected= sum(1 for o in orders.values() if o["status"] == "rejected")
        products = db.get_all_products()
        active_p = sum(1 for p in products.values() if p.get("active", True))
        return await bot.send_message(
            chat_id,
            f"📊 آمار\n\n"
            f"👥 کاربران: {len(users)}\n"
            f"📦 محصولات فعال: {active_p} از {len(products)}\n"
            f"✅ تحویل‌شده: {done}\n"
            f"⏳ در انتظار: {pending}\n"
            f"❌ رد‌شده: {rejected}",
            reply_to_message_id=msg.message_id,
        )

    # ── کاربران ───────────────────────────────────────────────────────────────
    if text == "👥 کاربران":
        users = db.get_all_users()
        if not users:
            return await bot.send_message(chat_id, "👥 کاربری نداری.", reply_to_message_id=msg.message_id)
        lines = [f"• {u.get('name', '؟')} — {uid}" for uid, u in list(users.items())[-20:]]
        return await bot.send_message(
            chat_id, f"👥 {len(users)} کاربر\n\n" + "\n".join(lines),
            reply_to_message_id=msg.message_id,
        )
