import type { BotbuilderStorage } from '../storage.js'
import type { RailwayConfig } from '../index.js'
import type { IChannelAdapter } from '../../../core/channel.js'
import type { NotificationMessage } from '../../../core/types.js'
import { stopService } from '../services/railway.js'
import { createChildLogger } from '../../../core/utils/log.js'

const log = createChildLogger({ module: 'botbuilder-watchdog' })

const WARN_BEFORE_MS  = 24 * 60 * 60 * 1000  // 24 hours
const CHECK_EVERY_MS  = 60 * 60 * 1000         // 1 hour

export class HostingWatchdog {
  private timer: ReturnType<typeof setInterval> | undefined

  constructor(
    private readonly storage: BotbuilderStorage,
    private readonly railwayCfg: RailwayConfig,
    private readonly getAdapters: () => Map<string, IChannelAdapter>,
  ) {}

  start(): void {
    // Run immediately on start, then every hour
    void this.tick()
    this.timer = setInterval(() => void this.tick(), CHECK_EVERY_MS)
    log.info('Hosting watchdog started (checks every hour)')
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = undefined
      log.info('Hosting watchdog stopped')
    }
  }

  private async tick(): Promise<void> {
    try {
      const bots = await this.storage.getAllActiveBots()
      const now  = Date.now()

      for (const bot of bots) {
        if (!bot.hostingUntil) continue

        const expiresAt = new Date(bot.hostingUntil).getTime()
        const msLeft    = expiresAt - now

        if (msLeft <= 0) {
          // Hosting expired — stop the bot and notify
          await this.handleExpired(bot.userId, bot.channelId, bot.id, bot.name, bot.serviceId)
        } else if (msLeft <= WARN_BEFORE_MS && !bot.warnedAt) {
          // Expires within 24h and not yet warned
          await this.handleWarning(bot.userId, bot.channelId, bot.id, bot.name, msLeft)
        }
      }
    } catch (err) {
      log.error({ err }, 'Watchdog tick error')
    }
  }

  private async handleExpired(
    userId: string,
    channelId: string,
    botId: string,
    botName: string,
    serviceId: string,
  ): Promise<void> {
    try {
      log.info({ botId, botName }, 'Stopping expired bot on Railway')
      await stopService(this.railwayCfg, serviceId)
    } catch (err) {
      log.warn({ err, botId }, 'Failed to stop service on Railway')
    }

    await this.storage.updateBot(userId, botId, { isActive: false })

    await this.notify(
      channelId,
      userId,
      `⛔ Бот <b>${botName}</b> остановлен — оплаченный период закончился.\n\n` +
      `Продли хостинг чтобы запустить снова:\n` +
      `/hosting ${botId} week — 199 ₽ / 1 неделя\n` +
      `/hosting ${botId} month — 590 ₽ / 1 месяц\n` +
      `/hosting ${botId} year — 3990 ₽ / 1 год`,
    )

    log.info({ botId, botName, userId }, 'Bot stopped and user notified')
  }

  private async handleWarning(
    userId: string,
    channelId: string,
    botId: string,
    botName: string,
    msLeft: number,
  ): Promise<void> {
    const hoursLeft = Math.ceil(msLeft / (60 * 60 * 1000))

    await this.notify(
      channelId,
      userId,
      `⚠️ Бот <b>${botName}</b> остановится через <b>${hoursLeft} ч.</b>\n\n` +
      `Продли хостинг прямо сейчас:\n` +
      `/hosting ${botId} week — 199 ₽ / 1 неделя\n` +
      `/hosting ${botId} month — 590 ₽ / 1 месяц\n` +
      `/hosting ${botId} year — 3990 ₽ / 1 год`,
    )

    await this.storage.updateBot(userId, botId, { warnedAt: new Date().toISOString() })

    log.info({ botId, botName, userId, hoursLeft }, 'Sent hosting expiry warning')
  }

  private async notify(channelId: string, platformId: string, text: string): Promise<void> {
    const adapter = this.getAdapters().get(channelId)
    if (!adapter?.sendUserNotification) {
      log.warn({ channelId, platformId }, 'No adapter found for user notification')
      return
    }

    const message: NotificationMessage = { text, parseMode: 'HTML' }
    await adapter.sendUserNotification(platformId, message)
  }
}
