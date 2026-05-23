import type { IChannelAdapter, OutgoingMessage } from '../../../core/channel.js'
import type { BotbuilderStorage } from '../storage.js'
import type { FlowState } from '../types.js'
import type { LLMConfig } from '../index.js'
import type { RailwayConfig } from '../index.js'
import { generateBotCode } from '../services/llm.js'
import { deployBot } from '../services/railway.js'
import { CREDIT_COSTS, FREE_TRIAL_HOURS, IMPROVEMENT_LABELS } from '../config.js'
import type { ImprovementType } from '../types.js'

const FLOW_TTL_MS = 10 * 60 * 1000 // 10 minutes

function makeExpiry() {
  return Date.now() + FLOW_TTL_MS
}

export class FlowManager {
  constructor(
    private readonly storage: BotbuilderStorage,
    private readonly llmCfg: LLMConfig,
    private readonly railwayCfg: RailwayConfig,
  ) {}

  async startCreateFlow(channelId: string, userId: string): Promise<string> {
    const user = await this.storage.getOrCreateUser(channelId, userId)
    const cost = CREDIT_COSTS.create_bot

    if (user.credits < cost) {
      return (
        `❌ Недостаточно кредитов.\n\n` +
        `Для создания бота нужно <b>${cost} кредита</b>, у тебя <b>${user.credits}</b>.\n\n` +
        `Пополни баланс: /buy`
      )
    }

    await this.storage.setFlow(channelId, userId, {
      type: 'create',
      step: 'description',
      data: {},
      expiresAt: makeExpiry(),
    })

    return (
      `🤖 <b>Создание нового бота</b>\n\n` +
      `💰 Баланс: <b>${user.credits} кредитов</b> (создание стоит ${cost})\n\n` +
      `Опиши что должен делать твой бот:\n\n` +
      `• «Бот для записи клиентов, собирает имя, телефон и дату»\n` +
      `• «Бот-викторина по географии, 10 вопросов с вариантами»\n` +
      `• «Бот для магазина, каталог товаров и приём заказов»\n\n` +
      `Напиши описание 👇`
    )
  }

  async startImproveFlow(channelId: string, userId: string, botId: string): Promise<string> {
    const user = await this.storage.getOrCreateUser(channelId, userId)

    const improvements = Object.entries(IMPROVEMENT_LABELS)
      .map(([key, label]) => {
        const cost = CREDIT_COSTS[key as ImprovementType]
        const ok = user.credits >= cost ? '✅' : '❌'
        return `${ok} ${label} — ${cost} кред. → /improve-${key}`
      })
      .join('\n')

    await this.storage.setFlow(channelId, userId, {
      type: 'improve',
      step: 'type',
      data: { botId },
      expiresAt: makeExpiry(),
    })

    return (
      `🔧 <b>Улучшение бота</b>\n\n` +
      `💰 Баланс: <b>${user.credits} кредитов</b>\n\n` +
      `Выбери тип улучшения:\n${improvements}\n\n` +
      `Или напиши /cancel чтобы отменить`
    )
  }

  async handleFlowMessage(
    channelId: string,
    threadId: string,
    userId: string,
    text: string,
    adapter: IChannelAdapter,
  ): Promise<boolean> {
    const flow = await this.storage.getFlow(channelId, userId)
    if (!flow) return false

    if (text.trim().toLowerCase() === '/cancel') {
      await this.storage.clearFlow(channelId, userId)
      await this.send(adapter, threadId, '❌ Отменено.')
      return true
    }

    if (flow.type === 'create') {
      await this.handleCreateStep(flow, channelId, threadId, userId, text, adapter)
    } else if (flow.type === 'improve') {
      await this.handleImproveStep(flow, channelId, threadId, userId, text, adapter)
    }

    return true
  }

  private async handleCreateStep(
    flow: FlowState,
    channelId: string,
    threadId: string,
    userId: string,
    text: string,
    adapter: IChannelAdapter,
  ) {
    switch (flow.step) {
      case 'description': {
        flow.data.description = text
        flow.step = 'token'
        flow.expiresAt = makeExpiry()
        await this.storage.setFlow(channelId, userId, flow)
        await this.send(adapter, threadId,
          `Отлично! Теперь нужен токен для нового бота.\n\n` +
          `1. Открой @BotFather в Telegram\n` +
          `2. Отправь /newbot\n` +
          `3. Скопируй токен и отправь сюда 👇`,
        )
        break
      }
      case 'token': {
        const token = text.trim()
        if (!token.includes(':') || token.length < 30) {
          await this.send(adapter, threadId, '❌ Это не похоже на токен. Пример: 123456789:AABBccdd...\n\nПопробуй ещё раз 👇')
          return
        }
        flow.data.token = token
        flow.step = 'name'
        flow.expiresAt = makeExpiry()
        await this.storage.setFlow(channelId, userId, flow)
        await this.send(adapter, threadId, 'Как назовём сервис? (латиницей, без пробелов)\n\nНапример: my-shop-bot, quiz-bot, booking-bot')
        break
      }
      case 'name': {
        const name = text.trim().toLowerCase().replace(/\s+/g, '-')
        await this.storage.clearFlow(channelId, userId)
        await this.send(adapter, threadId, `⚙️ Генерирую код бота <b>${name}</b>...`)
        await this.runDeploy(channelId, threadId, userId, name, flow.data.description, flow.data.token, adapter)
        break
      }
    }
  }

