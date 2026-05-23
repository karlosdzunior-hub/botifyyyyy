export interface BotbuilderUser {
  userId: string
  channelId: string
  credits: number
  createdAt: string
}

export interface BotRecord {
  id: string
  userId: string
  channelId: string
  name: string
  description: string
  serviceId: string
  dashboardUrl: string
  isActive: boolean
  hostingUntil: string
  /** ISO timestamp of last "expires soon" warning sent to user */
  warnedAt?: string
  createdAt: string
}

export interface FlowState {
  type: 'create' | 'improve'
  step: string
  data: Record<string, string>
  expiresAt: number
}

export type ImprovementType = 'add_feature' | 'change_logic' | 'full_rework'

export const IMPROVEMENT_LABELS: Record<ImprovementType, string> = {
  add_feature:  'Добавить функцию',
  change_logic: 'Изменить логику',
  full_rework:  'Полная переработка',
}
