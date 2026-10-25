import type { NetworkSession } from '../../shared/types'

export function isNetworkSessionExpired(
  session: Pick<NetworkSession, 'status' | 'startedAt' | 'endedAt'>,
  retentionMinutes: number,
  now = Date.now()
): boolean {
  if (session.status === 'active') return false
  const endedAt = Date.parse(session.endedAt ?? session.startedAt)
  return Number.isFinite(endedAt) && now - endedAt >= retentionMinutes * 60_000
}
