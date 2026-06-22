"""
مدیریت state کاربران در حافظه
"""

_states: dict[str, dict] = {}
# user_id → {step, data: {...}}


def set_state(user_id: str, step: str, **data) -> None:
    _states[user_id] = {"step": step, "data": data}


def get_state(user_id: str) -> dict | None:
    return _states.get(user_id)


def clear_state(user_id: str) -> None:
    _states.pop(user_id, None)


def get_step(user_id: str) -> str | None:
    s = _states.get(user_id)
    return s["step"] if s else None
