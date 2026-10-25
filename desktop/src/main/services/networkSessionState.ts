export type NetworkSessionStatus = 'active' | 'completed' | 'failed' | 'stopped'

export function canTransitionNetworkSession(
  current: NetworkSessionStatus,
  next: NetworkSessionStatus
): boolean {
  return current === 'active' && next !== 'active'
}
