from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    PreCheckoutQuery, ReplyKeyboardRemove
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.config import CREDIT_PACKS, HOSTING_PLANS
from bot.database import get_user, get_user_bots, extend_hosting, update_credits

router = Router()


def credits_keyboard():
    buttons = []
    for key, pack in CREDIT_PACKS.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{pack['label']} — {pack['credits']} кред. | {pack['price_rub']} ₽ или {pack['stars']} ⭐",
                callback_data=f"buy_credits:{key}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def payment_method_keyboard(payload: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"pay_stars:{payload}")],
        [InlineKeyboardButton(text="💳 ЮMoney", callback_data=f"pay_yoomoney:{payload}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="pay_cancel")],
    ])


def hosting_keyboard(bots: list):
    buttons = []
    for bot_item in bots:
        buttons.append([
            InlineKeyboardButton(
                text=f"🤖 {bot_item['name']}",
                callback_data=f"host_bot:{bot_item['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="pay_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def hosting_plans_keyboard(bot_id: int):
    buttons = []
    for key, plan in HOSTING_PLANS.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{plan['label']} — {plan['price_rub']} ₽ или {plan['stars']} ⭐",
                callback_data=f"buy_hosting:{key}:{bot_id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="show_hosting")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("balance"))
@router.message(F.text == "💰 Баланс")
async def cmd_balance(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала отправь /start")
        return
    await message.answer(
        f"💰 Твой баланс: <b>{user['credits']} кредитов</b>\n\n"
        f"Кредиты используются для создания и улучшения ботов.\n"
        f"Хостинг оплачивается отдельно.",
        parse_mode="HTML"
    )


@router.message(Command("buy"))
@router.message(F.text == "🛒 Купить кредиты")
async def cmd_buy_credits(message: Message):
    await message.answer(
        "💳 Выбери пакет кредитов:\n\n"
        "🎁 <b>Новым пользователям</b> — 10 кредитов бесплатно при регистрации\n\n"
        "Кредиты нужны для:\n"
        "• Создать бота — 3 кредита\n"
        "• Добавить функцию — 2 кредита\n"
        "• Изменить логику — 1 кредит\n"
        "• Полная переработка — 3 кредита",
        parse_mode="HTML",
        reply_markup=credits_keyboard()
    )


@router.message(Command("hosting"))
@router.message(F.text == "🖥 Хостинг")
async def cmd_hosting(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала отправь /start")
        return

    bots = await get_user_bots(user["id"])
    if not bots:
        await message.answer("У тебя пока нет созданных ботов. Используй /create чтобы создать первого.")
        return

    lines = []
    for b in bots:
        until = b["hosting_until"] or "—"
        if until != "—":
            until = until[:10]
        status = "✅" if b["is_active"] else "⛔"
        lines.append(f"{status} <b>{b['name']}</b> — до {until}")

    await message.answer(
        "🖥 Твои боты:\n\n" + "\n".join(lines) + "\n\nВыбери бота для продления хостинга:",
        parse_mode="HTML",
        reply_markup=hosting_keyboard(bots)
    )


@router.callback_query(F.data == "show_hosting")
async def cb_show_hosting(callback: CallbackQuery):
    await callback.message.delete()
    await cmd_hosting(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("host_bot:"))
async def cb_host_bot(callback: CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "Выбери период хостинга:",
        reply_markup=hosting_plans_keyboard(bot_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_credits:"))
async def cb_buy_credits(callback: CallbackQuery):
    pack_key = callback.data.split(":")[1]
    pack = CREDIT_PACKS[pack_key]
    await callback.message.edit_text(
        f"Пакет <b>{pack['label']}</b>: {pack['credits']} кредитов\n\n"
        f"Выбери способ оплаты:",
        parse_mode="HTML",
        reply_markup=payment_method_keyboard(f"credits:{pack_key}")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_hosting:"))
async def cb_buy_hosting(callback: CallbackQuery):
    _, plan_key, bot_id = callback.data.split(":")
    plan = HOSTING_PLANS[plan_key]
    await callback.message.edit_text(
        f"Хостинг <b>{plan['label']}</b>: {plan['price_rub']} ₽\n\n"
        f"Выбери способ оплаты:",
        parse_mode="HTML",
        reply_markup=payment_method_keyboard(f"hosting:{plan_key}:{bot_id}")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_stars:"))
async def cb_pay_stars(callback: CallbackQuery, bot: Bot):
    payload = callback.data[len("pay_stars:"):]
    parts = payload.split(":")

    if parts[0] == "credits":
        from bot.services.payments.telegram_stars import send_credits_invoice
        await send_credits_invoice(bot, callback.from_user.id, parts[1])
    elif parts[0] == "hosting":
        from bot.services.payments.telegram_stars import send_hosting_invoice
        await send_hosting_invoice(bot, callback.from_user.id, parts[1], int(parts[2]))

    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("pay_yoomoney:"))
async def cb_pay_yoomoney(callback: CallbackQuery):
    payload = callback.data[len("pay_yoomoney:"):]
    parts = payload.split(":")
    user = await get_user(callback.from_user.id)

    if parts[0] == "credits":
        from bot.services.payments.yoomoney import make_credits_link
        link, label = make_credits_link(user["id"], parts[1])
        pack = CREDIT_PACKS[parts[1]]
        text = (
            f"💳 Оплата через ЮMoney\n\n"
            f"Пакет: {pack['label']} ({pack['credits']} кредитов)\n"
            f"Сумма: {pack['price_rub']} ₽\n\n"
            f"После оплаты кредиты начислятся автоматически.\n\n"
            f"👉 <a href='{link}'>Оплатить</a>"
        )
    elif parts[0] == "hosting":
        from bot.services.payments.yoomoney import make_hosting_link
        link, label = make_hosting_link(user["id"], parts[1], int(parts[2]))
        plan = HOSTING_PLANS[parts[1]]
        text = (
            f"💳 Оплата через ЮMoney\n\n"
            f"Хостинг: {plan['label']}\n"
            f"Сумма: {plan['price_rub']} ₽\n\n"
            f"После оплаты хостинг активируется автоматически.\n\n"
            f"👉 <a href='{link}'>Оплатить</a>"
        )
    else:
        await callback.answer("Ошибка")
        return

    await callback.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()


@router.callback_query(F.data == "pay_cancel")
async def cb_pay_cancel(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Отменено")


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    parts = payload.split(":")
    user = await get_user(message.from_user.id)

    if parts[0] == "credits":
        from bot.config import CREDIT_PACKS
        pack = CREDIT_PACKS[parts[1]]
        await update_credits(
            user["id"], pack["credits"],
            description=f"Покупка пакета {pack['label']}",
            payment_method="telegram_stars",
            amount_rub=0
        )
        await message.answer(
            f"✅ Оплата прошла! Начислено <b>{pack['credits']} кредитов</b>.\n\n"
            f"Используй /create чтобы создать нового бота.",
            parse_mode="HTML"
        )

    elif parts[0] == "hosting":
        from bot.config import HOSTING_PLANS
        plan = HOSTING_PLANS[parts[1]]
        bot_id = int(parts[2])
        new_until = await extend_hosting(bot_id, plan["days"])
        await message.answer(
            f"✅ Хостинг оплачен! Бот будет работать до <b>{new_until[:10]}</b>.",
            parse_mode="HTML"
        )
