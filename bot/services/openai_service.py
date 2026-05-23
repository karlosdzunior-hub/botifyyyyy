import os
from openai import AsyncOpenAI

SYSTEM_PROMPT = """Ты — эксперт по созданию Telegram-ботов на Python.
Пользователь опишет что должен делать бот, а ты напишешь полный рабочий код.

Правила:
1. Используй библиотеку python-telegram-bot==20.7 (asyncio-based)
2. Токен бота читай из переменной окружения BOT_TOKEN
3. Код должен быть полным и готовым к запуску
4. Не используй webhook — только polling (run_polling())
5. Добавь обработку /start и /help команд
6. Пиши только код, без объяснений — всё в одном файле main.py
7. В конце файла должен быть блок:
   if __name__ == "__main__":
       import asyncio
       asyncio.run(main())
"""

PROVIDERS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env_key": "QWEN_API_KEY",
        "default_model": "qwen-plus",
    },
}

def get_client():
    provider_name = os.getenv("LLM_PROVIDER", "openai").lower()
    provider = PROVIDERS.get(provider_name, PROVIDERS["openai"])
    api_key = os.getenv(provider["env_key"])
    model = os.getenv("LLM_MODEL", provider["default_model"])
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=provider["base_url"],
    )
    return client, model


async def generate_bot_code(user_description: str) -> str:
    client, model = get_client()
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Создай бота: {user_description}"}
        ],
        temperature=0.2,
    )
    code = response.choices[0].message.content.strip()
    if code.startswith("```python"):
        code = code[9:]
    if code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    return code.strip()
