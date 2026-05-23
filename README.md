# BotBuilder — Telegram бот, который создаёт других ботов

## Как работает

1. Новый пользователь получает **10 бесплатных кредитов**
2. Описывает что должен делать бот (стоит 3 кредита)
3. ИИ генерирует код, проверяет и деплоит на Railway
4. Бот работает **1 час бесплатно** (пробный период)
5. Продлевает хостинг или улучшает бота за кредиты

## Тарифы

### Кредиты (на что тратятся)
| Действие | Кредиты |
|----------|---------|
| Создать бота | 3 |
| Добавить функцию | 2 |
| Изменить логику | 1 |
| Полная переработка | 3 |

### Пакеты кредитов
| Пакет | Кредиты | Цена ₽ | Telegram Stars |
|-------|---------|--------|----------------|
| Старт | 10 | 199 ₽ | 220 ⭐ |
| Стандарт | 30 | 499 ₽ | 550 ⭐ |
| Про | 100 | 1 290 ₽ | 1430 ⭐ |

### Хостинг (за одного бота)
| Период | Цена ₽ | Telegram Stars |
|--------|--------|----------------|
| 1 неделя | 199 ₽ | 220 ⭐ |
| 1 месяц | 590 ₽ | 655 ⭐ |
| 1 год | 3 990 ₽ | 4430 ⭐ |

## Способы оплаты
- **Telegram Stars** — встроенная оплата прямо в Telegram
- **ЮMoney** — ссылка на оплату с автоматическим начислением

## Поддерживаемые ИИ-провайдеры

| Провайдер | LLM_PROVIDER | Модель |
|-----------|-------------|--------|
| Groq (рекомендуется) | `groq` | llama-3.3-70b-versatile |
| OpenAI | `openai` | gpt-4o |
| Qwen | `qwen` | qwen-plus |

## Установка на VPS

### 1. Клонируй репо и установи зависимости
```bash
git clone <your-repo>
cd botbuilder
pip install -r requirements.txt
```

### 2. Создай .env файл
```bash
cp .env.example .env
nano .env
```

### 3. Заполни .env
```env
TELEGRAM_BOT_TOKEN=токен_от_BotFather
LLM_PROVIDER=groq
GROQ_API_KEY=твой_groq_ключ
RAILWAY_API_TOKEN=твой_railway_токен
RAILWAY_PROJECT_ID=id_проекта_в_railway
YOOMONEY_WALLET=номер_кошелька
YOOMONEY_SECRET=секрет_из_настроек_ЮMoney
YOOMONEY_REDIRECT_URL=https://t.me/твой_бот
```

### 4. Запусти
```bash
python -m bot.main
```

### 5. Автозапуск через systemd
```ini
[Unit]
Description=BotBuilder Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/path/to/botbuilder
EnvironmentFile=/path/to/botbuilder/.env
ExecStart=/usr/bin/python3 -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable botbuilder
sudo systemctl start botbuilder
```

## Где взять токены

- **Telegram Bot Token** — @BotFather → /newbot
- **Groq API Key** — https://console.groq.com (бесплатно)
- **Railway API Token** — https://railway.app/account/tokens
- **Railway Project ID** — создай проект, ID в URL
- **ЮMoney** — https://yoomoney.ru/transfer/myservices/http-notification

## Структура проекта

```
botbuilder/
├── bot/
│   ├── config.py               ← тарифы, цены, константы
│   ├── database.py             ← SQLite: пользователи, боты, транзакции
│   ├── handlers/
│   │   ├── start.py            ← /start, /help, меню
│   │   ├── create_bot.py       ← создание бота с проверкой кредитов
│   │   ├── improve_bot.py      ← улучшение бота за кредиты
│   │   └── billing.py         ← покупка кредитов, хостинг, оплата
│   ├── services/
│   │   ├── openai_service.py   ← генерация кода через ИИ
│   │   ├── railway_service.py  ← деплой на Railway
│   │   └── payments/
│   │       ├── telegram_stars.py  ← оплата через Telegram Stars
│   │       └── yoomoney.py        ← оплата через ЮMoney
│   └── main.py
├── requirements.txt
├── .env.example
└── README.md
```
