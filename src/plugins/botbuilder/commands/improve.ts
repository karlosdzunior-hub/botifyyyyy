import type { CommandDef } from '../../../core/plugin/types.js'
import type { FlowManager } from '../flow/flow-manager.js'
import type { BotbuilderStorage } from '../storage.js'

export function improveBotCommand(flowManager: FlowManager, storage: BotbuilderStorage): CommandDef {
  return {
    name: 'improve-bot',
    description: 'Улучшить существующего бота за кредиты',
    usage: '<bot-id>',
    category: 'plugin',
    async handler(args) {
      const botId = args.raw.trim()
      if (!botId) {
        const bots = await storage.getUserBots(args.userId)
        if (!bots.length) {
          return { type: 'text', text: 'У тебя пока нет ботов. Создай первого: /create-bot' }
        }
        const list = bots
          .map((b) => `• <b>${b.name}</b> — /improve-bot ${b.id}`)
          .join('\n')
        return {
          type: 'adaptive',
          fallback: `Укажи ID бота: /improve-bot <id>\n\nТвои боты:\n${bots.map((b) => `• ${b.name} — /improve-bot ${b.id}`).join('\n')}`,
          variants: { telegram: { text: `Твои боты:\n${list}\n\nОтправь /improve-bot &lt;id&gt;`, parse_mode: 'HTML' } },
        }
      }

      const text = await flowManager.startImproveFlow(args.channelId, args.userId, botId)
      return { type: 'adaptive', fallback: text, variants: { telegram: { text, parse_mode: 'HTML' } } }
    },
  }
}
