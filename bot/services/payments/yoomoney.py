import os
import hashlib
import hmac
import httpx
import uuid


YOOMONEY_CLIENT_ID = os.getenv("YOOMONEY_CLIENT_ID", "")
YOOMONEY_SECRET = os.getenv("YOOMONEY_SECRET", "")
YOOMONEY_WALLET = os.getenv("YOOMONEY_WALLET", "")
YOOMONEY_REDIRECT_URL = os.getenv("YOOMONEY_REDIRECT_URL", "https://t.me/your_bot")


def create_payment_link(amount: float, label: str, description: str) -> str:
    params = {
        "receiver": YOOMONEY_WALLET,
        "quickpay-form": "button",
        "paymentType": "AC",
        "sum": str(amount),
        "label": label,
        "comment": description,
        "successURL": YOOMONEY_REDIRECT_URL,
    }
    base_url = "https://yoomoney.ru/quickpay/confirm.xml"
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{base_url}?{query}"


def verify_notification(data: dict) -> bool:
    if not YOOMONEY_SECRET:
        return False
    fields = [
        data.get("notification_type", ""),
        data.get("operation_id", ""),
        data.get("amount", ""),
        data.get("currency", ""),
        data.get("datetime", ""),
        data.get("sender", ""),
        data.get("codepro", ""),
        YOOMONEY_SECRET,
        data.get("label", ""),
    ]
    check_string = "&".join(fields)
    expected = hashlib.sha1(check_string.encode("utf-8")).hexdigest()
    return hmac.compare_digest(expected, data.get("sha1_hash", ""))


def generate_label(user_id: int, pack_type: str) -> str:
    return f"{pack_type}_{user_id}_{uuid.uuid4().hex[:8]}"


def make_credits_link(user_id: int, pack_key: str) -> tuple[str, str]:
    from bot.config import CREDIT_PACKS
    pack = CREDIT_PACKS[pack_key]
    label = generate_label(user_id, f"credits_{pack_key}")
    link = create_payment_link(
        amount=pack["price_rub"],
        label=label,
        description=f"Кредиты {pack['label']} — {pack['credits']} кредитов",
    )
    return link, label


def make_hosting_link(user_id: int, plan_key: str, bot_id: int) -> tuple[str, str]:
    from bot.config import HOSTING_PLANS
    plan = HOSTING_PLANS[plan_key]
    label = generate_label(user_id, f"hosting_{plan_key}_{bot_id}")
    link = create_payment_link(
        amount=plan["price_rub"],
        label=label,
        description=f"Хостинг бота {plan['label']}",
    )
    return link, label
