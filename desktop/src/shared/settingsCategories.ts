export const settingsCategoryIds = [
  'appearance',
  'terminal',
  'workspace',
  'reports',
  'cli-report-colors',
  'network-history',
  'privacy'
] as const

export type SettingsCategoryId = (typeof settingsCategoryIds)[number]

export function normalizeSettingsCategoryOrder(value: unknown): SettingsCategoryId[] {
  const requested = Array.isArray(value)
    ? value.filter(
        (id): id is SettingsCategoryId =>
          typeof id === 'string' && settingsCategoryIds.includes(id as SettingsCategoryId)
      )
    : []
  return [...new Set(requested), ...settingsCategoryIds.filter((id) => !requested.includes(id))]
}
