import hashlib
from rubpy.bot.models import Keypad, KeypadRow, Button, ButtonTypeEnum
from rubpy.bot.enums import ChatKeypadTypeEnum

BTE = ButtonTypeEnum
PAGE_SIZE = 5


def _b(text: str) -> Button:
    bid = hashlib.md5(text.encode()).hexdigest()[:8]
    return Button(id=bid, type=BTE.SIMPLE, button_text=text)


def _row(*texts) -> KeypadRow:
    return KeypadRow(buttons=[_b(t) for t in texts])


# ── کاربر ────────────────────────────────────────────────────────────────────

def kb_main() -> Keypad:
    return Keypad(rows=[
        _row("🛒 خرید ووچر"),
        _row("📦 سفارش‌های من", "ℹ️ راهنما"),
        _row("💬 پشتیبانی"),
    ])


def kb_products(products: dict, page: int = 0) -> Keypad:
    items = list(products.values())
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = items[start:end]
    rows = [_row(f"🔖 {p['name']} — {p['price']:,} تومان") for p in page_items]
    nav = []
    if page > 0:
        nav.append("◀️ قبلی")
    if end < len(items):
        nav.append("▶️ بعدی")
    if nav:
        rows.append(_row(*nav))
    rows.append(_row("🔙 بازگشت"))
    return Keypad(rows=rows)


def kb_cancel() -> Keypad:
    return Keypad(rows=[_row("❌ لغو سفارش")])


def kb_back() -> Keypad:
    return Keypad(rows=[_row("🔙 بازگشت")])


# ── ادمین ────────────────────────────────────────────────────────────────────

def kb_admin_main() -> Keypad:
    return Keypad(rows=[
        _row("📋 سفارش‌های در انتظار"),
        _row("📦 محصولات", "💳 تنظیم کارت"),
        _row("➕ افزودن محصول", "📊 آمار"),
        _row("👥 کاربران", "💬 تنظیم پشتیبانی"),
    ])


def kb_admin_order(order_id: str) -> Keypad:
    return Keypad(rows=[
        _row(f"✅ تایید — {order_id}"),
        _row(f"❌ رد — {order_id}"),
        _row("🔙 بازگشت به پنل"),
    ])


def kb_products_admin(products: dict, page: int = 0) -> Keypad:
    items = list(products.items())
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = items[start:end]
    rows = []
    for pid, p in page_items:
        status = "✅" if p.get("active", True) else "❌"
        rows.append(KeypadRow(buttons=[
            _b(f"{status} {p['name']}"),
            _b(f"🗑 {p['name']}"),
        ]))
    nav = []
    if page > 0:
        nav.append("◀️ قبلی")
    if end < len(items):
        nav.append("▶️ بعدی")
    if nav:
        rows.append(_row(*nav))
    rows.append(_row("🔙 بازگشت به پنل"))
    return Keypad(rows=rows)
