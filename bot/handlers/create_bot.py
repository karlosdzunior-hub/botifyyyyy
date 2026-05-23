from datetime import datetime, timezone, timedelta

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from bot.services.openai_service import generate_bot_code
from bot.services.railway_service import deploy_bot
from bot.database import get_user, update_credits, save_bot
from bot.config import CREDIT_COSTS, FREE_TRIAL_HOURS

router = Router()


class BotCreation(StatesGroup):
    waiting_description = State()
    waiting_token = State()
    waiting_bot_name = State()


@router.message(Command("create"))
@router.message(F.text == "🤖 Создать бота")
async def cmd_create(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала отправь /start")
        return

    cost = CREDIT_COSTS["create_bot"]
    if user["credits"] < cost:
        await message.answer(
            f"❌ Недостаточно кредитов.\n\n"
            f"Для создания бота нужно <b>{cost} кредита</b>, у тебя <b>{user['credits']}</b>.\n\n"
            f"Пополни баланс через /buy 👇",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Купить кредиты", callback_data="goto_buy")]
            ])
        )
        return

    await state.update_data(user_db_id=user["id"])
    await state.set_state(BotCreation.waiting_description)
    await message.answer(
        f"🤖 Создание нового бота\n\n"
        f"Твой баланс: <b>{user['credits']} кредитов</b> (создание стоит {cost})\n\n"
        f"Опиши что должен делать твой бот:\n\n"
        f"Например:\n"
        f"• «Бот для записи клиентов на стрижку, собирает имя, телефон и дату»\n"
        f"• «Бот-викторина по географии, 10 вопросов с вариантами ответов»\n"
        f"• «Бот для магазина, показывает каталог товаров и принимает заказы»",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(BotCreation.waiting_description)
async def got_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(BotCreation.waiting_token)
    await message.answer(
        "Отлично! Теперь нужен токен для нового бота.\n\n"
        "1. Открой @BotFather в Telegram\n"
        "2. Отправь /newbot\n"
        "3. Придумай имя и username\n"
        "4. Скопируй токен и отправь сюда 👇"
    )


@router.message(BotCreation.waiting_token)
async def got_token(message: Message, state: FSMContext):
    token = message.text.strip()
    if ":" not in token or len(token) < 30:
        await message.answer(
            "❌ Это не похоже на токен. Токен выглядит так: 123456789:AABBccdd...\n\nПопробуй ещё раз 👇"
        )
        return

    await state.update_data(token=token)
    await state.set_state(BotCreation.waiting_bot_name)
    await message.answer(
        "Как назовём сервис? (латиницей, без пробелов)\n\n"
        "Например: my-shop-bot, quiz-bot, booking-bot"
    )


@router.message(BotCreation.waiting_bot_name)
async def got_name(message: Message, state: FSMContext):
    name = message.text.strip().lower().replace(" ", "-")
    data = await state.get_data()
    await state.update_data(name=name)
    await state.clear()

    status_msg = await message.answer(
        f"✅ Запускаю создание бота <b>{name}</b>...\n\n"
        f"⚙️ Генерирую код с помощью ИИ...",
        parse_mode="HTML",
    )

    try:
        code = await generate_bot_code(data["description"])

        await status_msg.edit_text(
            f"✅ Код готов!\n\n🚀 Деплою на Railway...",
            parse_mode="HTML",
        )

        trial_until = (datetime.now(timezone.utc) + timedelta(hours=FREE_TRIAL_HOURS)).isoformat()
        result = await deploy_bot(name, code, data["token"])

        bot_id = await save_bot(
            user_id=data["user_db_id"],
            name=name,
            description=data["description"],
            service_id=result["service_id"],
            dashboard_url=result["dashboard_url"],
            hosting_until=trial_until,
        )

        await update_credits(
            data["user_db_id"],
            -CREDIT_COSTS["create_bot"],
            description=f"Создание бота {name}",
        )

        await status_msg.edit_text(
            f"🎉 Бот <b>{name}</b> создан и запущен!\n\n"
            f"🕐 Бесплатный пробный период: <b>{FREE_TRIAL_HOURS} час</b>\n"
            f"🔗 Dashboard: {result['dashboard_url']}\n\n"
            f"Через 1-2 минуты бот будет готов в Telegram.\n\n"
            f"⚠️ Через {FREE_TRIAL_HOURS} ч. бот остановится — продли хостинг через /hosting",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🖥 Продлить хостинг", callback_data=f"host_bot:{bot_id}")],
                [InlineKeyboardButton(text="🔧 Улучшить бота", callback_data=f"improve_bot:{bot_id}")],
            ])
        )

    except Exception as e:
        await status_msg.edit_text(
            f"❌ Ошибка при создании бота:\n{str(e)}\n\nКредиты не списаны. Попробуй ещё раз /create"
        )
