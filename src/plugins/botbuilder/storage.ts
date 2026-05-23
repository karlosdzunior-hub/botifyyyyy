import type { PluginStorage } from '../../core/plugin/types.js'
import type { BotbuilderUser, BotRecord, FlowState } from './types.js'
import { NEW_USER_CREDITS } from './config.js'
import { nanoid } from 'nanoid'

export class BotbuilderStorage {
  constructor(private readonly kv: PluginStorage) {}

  // ─── Users ───

  async getOrCreateUser(channelId: string, userId: string): Promise<BotbuilderUser> {
    const key = `users/${channelId}/${userId}`
    const existing = await this.kv.get<BotbuilderUser>(key)
    if (existing) return existing

    const user: BotbuilderUser = {
      userId,
      channelId,
      credits: NEW_USER_CREDITS,
      createdAt: new Date().toISOString(),
    }
    await this.kv.set(key, user)
    return user
  }

  async getUser(channelId: string, userId: string): Promise<BotbuilderUser | undefined> {
    return this.kv.get<BotbuilderUser>(`users/${channelId}/${userId}`)
  }

  async updateCredits(channelId: string, userId: string, delta: number): Promise<number> {
    const user = await this.getOrCreateUser(channelId, userId)
    const updated = { ...user, credits: user.credits + delta }
    await this.kv.set(`users/${channelId}/${userId}`, updated)
    return updated.credits
  }

  // ─── Bots ───

  async saveBot(bot: Omit<BotRecord, 'id' | 'createdAt'>): Promise<BotRecord> {
    const record: BotRecord = {
      ...bot,
      id: nanoid(),
      createdAt: new Date().toISOString(),
    }
    await this.kv.set(`bots/${record.userId}/${record.id}`, record)
    return record
  }

  async getUserBots(userId: string): Promise<BotRecord[]> {
    const keys = await this.kv.keys(`bots/${userId}/`)
    const bots: BotRecord[] = []
    for (const key of keys) {
      const bot = await this.kv.get<BotRecord>(key)
      if (bot) bots.push(bot)
    }
    return bots.sort((a, b) => b.createdAt.localeCompare(a.createdAt))
  }

  async getBot(userId: string, botId: string): Promise<BotRecord | undefined> {
    return this.kv.get<BotRecord>(`bots/${userId}/${botId}`)
  }

  async extendHosting(userId: string, botId: string, days: number): Promise<string> {
    const bot = await this.getBot(userId, botId)
    if (!bot) throw new Error('Бот не найден')

    const now = new Date()
    const current = bot.hostingUntil ? new Date(bot.hostingUntil) : now
    const base = current > now ? current : now
    base.setDate(base.getDate() + days)
    const newUntil = base.toISOString()

    await this.kv.set(`bots/${userId}/${botId}`, { ...bot, hostingUntil: newUntil, isActive: true })
    return newUntil
  }

  // ─── Flows (multi-step conversation state) ───

  private flowKey(channelId: string, userId: string) {
    return `flow/${channelId}/${userId}`
  }

  async setFlow(channelId: string, userId: string, state: FlowState): Promise<void> {
    await this.kv.set(this.flowKey(channelId, userId), state)
  }

  async getFlow(channelId: string, userId: string): Promise<FlowState | undefined> {
    const state = await this.kv.get<FlowState>(this.flowKey(channelId, userId))
    if (!state) return undefined
    if (Date.now() > state.expiresAt) {
      await this.clearFlow(channelId, userId)
      return undefined
    }
    return state
  }

  async clearFlow(channelId: string, userId: string): Promise<void> {
    await this.kv.delete(this.flowKey(channelId, userId))
  }
}
