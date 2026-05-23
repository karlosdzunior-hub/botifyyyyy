export const NEW_USER_CREDITS = 10

export const CREDIT_COSTS = {
  create_bot: 3,
  add_feature: 2,
  change_logic: 1,
  full_rework: 3,
} as const

export const CREDIT_PACKS = {
  start:    { credits: 10,  price_rub: 199,  stars: 220,  label: 'Старт' },
  standard: { credits: 30,  price_rub: 499,  stars: 550,  label: 'Стандарт' },
  pro:      { credits: 100, price_rub: 1290, stars: 1430, label: 'Про' },
} as const

export const HOSTING_PLANS = {
  week:  { days: 7,   price_rub: 199,  stars: 220,  label: '1 неделя' },
  month: { days: 30,  price_rub: 590,  stars: 655,  label: '1 месяц' },
  year:  { days: 365, price_rub: 3990, stars: 4430, label: '1 год' },
} as const

export type CreditPackKey  = keyof typeof CREDIT_PACKS
export type HostingPlanKey = keyof typeof HOSTING_PLANS
export type ImprovementKey = keyof typeof CREDIT_COSTS

export const FREE_TRIAL_HOURS = 1

export const LLM_SYSTEM_PROMPT = `Ты — эксперт по созданию Telegram-ботов на Python.
Пользователь опишет что должен делать бот, а ты напишешь полный рабочий код.

Правила:
1. Используй библиотеку python-telegram-bot==20.7 (asyncio-based)
2. Токен бота читай из переменной окружения BOT_TOKEN
3. Код должен быть полным и готовым к запуску без изменений
4. Не используй webhook — только polling (run_polling())
5. Добавь обработку /start и /help команд
6. Пиши только код без объяснений — всё в одном файле main.py
7. В конце файла должен быть блок:
   if __name__ == "__main__":
       import asyncio
       asyncio.run(main())`
