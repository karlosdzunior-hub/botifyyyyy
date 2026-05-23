import type { CommandDef } from '../../../core/plugin/types.js'
import type { FlowManager } from '../flow/flow-manager.js'

export function createBotCommand(flowManager: FlowManager): CommandDef {
  return {
    name: 'create-bot',
    description: 'Создать нового Telegram-бота с помощью ИИ',
    category: 'plugin',
    async handler(args) {
      const text = await flowManager.startCreateFlow(args.channelId, args.userId)
      return { type: 'adaptive', fallback: text, variants: { telegram: { text, parse_mode: 'HTML' } } }
    },
  }
}
