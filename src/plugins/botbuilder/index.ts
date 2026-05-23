import type { OpenACPPlugin } from '../../core/plugin/types.js'
import { Hook } from '../../core/events.js'
import { BotbuilderStorage } from './storage.js'
import { FlowManager } from './flow/flow-manager.js'
import { createFlowInterceptor } from './middleware/flow-interceptor.js'
import { createBotCommand } from './commands/create.js'
import { improveBotCommand } from './commands/improve.js'
import {
  balanceCommand,
  buyCommand,
  hostingCommand,
  hostingConfirmCommand,
  myBotsCommand,
} from './commands/billing.js'
import type { CoreAccess } from '../../core/plugin/types.js'

export interface LLMConfig {
  provider: string
  apiKey: string
  model?: string
}

export interface RailwayConfig {
  apiToken: string
  projectId: string
}

function createBotbuilderPlugin(): OpenACPPlugin {
  return {
    name: '@openacp/botbuilder',
    version: '1.0.0',
    description: 'AI-powered Telegram bot factory — create and deploy bots from a chat',
    essential: false,
    permissions: [
      'storage:read',
      'storage:write',
      'middleware:register',
      'commands:register',
      'kernel:access',
    ],

    async install(ctx) {
      await ctx.settings.setAll({
        llmProvider:    'groq',
        llmApiKey:      '',
        llmModel:       '',
        railwayToken:   '',
        railwayProject: '',
        yoomoneyWallet: '',
      })
      ctx.terminal.log.success('BotBuilder defaults saved')
    },

    async configure(ctx) {
      const { terminal, settings } = ctx
      const current = await settings.getAll()

      const field = await terminal.select({
        message: 'What to configure?',
        options: [
          { value: 'llmProvider',    label: `LLM Provider (current: ${current.llmProvider ?? 'groq'})` },
          { value: 'llmApiKey',      label: 'LLM API Key' },
          { value: 'llmModel',       label: `LLM Model (current: ${current.llmModel || 'default'})` },
          { value: 'railwayToken',   label: 'Railway API Token' },
          { value: 'railwayProject', label: 'Railway Project ID' },
          { value: 'yoomoneyWallet', label: 'YooMoney Wallet Number' },
          { value: 'done',           label: 'Done' },
        ],
      })

      if (field === 'done') return

      if (field === 'llmProvider') {
        const provider = await terminal.select({
          message: 'Select LLM provider:',
          options: [
            { value: 'groq',   label: 'Groq (free, fast)' },
            { value: 'openai', label: 'OpenAI (GPT-4o)' },
            { value: 'qwen',   label: 'Qwen (Alibaba)' },
          ],
        })
        await settings.set('llmProvider', provider)
        terminal.log.success(`LLM provider set to ${provider}`)
        return
      }

      const value = await terminal.text({
        message: `Enter value for ${field}:`,
        defaultValue: String(current[field] ?? ''),
      })
      await settings.set(field, value)
      terminal.log.success(`${field} updated`)
    },

    async setup(ctx) {
      const s = await ctx.settings.getAll()

      const llmCfg: LLMConfig = {
        provider: String(s.llmProvider ?? 'groq'),
        apiKey:   String(s.llmApiKey   ?? process.env.LLM_API_KEY ?? ''),
        model:    s.llmModel ? String(s.llmModel) : undefined,
      }

      const railwayCfg: RailwayConfig = {
        apiToken:  String(s.railwayToken   ?? process.env.RAILWAY_API_TOKEN   ?? ''),
        projectId: String(s.railwayProject ?? process.env.RAILWAY_PROJECT_ID  ?? ''),
      }

      const yoomoneyWallet = String(s.yoomoneyWallet ?? process.env.YOOMONEY_WALLET ?? '')

      const storage     = new BotbuilderStorage(ctx.storage)
      const flowManager = new FlowManager(storage, llmCfg, railwayCfg)

      let coreRef: CoreAccess | undefined

      ctx.registerMiddleware(Hook.MESSAGE_INCOMING, {
        priority: 150,
        handler: createFlowInterceptor(flowManager, () => coreRef!),
      })

      ctx.registerCommand(createBotCommand(flowManager))
      ctx.registerCommand(improveBotCommand(flowManager, storage))
      ctx.registerCommand(balanceCommand(storage))
      ctx.registerCommand(buyCommand(yoomoneyWallet))
      ctx.registerCommand(hostingCommand(storage, yoomoneyWallet))
      ctx.registerCommand(hostingConfirmCommand(storage))
      ctx.registerCommand(myBotsCommand(storage))

      ctx.on('plugin:loaded', () => {
        coreRef = ctx.core as CoreAccess
      })

      coreRef = ctx.core as CoreAccess

      ctx.log.info('BotBuilder plugin ready — commands: /create-bot /improve-bot /balance /buy /hosting /my-bots')
    },
  }
}

export default createBotbuilderPlugin()
