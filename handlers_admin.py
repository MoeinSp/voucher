import uuid
import db
import states
from keyboards import (
    kb_admin_main, kb_admin_order, kb_main,
    kb_product_card, kb_products_nav,
    kb_users_nav, ChatKeypadTypeEnum,
    USERS_PAGE, PAGE_SIZE,
)

_STATUS = {
    "pending":         "⏳ در انتظار رسید",
    "waiting_confirm": "🔍 در بررسی",
    "done":            "✅ تحویل‌شده",
    "rejected":        "❌ رد‌شده",
    "cancelled":       "🚫 لغو‌شده",
}


async def handle_admin(bot, update, text: str, user_id: str, chat_id: str):
    msg = update.new_message
    step = states.get_step(user_id)

    # ── پنل اصلی ─────────────────────────────────────────────────────────────
    if text in ("/start", "/admin", "🔙 بازگشت به پنل"):
        states.clear_state(user_id)
        pending = len(db.get_pending_orders())
        badge = f"  •  {pending} سفارش جدید 🔴" if pending else ""
        return await bot.send_message(
            chat_id,
            f"👑 پنل ادمین{badge}",
            chat_keypad=kb_admin_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
        )

    # ── سفارش‌های در انتظار ───────────────────────────────────────────────────
    if text == "📋 سفارش‌های در انتظار":
        orders = db.get_pending_orders()
        if not orders:
            return await bot.send_message(
                chat_id,
                "✅ هیچ سفارش جدیدی در صف نداری.",
            )
        await bot.send_message(chat_id, f"📋 {len(orders)} سفارش در انتظار:")
        for oid, o in orders:
            p = db.get_product(o["product_id"]) or {}
            u = db.get_user(o["user_id"]) or {}
            await bot.send_message(
                chat_id,
                f"📦 سفارش #{oid}\n"
                f"━━━━━━━━━━━━\n"
                f"👤 {u.get('name', 'ناشناس')}\n"
                f"🔖 {p.get('name', '؟')} — {p.get('price', 0):,} تومان\n"
                f"🧾 رسید: {o.get('receipt', '—')}",
                inline_keypad=kb_admin_order(oid),
            )
        return

    # ── ورود کد ووچر (بعد از تایید inline) ──────────────────────────────────
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
                f"🔖 {product.get('name', '')}\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"🎟 کد ووچر:\n\n"
                f"{voucher_code}\n\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"ممنون از خریدت 🙏",
                chat_keypad=kb_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            )
            sent = True
        except Exception as e:
            print(f"[send_voucher] error: {e}")

        if sent:
            return await bot.send_message(
                chat_id,
                f"✅ کد ووچر ارسال شد.\n🎟 {voucher_code}",
                chat_keypad=kb_admin_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            )
        return await bot.send_message(
            chat_id,
            f"⚠️ ارسال به کاربر ناموفق بود!\n"
            f"🎟 کد: {voucher_code}\n"
            f"👤 آیدی: {order['user_id']}",
            chat_keypad=kb_admin_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
        )

    # ── دلیل رد سفارش (بعد از رد inline) ────────────────────────────────────
    if step == "reject_reason":
        order_id = states.get_state(user_id)["data"]["order_id"]
        order = db.get_order(order_id)
        reason = "" if text.strip() == "-" else text.strip()
        db.update_order(order_id, status="rejected")
        states.clear_state(user_id)
        msg_user = "❌ سفارش شما رد شد."
        if reason:
            msg_user += f"\n\n📝 دلیل: {reason}"
        try:
            await bot.send_message(
                order["user_id"], msg_user,
                chat_keypad=kb_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
            )
        except Exception:
            pass
        return await bot.send_message(
            chat_id, "❌ سفارش رد شد و کاربر مطلع شد.",
            chat_keypad=kb_admin_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
        )

    # ── محصولات (کارت inline) ───────────────────────────────────────────────
    if text == "📦 محصولات":
        await _send_products_page(bot, chat_id, 0)
        return

    # ── افزودن محصول ─────────────────────────────────────────────────────────
    if text == "➕ افزودن محصول":
        states.set_state(user_id, "add_product_name")
        return await bot.send_message(chat_id, "📝 اسم محصول جدید:")

    if step == "add_product_name":
        states.set_state(user_id, "add_product_price", name=text)
        return await bot.send_message(chat_id, "💰 قیمت (تومان):")

    if step == "add_product_price":
        try:
            price = int(text.replace(",", "").replace("،", "").strip())
        except ValueError:
            return await bot.send_message(chat_id, "⚠️ عدد صحیح وارد کن:")
        data = states.get_state(user_id)["data"]
        states.set_state(user_id, "add_product_desc", name=data["name"], price=price)
        return await bot.send_message(chat_id, "📄 توضیحات (یا — برای رد کردن):")

    if step == "add_product_desc":
        data = states.get_state(user_id)["data"]
        desc = "" if text.strip() in ("-", "—") else text.strip()
        pid = str(uuid.uuid4())[:8]
        db.add_product(pid, data["name"], data["price"], desc)
        states.clear_state(user_id)
        return await bot.send_message(
            chat_id,
            f"✅ محصول اضافه شد\n\n"
            f"🔖 {data['name']}\n"
            f"💰 {data['price']:,} تومان"
            + (f"\n📄 {desc}" if desc else ""),
            chat_keypad=kb_admin_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
        )

    # ── تنظیم کارت ───────────────────────────────────────────────────────────
    if text == "💳 تنظیم کارت":
        card_number = db.get_setting("card_number", "—")
        card_name = db.get_setting("card_name", "—")
        states.set_state(user_id, "set_card_number")
        return await bot.send_message(
            chat_id,
            f"💳 کارت فعلی:\n{card_number}\nبه نام: {card_name}\n\n"
            f"شماره کارت جدید:",
        )

    if step == "set_card_number":
        states.set_state(user_id, "set_card_name", card_number=text.strip())
        return await bot.send_message(chat_id, "👤 نام صاحب کارت:")

    if step == "set_card_name":
        data = states.get_state(user_id)["data"]
        db.set_setting("card_number", data["card_number"])
        db.set_setting("card_name", text.strip())
        states.clear_state(user_id)
        return await bot.send_message(
            chat_id,
            f"✅ کارت ذخیره شد\n💳 {data['card_number']}\nبه نام: {text.strip()}",
            chat_keypad=kb_admin_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
        )

    # ── پشتیبانی ─────────────────────────────────────────────────────────────
    if text == "💬 تنظیم پشتیبانی":
        cur = db.get_setting("support_id", "تنظیم نشده")
        states.set_state(user_id, "set_support_id")
        return await bot.send_message(
            chat_id,
            f"💬 آیدی پشتیبانی فعلی:\n{cur}\n\nآیدی جدید (یا — برای حذف):",
        )

    if step == "set_support_id":
        val = None if text.strip() in ("-", "—") else text.strip()
        db.set_setting("support_id", val)
        states.clear_state(user_id)
        return await bot.send_message(
            chat_id,
            "✅ آیدی پشتیبانی حذف شد." if not val else f"✅ ذخیره شد:\n{val}",
            chat_keypad=kb_admin_main(), chat_keypad_type=ChatKeypadTypeEnum.NEW,
        )

    # ── آمار ─────────────────────────────────────────────────────────────────
    if text == "📊 آمار":
        orders = db.get("orders")
        users = db.get_all_users()
        products = db.get_all_products()
        done     = sum(1 for o in orders.values() if o["status"] == "done")
        pending  = sum(1 for o in orders.values() if o["status"] == "waiting_confirm")
        rejected = sum(1 for o in orders.values() if o["status"] == "rejected")
        cancelled= sum(1 for o in orders.values() if o["status"] == "cancelled")
        active_p = sum(1 for p in products.values() if p.get("active", True))
        return await bot.send_message(
            chat_id,
            f"📊 آمار کلی\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"👥 کاربران: {len(users)}\n"
            f"📦 محصولات: {active_p} فعال / {len(products)} کل\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"✅ تحویل‌شده: {done}\n"
            f"🔍 در بررسی: {pending}\n"
            f"❌ ردشده: {rejected}\n"
            f"🚫 لغوشده: {cancelled}\n"
            f"📋 مجموع: {len(orders)}",
        )

    # ── کاربران ───────────────────────────────────────────────────────────────
    if text == "👥 کاربران":
        await _send_users_page(bot, chat_id, 0)
        return


