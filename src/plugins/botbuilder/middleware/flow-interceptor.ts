import type { MiddlewareFn, MiddlewarePayloadMap } from '../../../core/plugin/types.js'
import type { FlowManager } from '../flow/flow-manager.js'
import type { CoreAccess } from '../../../core/plugin/types.js'

type IncomingPayload = MiddlewarePayloadMap['message:incoming']

export function createFlowInterceptor(
  flowManager: FlowManager,
  getCoreAccess: () => CoreAccess,
): MiddlewareFn<IncomingPayload> {
  return async (payload, next) => {
    const { channelId, threadId, userId, text } = payload

    const core = getCoreAccess()
    const adapter = core.adapters.get(channelId)
    if (!adapter) return next()

    const handled = await flowManager.handleFlowMessage(channelId, threadId, userId, text, adapter)
    if (handled) return null

    return next()
  }
}
