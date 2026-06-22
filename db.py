import json
import os
import time
import random

DB_FILE = os.environ.get("DATA_FILE", os.path.join(os.path.dirname(__file__), "data.json"))

_default = {
    "orders":   {},   # order_id → {user_id, product_id, status, receipt, voucher_code, created_at}
    "products": {},   # pid → {name, price, description, active}
    "users":    {},   # user_id → {name}
    "admins":   [],
    "settings": {},   # card_number, card_name
}


def _load() -> dict:
    if not os.path.exists(DB_FILE):
        _save(_default.copy())
        return _default.copy()
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get(key: str):
    return _load().get(key, {})


# ── settings ──────────────────────────────────────────────────────────────────

def get_setting(key: str, default=None):
    return _load().get("settings", {}).get(key, default)


def set_setting(key: str, value) -> None:
    data = _load()
    data.setdefault("settings", {})[key] = value
    _save(data)


# ── products ──────────────────────────────────────────────────────────────────

def add_product(pid: str, name: str, price: int, description: str = "") -> None:
    data = _load()
    data["products"][pid] = {"name": name, "price": price, "description": description, "active": True}
    _save(data)


def get_product(pid: str) -> dict | None:
    return _load()["products"].get(pid)


def get_all_products() -> dict:
    return _load()["products"]


def get_active_products() -> dict:
    return {pid: p for pid, p in _load()["products"].items() if p.get("active", True)}


def toggle_product(pid: str) -> bool | None:
    data = _load()
    if pid not in data["products"]:
        return None
    data["products"][pid]["active"] = not data["products"][pid].get("active", True)
    _save(data)
    return data["products"][pid]["active"]


def delete_product(pid: str) -> bool:
    data = _load()
    if pid not in data["products"]:
        return False
    del data["products"][pid]
    _save(data)
    return True


# ── orders ────────────────────────────────────────────────────────────────────

def create_order(user_id: str, product_id: str) -> str:
    data = _load()
    order_id = f"{int(time.time())}_{random.randint(1000, 9999)}"
    data["orders"][order_id] = {
        "user_id":      user_id,
        "product_id":   product_id,
        "status":       "waiting_confirm",
        "receipt":      None,
        "voucher_code": None,
        "created_at":   int(time.time()),
    }
    _save(data)
    return order_id


def get_order(order_id: str) -> dict | None:
    return _load()["orders"].get(order_id)


def update_order(order_id: str, **kwargs) -> None:
    data = _load()
    if order_id in data["orders"]:
        data["orders"][order_id].update(kwargs)
        _save(data)


def get_user_orders(user_id: str) -> list[tuple[str, dict]]:
    return [(oid, o) for oid, o in _load()["orders"].items() if o["user_id"] == user_id]


def get_pending_orders() -> list[tuple[str, dict]]:
    return [(oid, o) for oid, o in _load()["orders"].items() if o["status"] == "waiting_confirm"]


# ── users ─────────────────────────────────────────────────────────────────────

def ensure_user(user_id: str, name: str = "") -> None:
    data = _load()
    if user_id not in data["users"]:
        data["users"][user_id] = {"name": name}
        _save(data)
    elif name and data["users"][user_id].get("name") != name:
        data["users"][user_id]["name"] = name
        _save(data)


def get_user(user_id: str) -> dict | None:
    return _load()["users"].get(user_id)


def get_all_users() -> dict:
    return _load()["users"]


# ── admins ────────────────────────────────────────────────────────────────────

def get_admins() -> set:
    return set(_load().get("admins", []))


def add_admin(user_id: str) -> bool:
    data = _load()
    if user_id in data["admins"]:
        return False
    data["admins"].append(user_id)
    _save(data)
    return True


def remove_admin(user_id: str) -> bool:
    data = _load()
    if user_id not in data["admins"]:
        return False
    data["admins"].remove(user_id)
    _save(data)
    return True