async def _send_products_page(bot, chat_id: str, page: int):
    products = db.get_all_products()
    if not products:
        return await bot.send_message(chat_id, "⚠️ هنوز محصولی اضافه نکردی.")

    items = list(products.items())
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, len(items))
    page_items = items[start:end]

    await bot.send_message(
        chat_id,
        f"📦 محصولات — صفحه {page + 1}\n"
        f"({start + 1} تا {end} از {len(items)} محصول)",
    )
    for pid, p in page_items:
        active = p.get("active", True)
        icon = "🟢" if active else "🔴"
        desc_line = f"\n📄 {p['description']}" if p.get("description") else ""
        await bot.send_message(
            chat_id,
            f"{icon} {p['name']}\n💰 {p['price']:,} تومان{desc_line}",
            inline_keypad=kb_product_card(pid, active),
        )
    nav = kb_products_nav(page, len(items))
    if nav:
        await bot.send_message(chat_id, "─", inline_keypad=nav)


async def _send_users_page(bot, chat_id: str, page: int):
    users = db.get_all_users()
    if not users:
        return await bot.send_message(chat_id, "👥 هنوز کاربری نداری.")

    all_users = list(users.items())
    total = len(all_users)
    start = page * USERS_PAGE
    end = min(start + USERS_PAGE, total)
    page_users = all_users[start:end]

    orders = db.get("orders")

    lines = []
    for i, (uid, u) in enumerate(page_users, start=start + 1):
        name = u.get("name") or "بی‌نام"
        order_count = sum(1 for o in orders.values() if o.get("user_id") == uid)
        done_count  = sum(1 for o in orders.values() if o.get("user_id") == uid and o["status"] == "done")
        order_info = f"{done_count} خرید" if done_count else (f"{order_count} سفارش" if order_count else "")
        lines.append(f"#{i}  {name}" + (f"  •  {order_info}" if order_info else ""))

    nav = kb_users_nav(page, total)
    await bot.send_message(
        chat_id,
        f"👥 {total} کاربر — صفحه {page + 1}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        + "\n".join(lines),
        inline_keypad=nav,
    )


async def handle_admin_inline(bot, update, action: str, order_id: str, chat_id: str):
    import states

    order = db.get_order(order_id)
    print(f"[admin_inline] action={action} order_id={order_id} order={order}")

    if action == "confirm":
        if not order or order["status"] != "waiting_confirm":
            return await bot.send_message(chat_id, "⚠️ این سفارش قبلاً پردازش شده یا معتبر نیست.")
        states.set_state(chat_id, "enter_voucher_code", order_id=order_id)
        return await bot.send_message(chat_id, "🎟 کد ووچر رو بنویس:")

    if action == "reject":
        if not order or order["status"] != "waiting_confirm":
            return await bot.send_message(chat_id, "⚠️ این سفارش قبلاً پردازش شده یا معتبر نیست.")
        states.set_state(chat_id, "reject_reason", order_id=order_id)
        return await bot.send_message(chat_id, "📝 دلیل رد (یا — برای بدون دلیل):")
