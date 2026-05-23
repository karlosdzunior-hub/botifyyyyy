import type { CommandDef } from '../../../core/plugin/types.js'
import type { BotbuilderStorage } from '../storage.js'
import { CREDIT_PACKS, HOSTING_PLANS } from '../config.js'
import type { CreditPackKey, HostingPlanKey } from '../config.js'

function yoomoneyLink(wallet: string, amount: number, label: string, comment: string): string {
  const params = new URLSearchParams({
    receiver: wallet,
    'quickpay-form': 'button',
    paymentType: 'AC',
    sum: String(amount),
    label,
    comment,
  })
  return `https://yoomoney.ru/quickpay/confirm.xml?${params}`
}

export function balanceCommand(storage: BotbuilderStorage): CommandDef {
  return {
    name: 'balance',
    description: 'Показать баланс кредитов',
    category: 'plugin',
    async handler(args) {
      const user = await storage.getOrCreateUser(args.channelId, args.userId)
      const text = `💰 Твой баланс: <b>${user.credits} кредитов</b>\n\nКредиты используются для создания и улучшения ботов.`
      return { type: 'adaptive', fallback: `💰 Баланс: ${user.credits} кредитов`, variants: { telegram: { text, parse_mode: 'HTML' } } }
    },
  }
}

export function buyCommand(yoomoneyWallet: string): CommandDef {
  return {
    name: 'buy',
    description: 'Купить пакет кредитов',
    usage: '[start|standard|pro]',
    category: 'plugin',
    async handler(args) {
      const packKey = args.raw.trim().toLowerCase() as CreditPackKey
      const pack = CREDIT_PACKS[packKey]

      if (!pack) {
        const lines = Object.entries(CREDIT_PACKS).map(([k, p]) =>
          `• <b>${p.label}</b> — ${p.credits} кред. за ${p.price_rub} ₽ / ${p.stars} ⭐\n  /buy ${k}`,
        )
        const text = `💳 <b>Пакеты кредитов:</b>\n\n${lines.join('\n\n')}\n\n🎁 Новым пользователям — 10 кредитов бесплатно`
        return { type: 'adaptive', fallback: text, variants: { telegram: { text, parse_mode: 'HTML' } } }
      }

      const label = `credits_${packKey}_${args.userId}_${Date.now()}`
      const link  = yoomoneyLink(yoomoneyWallet, pack.price_rub, label, `Кредиты ${pack.label}`)

      const text = (
        `💳 <b>Пакет "${pack.label}"</b> — ${pack.credits} кредитов\n\n` +
        `Способ оплаты:\n` +
        `⭐ <b>Telegram Stars:</b> ${pack.stars} звёзд (в разработке)\n` +
        `💳 <b>ЮMoney:</b> ${pack.price_rub} ₽ → <a href="${link}">Оплатить</a>`
      )
      return { type: 'adaptive', fallback: text, variants: { telegram: { text, parse_mode: 'HTML', disable_web_page_preview: true } } }
    },
  }
}

export function hostingCommand(storage: BotbuilderStorage, yoomoneyWallet: string): CommandDef {
  return {
    name: 'hosting',
    description: 'Продлить хостинг бота',
    usage: '[bot-id] [week|month|year]',
    category: 'plugin',
    async handler(args) {
      const parts   = args.raw.trim().split(/\s+/)
      const botId   = parts[0]
      const planKey = (parts[1] ?? '') as HostingPlanKey

      if (!botId) {
        const bots = await storage.getUserBots(args.userId)
        if (!bots.length) return { type: 'text', text: 'У тебя нет ботов. Создай: /create-bot' }

        const lines = bots.map((b) => {
          const until  = b.hostingUntil ? b.hostingUntil.slice(0, 10) : '—'
          const status = b.isActive ? '✅' : '⛔'
          return `${status} <b>${b.name}</b> — до ${until}\n  /hosting ${b.id} week | month | year`
        })
        const text = `🖥 <b>Твои боты:</b>\n\n${lines.join('\n\n')}`
        return { type: 'adaptive', fallback: text, variants: { telegram: { text, parse_mode: 'HTML' } } }
      }

      const plan = HOSTING_PLANS[planKey]
      if (!plan) {
        const opts = Object.entries(HOSTING_PLANS)
          .map(([k, p]) => `• ${p.label} — ${p.price_rub} ₽ → /hosting ${botId} ${k}`)
          .join('\n')
        const text = `Выбери период хостинга:\n\n${opts}`
        return { type: 'text', text }
      }

      const label = `hosting_${planKey}_${botId}_${Date.now()}`
      const link  = yoomoneyLink(yoomoneyWallet, plan.price_rub, label, `Хостинг ${plan.label}`)

      const text = (
        `🖥 <b>Хостинг "${plan.label}"</b>\n\n` +
        `⭐ Telegram Stars: ${plan.stars} звёзд (в разработке)\n` +
        `💳 ЮMoney: ${plan.price_rub} ₽ → <a href="${link}">Оплатить</a>\n\n` +
        `После оплаты напиши: /hosting-confirm ${botId} ${planKey}`
      )
      return { type: 'adaptive', fallback: text, variants: { telegram: { text, parse_mode: 'HTML', disable_web_page_preview: true } } }
    },
  }
}

export function hostingConfirmCommand(storage: BotbuilderStorage): CommandDef {
  return {
    name: 'hosting-confirm',
    description: 'Подтвердить оплату хостинга (после оплаты ЮMoney)',
    usage: '<bot-id> <week|month|year>',
    category: 'plugin',
    async handler(args) {
      const [botId, planKey] = args.raw.trim().split(/\s+/)
      const plan = HOSTING_PLANS[planKey as HostingPlanKey]
      if (!botId || !plan) return { type: 'error', message: 'Использование: /hosting-confirm <bot-id> <week|month|year>' }

      const newUntil = await storage.extendHosting(args.userId, botId, plan.days)
      const text = `✅ Хостинг продлён до <b>${newUntil.slice(0, 10)}</b>`
      return { type: 'adaptive', fallback: text, variants: { telegram: { text, parse_mode: 'HTML' } } }
    },
  }
}

export function myBotsCommand(storage: BotbuilderStorage): CommandDef {
  return {
    name: 'my-bots',
    description: 'Список всех созданных ботов',
    category: 'plugin',
    async handler(args) {
      const bots = await storage.getUserBots(args.userId)
      if (!bots.length) return { type: 'text', text: 'У тебя пока нет ботов. Создай: /create-bot' }

      const lines = bots.map((b) => {
        const until  = b.hostingUntil ? b.hostingUntil.slice(0, 10) : '—'
        const status = b.isActive ? '✅ Активен' : '⛔ Остановлен'
        return `🤖 <b>${b.name}</b>\n   ${status} | до ${until}\n   <a href="${b.dashboardUrl}">Dashboard</a>`
      })
      const text = `📋 <b>Твои боты:</b>\n\n${lines.join('\n\n')}`
      return { type: 'adaptive', fallback: text, variants: { telegram: { text, parse_mode: 'HTML', disable_web_page_preview: true } } }
    },
  }
}