  private async handleImproveStep(
    flow: FlowState,
    channelId: string,
    threadId: string,
    userId: string,
    text: string,
    adapter: IChannelAdapter,
  ) {
    switch (flow.step) {
      case 'type': {
        const typeMap: Record<string, ImprovementType> = {
          '/improve-add_feature':  'add_feature',
          '/improve-change_logic': 'change_logic',
          '/improve-full_rework':  'full_rework',
        }
        const improvType = typeMap[text.trim().toLowerCase()]
        if (!improvType) {
          await this.send(adapter, threadId, 'Выбери тип: /improve-add_feature, /improve-change_logic или /improve-full_rework')
          return
        }
        const user = await this.storage.getOrCreateUser(channelId, userId)
        const cost = CREDIT_COSTS[improvType]
        if (user.credits < cost) {
          await this.send(adapter, threadId, `❌ Нужно ${cost} кредитов, у тебя ${user.credits}. Пополни: /buy`)
          await this.storage.clearFlow(channelId, userId)
          return
        }
        flow.data.improvType = improvType
        flow.step = 'prompt'
        flow.expiresAt = makeExpiry()
        await this.storage.setFlow(channelId, userId, flow)
        await this.send(adapter, threadId, `Опиши что именно нужно ${IMPROVEMENT_LABELS[improvType].toLowerCase()} 👇`)
        break
      }
      case 'prompt': {
        const { botId, improvType } = flow.data
        await this.storage.clearFlow(channelId, userId)

        const bot = await this.storage.getBot(userId, botId)
        if (!bot) {
          await this.send(adapter, threadId, '❌ Бот не найден.')
          return
        }

        const cost = CREDIT_COSTS[improvType as ImprovementType]
        await this.send(adapter, threadId, '⚙️ Генерирую улучшенную версию...')

        try {
          const prompt = `Улучши бота (${IMPROVEMENT_LABELS[improvType as ImprovementType]}): ${text}\n\nОригинальное описание: ${bot.description}`
          const code = await generateBotCode(prompt, this.llmCfg)
          const result = await deployBot(this.railwayCfg, `${bot.name}-v2`, code, 'BOT_TOKEN_PLACEHOLDER')

          await this.storage.updateCredits(channelId, userId, -cost)
          await this.send(adapter, threadId,
            `✅ Бот улучшен!\n\n` +
            `🔗 Dashboard: ${result.dashboardUrl}\n\n` +
            `Не забудь обновить BOT_TOKEN в переменных Railway.`
          )
        } catch (e: unknown) {
          const msg = e instanceof Error ? e.message : String(e)
          await this.send(adapter, threadId, `❌ Ошибка: ${msg}`)
        }
        break
      }
    }
  }

  private async runDeploy(
    channelId: string,
    threadId: string,
    userId: string,
    name: string,
    description: string,
    botToken: string,
    adapter: IChannelAdapter,
  ) {
    try {
      const code = await generateBotCode(description, this.llmCfg)
      await this.send(adapter, threadId, '🚀 Деплою на Railway...')

      const result = await deployBot(this.railwayCfg, name, code, botToken)

      const hostingUntil = new Date(Date.now() + FREE_TRIAL_HOURS * 3600_000).toISOString()
      const bot = await this.storage.saveBot({
        userId,
        name,
        description,
        serviceId:    result.serviceId,
        dashboardUrl: result.dashboardUrl,
        isActive:     true,
        hostingUntil,
      })

      await this.storage.updateCredits(channelId, userId, -CREDIT_COSTS.create_bot)

      await this.send(adapter, threadId,
        `🎉 Бот <b>${name}</b> создан и запущен!\n\n` +
        `🕐 Бесплатный пробный период: <b>${FREE_TRIAL_HOURS} час</b>\n` +
        `🔗 Dashboard: ${result.dashboardUrl}\n\n` +
        `Через 1-2 минуты бот будет готов в Telegram.\n\n` +
        `⚠️ Через ${FREE_TRIAL_HOURS} ч. бот остановится.\n` +
        `Продли хостинг: /hosting ${bot.id}\n` +
        `Улучши бота: /improve-bot ${bot.id}`
      )
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      await this.send(adapter, threadId, `❌ Ошибка при создании бота: ${msg}\n\nКредиты не списаны.`)
    }
  }

  private async send(adapter: IChannelAdapter, threadId: string, text: string) {
    const msg: OutgoingMessage = { type: 'text', text }
    await adapter.sendMessage(threadId, msg)
  }
}
