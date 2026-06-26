import hashlib
from rubpy.bot.models import Keypad, KeypadRow, Button, ButtonTypeEnum
from rubpy.bot.enums import ChatKeypadTypeEnum

BTE = ButtonTypeEnum
PAGE_SIZE = 5
USERS_PAGE = 12


def _b(text: str) -> Button:
    bid = hashlib.md5(text.encode()).hexdigest()[:8]
    return Button(id=bid, type=BTE.SIMPLE, button_text=text)


def _bi(bid: str, text: str) -> Button:
    return Button(id=bid, type=BTE.SIMPLE, button_text=text)


def _row(*texts) -> KeypadRow:
    return KeypadRow(buttons=[_b(t) for t in texts])


def _irow(*items) -> KeypadRow:
    """ردیف inline — هر آیتم یک tuple (bid, text)"""
    return KeypadRow(buttons=[_bi(bid, text) for bid, text in items])


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
    rows = [_row(f"🔖 {p['name']} — {p['price']:,} تومان") for p in items[start:end]]
    nav = []
    if page > 0: nav.append("◀️ قبلی")
    if end < len(items): nav.append("▶️ بعدی")
    if nav: rows.append(_row(*nav))
    rows.append(_row("🔙 بازگشت"))
    return Keypad(rows=rows)


def kb_cancel() -> Keypad:
    return Keypad(rows=[_row("❌ لغو سفارش")])


def kb_back() -> Keypad:
    return Keypad(rows=[_row("🔙 بازگشت")])


def kb_inline_cancel() -> Keypad:
    return Keypad(rows=[KeypadRow(buttons=[_bi("cancel_order", "❌ لغو سفارش")])])


def kb_inline_support_cancel() -> Keypad:
    return Keypad(rows=[KeypadRow(buttons=[_bi("cancel_support", "❌ لغو")])])


# ── ادمین — کیبورد اصلی ──────────────────────────────────────────────────────

def kb_admin_main() -> Keypad:
    return Keypad(rows=[
        _row("📋 سفارش‌های در انتظار"),
        _row("📦 محصولات", "💳 تنظیم کارت"),
        _row("➕ افزودن محصول", "📊 آمار"),
        _row("👥 کاربران", "💬 تنظیم پشتیبانی"),
        _row("📢 پیام همگانی"),
    ])


# ── ادمین — inline: سفارش ──────────────────────────────────────────────────

def kb_admin_order(order_id: str) -> Keypad:
    return Keypad(rows=[
        _irow((f"confirm:{order_id}", "✅ تایید"), (f"reject:{order_id}", "❌ رد")),
        _irow((f"getreceipt:{order_id}", "🧾 دریافت رسید"),),
    ])


# ── ادمین — inline: محصولات ────────────────────────────────────────────────

def kb_product_card(pid: str, active: bool) -> Keypad:
    icon, lbl = ("🟢", "فعال") if active else ("🔴", "غیرفعال")
    return Keypad(rows=[
        _irow(
            (f"pt:{pid}", f"{icon} {lbl}"),
            (f"pd:{pid}", "🗑 حذف"),
        ),
    ])


def kb_product_del_confirm(pid: str) -> Keypad:
    return Keypad(rows=[
        _irow(
            (f"pdc:{pid}", "✅ بله، حذف شود"),
            ("pp:0", "↩️ انصراف"),
        ),
    ])


def kb_products_nav(page: int, total: int) -> Keypad | None:
    has_prev = page > 0
    has_next = (page + 1) * PAGE_SIZE < total
    btns = []
    if has_prev: btns.append(_bi(f"pp:{page - 1}", f"◀️ قبلی"))
    if has_next: btns.append(_bi(f"pp:{page + 1}", f"▶️ بعدی"))
    if not btns:
        return None
    return Keypad(rows=[KeypadRow(buttons=btns)])


# ── ادمین — inline: کاربران ────────────────────────────────────────────────

def kb_users_nav(page: int, total: int) -> Keypad | None:
    has_prev = page > 0
    has_next = (page + 1) * USERS_PAGE < total
    btns = []
    if has_prev: btns.append(_bi(f"up:{page - 1}", f"◀️ صفحه {page}"))
    if has_next: btns.append(_bi(f"up:{page + 1}", f"▶️ صفحه {page + 2}"))
    if not btns:
        return None
    return Keypad(rows=[KeypadRow(buttons=btns)])


# ── سوپر — inline: مدیریت ادمین‌ها ───────────────────────────────────────────

def kb_admins_list(admins: list) -> Keypad | None:
    if not admins:
        return None
    rows = [
        KeypadRow(buttons=[
            _bi(f"arm:{a}", f"❌ حذف — {a[:16]}…"),
        ])
        for a in admins
    ]
    return Keypad(rows=rows)


# ── سوپر — کیبورد اصلی ────────────────────────────────────────────────────

def kb_super_main() -> Keypad:
    return Keypad(rows=[
        _row("👑 مدیریت ادمین‌ها"),
        _row("📋 سفارش‌های در انتظار", "📊 آمار"),
        _row("📦 محصولات", "💳 تنظیم کارت"),
        _row("➕ افزودن محصول", "👥 کاربران"),
        _row("💬 تنظیم پشتیبانی"),
        _row("📢 پیام همگانی"),
    ])


# ── سوپر — inline: تایید حذف ادمین ──────────────────────────────────────────

def kb_admin_rm_confirm(uid: str) -> Keypad:
    return Keypad(rows=[
        _irow(
            (f"armc:{uid}", "✅ بله، حذف شود"),
            ("adm:list", "↩️ انصراف"),
        ),
    ])


# ── سوپر — inline: تایید افزودن ادمین ────────────────────────────────────────

def kb_admin_add_confirm(uid: str) -> Keypad:
    return Keypad(rows=[
        _irow(
            (f"adda:{uid}", "✅ افزودن"),
            ("adm:list", "↩️ انصراف"),
        ),
    ])
