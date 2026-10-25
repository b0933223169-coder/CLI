export function isCliAccountLoginNewer(sourceLastLogin: unknown, savedTimestamp: number): boolean {
  if (typeof sourceLastLogin !== 'string') return false
  const sourceTimestamp = Date.parse(sourceLastLogin)
  return Number.isFinite(sourceTimestamp) && sourceTimestamp > savedTimestamp
}
