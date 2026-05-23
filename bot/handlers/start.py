from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

from bot.database import get_or_create_user, get_user
from bot.config import NEW_USER_CREDITS

router = Router()


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🤖 Создать бота"), KeyboardButton(text="🔧 Улучшить бота")],
            [KeyboardButton(text="🖥 Хостинг"), KeyboardButton(text="🛒 Купить кредиты")],
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="📋 Мои боты")],
        ],
        resize_keyboard=True,
    )


@router.message(Command("start"))
async def cmd_start(message: Message):
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    is_new = user["credits"] == NEW_USER_CREDITS

    if is_new:
        text = (
            f"Привет, {message.from_user.first_name}! 👋\n\n"
            f"🎁 Тебе начислено <b>{NEW_USER_CREDITS} приветственных кредитов</b>!\n\n"
            f"Я создаю Telegram-ботов по твоему описанию. "
            f"Просто опиши что должен делать бот — ИИ напишет код и задеплоит его на Railway.\n\n"
            f"<b>Что умею:</b>\n"
            f"• Создать бота — 3 кредита\n"
            f"• Добавить функцию — 2 кредита\n"
            f"• Изменить логику — 1 кредит\n"
            f"• Хостинг: 1 час бесплатно, потом от 199 ₽\n\n"
            f"Нажми «🤖 Создать бота» чтобы начать 👇"
        )
    else:
        text = (
            f"С возвращением, {message.from_user.first_name}! 👋\n\n"
            f"💰 Баланс: <b>{user['credits']} кредитов</b>\n\n"
            f"Чем займёмся?"
        )

    await message.answer(text, parse_mode="HTML", reply_markup=main_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 Как пользоваться:\n\n"
        "1. Нажми «🤖 Создать бота» или /create\n"
        "2. Опиши что должен делать бот\n"
        "3. Получи токен в @BotFather\n"
        "4. Придумай имя сервиса\n"
        "5. Бот создан и запущен!\n\n"
        "🕐 Каждый бот работает 1 час бесплатно\n"
        "🖥 Продли хостинг через /hosting\n"
        "🔧 Улучши бота через /improve\n"
        "💰 Кредиты: /balance | Купить: /buy\n\n"
        "<b>Стоимость кредитов:</b>\n"
        "• Создать бота — 3 кред.\n"
        "• Добавить функцию — 2 кред.\n"
        "• Изменить логику — 1 кред.\n"
        "• Полная переработка — 3 кред.",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@router.message(F.text == "📋 Мои боты")
async def btn_my_bots(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала отправь /start")
        return

    from bot.database import get_user_bots
    bots = await get_user_bots(user["id"])

    if not bots:
        await message.answer(
            "У тебя пока нет ботов.\n\nНажми «🤖 Создать бота» чтобы создать первого!",
            reply_markup=main_keyboard(),
        )
        return

    lines = []
    for b in bots:
        until = (b["hosting_until"] or "")[:10] or "—"
        status = "✅ Активен" if b["is_active"] else "⛔ Остановлен"
        lines.append(f"🤖 <b>{b['name']}</b>\n   {status} | до {until}\n   <a href='{b['dashboard_url']}'>Dashboard</a>")

    await message.answer(
        "📋 Твои боты:\n\n" + "\n\n".join(lines),
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=main_keyboard(),
    )
