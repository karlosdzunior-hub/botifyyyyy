from aiogram import Bot
from aiogram.types import LabeledPrice


async def send_credits_invoice(bot: Bot, chat_id: int, pack_key: str):
    from bot.config import CREDIT_PACKS
    pack = CREDIT_PACKS[pack_key]
    await bot.send_invoice(
        chat_id=chat_id,
        title=f"Кредиты: {pack['label']}",
        description=f"{pack['credits']} кредитов для создания и улучшения ботов",
        payload=f"credits:{pack_key}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=pack["label"], amount=pack["stars"])],
    )


async def send_hosting_invoice(bot: Bot, chat_id: int, plan_key: str, bot_id: int):
    from bot.config import HOSTING_PLANS
    plan = HOSTING_PLANS[plan_key]
    await bot.send_invoice(
        chat_id=chat_id,
        title=f"Хостинг: {plan['label']}",
        description=f"Хостинг бота на {plan['label'].lower()}",
        payload=f"hosting:{plan_key}:{bot_id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=plan["label"], amount=plan["stars"])],
    )
