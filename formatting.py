def copyable(value, fallback="—") -> str:
    """Format a dynamic value with Rubika's tap-to-copy syntax."""
    if value is None or value == "":
        value = fallback
    return f"`{str(value).replace('`', 'ˋ')}`"


def copyable_money(value) -> str:
    try:
        amount = f"{int(value):,}"
    except (TypeError, ValueError):
        amount = str(value or 0)
    return f"{copyable(amount)} تومان"
