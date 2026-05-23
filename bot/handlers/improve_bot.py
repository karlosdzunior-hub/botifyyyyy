from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from bot.database import get_user, get_user_bots, get_bot, update_credits
from bot.services.openai_service import generate_bot_code
from bot.services.railway_service import deploy_bot
from bot.config import CREDIT_COSTS

router = Router()


class ImprovementType:
    ADD_FEATURE = "add_feature"
    CHANGE_LOGIC = "change_logic"
    FULL_REWORK = "full_rework"


IMPROVEMENT_LABELS = {
    ImprovementType.ADD_FEATURE: ("➕ Добавить функцию", 2),
    ImprovementType.CHANGE_LOGIC: ("✏️ Изменить логику", 1),
    ImprovementType.FULL_REWORK: ("🔄 Полная переработка", 3),
}


class ImproveState(StatesGroup):
    choosing_bot = State()
    choosing_type = State()
    waiting_prompt = State()
    confirming = State()


def bots_keyboard(bots: list):
    buttons = [
        [InlineKeyboardButton(text=f"🤖 {b['name']}", callback_data=f"improve_bot:{b['id']}")]
        for b in bots
    ]
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="improve_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def improvement_keyboard(bot_id: int, user_credits: int):
    buttons = []
    for key, (label, cost) in IMPROVEMENT_LABELS.items():
        enough = "✅" if user_credits >= cost else "❌"
        buttons.append([
            InlineKeyboardButton(
                text=f"{enough} {label} — {cost} кред.",
                callback_data=f"improve_type:{bot_id}:{key}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="improve_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("improve"))
@router.message(F.text == "🔧 Улучшить бота")
async def cmd_improve(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала отправь /start")
        return

    bots = await get_user_bots(user["id"])
    if not bots:
        await message.answer("У тебя пока нет ботов. Создай первого через /create")
        return

    await state.set_state(ImproveState.choosing_bot)
    await state.update_data(user_id=user["id"], user_credits=user["credits"])
    await message.answer(
        f"🔧 Улучшение бота\n\n"
        f"Твой баланс: <b>{user['credits']} кредитов</b>\n\n"
        f"Выбери бота который хочешь улучшить:",
        parse_mode="HTML",
        reply_markup=bots_keyboard(bots)
    )


@router.callback_query(F.data.startswith("improve_bot:"))
async def cb_choose_bot(callback: CallbackQuery, state: FSMContext):
    bot_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    user_credits = data.get("user_credits", 0)

    await state.update_data(bot_id=bot_id)
    await state.set_state(ImproveState.choosing_type)
    await callback.message.edit_text(
        f"Выбери тип улучшения:\n\n"
        f"Твой баланс: <b>{user_credits} кредитов</b>",
        parse_mode="HTML",
        reply_markup=improvement_keyboard(bot_id, user_credits)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("improve_type:"))
async def cb_choose_type(callback: CallbackQuery, state: FSMContext):
    _, bot_id, improve_type = callback.data.split(":")
    data = await state.get_data()
    user_credits = data.get("user_credits", 0)
    cost = CREDIT_COSTS[improve_type]

    if user_credits < cost:
        await callback.answer(f"Недостаточно кредитов. Нужно {cost}, есть {user_credits}", show_alert=True)
        return

    label, _ = IMPROVEMENT_LABELS[improve_type]
    await state.update_data(improve_type=improve_type, cost=cost)
    await state.set_state(ImproveState.waiting_prompt)
    await callback.message.edit_text(
        f"Тип улучшения: <b>{label}</b> (стоит {cost} кред.)\n\n"
        f"Опиши что именно нужно изменить или добавить 👇",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(ImproveState.waiting_prompt)
async def got_improvement_prompt(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(prompt=message.text)
    await state.set_state(ImproveState.confirming)

    label, cost = IMPROVEMENT_LABELS[data["improve_type"]]
    await message.answer(
        f"Подтверди улучшение:\n\n"
        f"Тип: <b>{label}</b>\n"
        f"Описание: {message.text[:300]}\n"
        f"Стоимость: <b>{cost} кредита</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="improve_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="improve_cancel")],
        ])
    )


@router.callback_query(F.data == "improve_confirm")
async def cb_improve_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data["user_id"]
    cost = data["cost"]

    await state.clear()
    await callback.message.edit_text("⚙️ Генерирую улучшенную версию бота...")

    try:
        prompt = f"Улучши существующего бота: {data['prompt']}"
        code = await generate_bot_code(prompt)
        bot_data = await get_bot(data["bot_id"], user_id)
        result = await deploy_bot(bot_data["name"] + "-v2", code, "BOT_TOKEN_PLACEHOLDER")

        await update_credits(user_id, -cost, f"Улучшение бота: {IMPROVEMENT_LABELS[data['improve_type']][0]}")

        await callback.message.edit_text(
            f"✅ Бот улучшен!\n\n"
            f"🔗 Dashboard: {result['dashboard_url']}\n\n"
            f"Не забудь обновить токен в переменных Railway.",
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {str(e)}\n\nПопробуй ещё раз /improve")

    await callback.answer()


@router.callback_query(F.data == "improve_cancel")
async def cb_improve_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer("Отменено")
