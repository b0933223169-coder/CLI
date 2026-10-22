import type { AppSettings } from './types'

export const defaultCliReportColors = {
  cliReportTitleColor: 'MAGENTA',
  cliReportTitleTextColor: 'WHITE',
  cliReportHeaderColor: 'CYAN',
  cliReportCurrentColor: 'REVERSE',
  cliReportBelowColor: 'RED_BG_WHITE',
  cliReportUrlColor: 'DIM',
  cliReportSeparatorColor: 'DIM'
} as const

export const cliReportColorFields = [
  {
    key: 'title',
    setting: 'cliReportTitleColor',
    label: '標題外框',
    description: '「學習時間」標題框線與裝飾',
    defaultValue: defaultCliReportColors.cliReportTitleColor
  },
  {
    key: 'title_text',
    setting: 'cliReportTitleTextColor',
    label: '標題文字',
    description: '標題及帳號名稱',
    defaultValue: defaultCliReportColors.cliReportTitleTextColor
  },
  {
    key: 'header',
    setting: 'cliReportHeaderColor',
    label: '表頭',
    description: '月份、停留、影片與練習欄位名稱',
    defaultValue: defaultCliReportColors.cliReportHeaderColor
  },
  {
    key: 'cur',
    setting: 'cliReportCurrentColor',
    label: '當月列',
    description: '本月已達標的整列重點標示',
    defaultValue: defaultCliReportColors.cliReportCurrentColor
  },
  {
    key: 'low',
    setting: 'cliReportBelowColor',
    label: '未達標列',
    description: '未達門檻月份的警示文字',
    defaultValue: defaultCliReportColors.cliReportBelowColor
  },
  {
    key: 'url',
    setting: 'cliReportUrlColor',
    label: '網址列',
    description: '報表來源網址與帳號提示',
    defaultValue: defaultCliReportColors.cliReportUrlColor
  },
  {
    key: 'sep',
    setting: 'cliReportSeparatorColor',
    label: '分隔線',
    description: '報表表格的水平分隔線',
    defaultValue: defaultCliReportColors.cliReportSeparatorColor
  }
] as const satisfies ReadonlyArray<{
  key: string
  setting: keyof Pick<
    AppSettings,
    | 'cliReportTitleColor'
    | 'cliReportTitleTextColor'
    | 'cliReportHeaderColor'
    | 'cliReportCurrentColor'
    | 'cliReportBelowColor'
    | 'cliReportUrlColor'
    | 'cliReportSeparatorColor'
  >
  label: string
  description: string
  defaultValue: string
}>

export type CliReportColorSetting = (typeof cliReportColorFields)[number]['setting']
export type CliReportColorValues = Pick<AppSettings, CliReportColorSetting>

export const cliReportColorPresets = [
  'GREEN',
  'RED',
  'YELLOW',
  'BLUE',
  'CYAN',
  'MAGENTA',
  'WHITE',
  'DIM',
  'RESET',
  'RED_BG',
  'RED_BG_WHITE',
  'YELLOW_BG_WHITE',
  'BLUE_BG_WHITE',
  'MAGENTA_BG_WHITE',
  'CYAN_BG_WHITE',
  'GREEN_BG_WHITE',
  'ORANGE',
  'ORANGE_BG',
  'PURPLE',
  'PURPLE_BG',
  'PINK',
  'PINK_BG',
  'LIME',
  'LIME_BG',
  'TEAL',
  'TEAL_BG',
  'GOLD',
  'GOLD_BG',
  'SKY',
  'SKY_BG',
  'BROWN',
  'BROWN_BG',
  'GRAY',
  'GRAY_BG',
  'BLACK',
  'BLACK_BG',
  'REVERSE'
] as const

export const cliIndexedForegroundColors = Array.from(
  { length: 256 },
  (_, index) => `COLOR_${String(index).padStart(3, '0')}`
)
export const cliIndexedBackgroundColors = Array.from(
  { length: 256 },
  (_, index) => `BG_${String(index).padStart(3, '0')}`
)

export const cliColorMappings = [
  ['terminal_cursor_color', 'terminalCursorColor'],
  ['terminal_text_color', 'terminalTextColor'],
  ['terminal_background_color', 'terminalBackgroundColor'],
  ['title', 'cliReportTitleColor'],
  ['title_text', 'cliReportTitleTextColor'],
  ['header', 'cliReportHeaderColor'],
  ['cur', 'cliReportCurrentColor'],
  ['low', 'cliReportBelowColor'],
  ['url', 'cliReportUrlColor'],
  ['sep', 'cliReportSeparatorColor']
] as const satisfies ReadonlyArray<readonly [string, keyof AppSettings]>

export const cliColorSettingKeys = cliColorMappings.map(([, setting]) => setting)

const ansiColorMap: Record<string, string> = {
  GREEN: '#00ff00',
  RED: '#ff0000',
  YELLOW: '#ffff00',
  BLUE: '#0000ff',
  CYAN: '#00ffff',
  MAGENTA: '#ff00ff',
  WHITE: '#ffffff',
  DIM: '#808080',
  RESET: '#d8fff4',
  RED_BG: '#800000',
  RED_BG_WHITE: '#800000',
  YELLOW_BG_WHITE: '#808000',
  BLUE_BG_WHITE: '#000080',
  MAGENTA_BG_WHITE: '#800080',
  CYAN_BG_WHITE: '#008080',
  GREEN_BG_WHITE: '#008000',
  ORANGE: '#ff8700',
  ORANGE_BG: '#ff8700',
  PURPLE: '#af5fff',
  PURPLE_BG: '#af5fff',
  PINK: '#ff87ff',
  PINK_BG: '#ff87ff',
  LIME: '#afff00',
  LIME_BG: '#afff00',
  TEAL: '#00afaf',
  TEAL_BG: '#00afaf',
  GOLD: '#ffd700',
  GOLD_BG: '#ffd700',
  SKY: '#87dfff',
  SKY_BG: '#87dfff',
  BROWN: '#af5f00',
  BROWN_BG: '#af5f00',
  GRAY: '#8b8b8b',
  GRAY_BG: '#8b8b8b',
  BLACK: '#000000',
  BLACK_BG: '#000000'
}

const basicXtermColors = [
  '#000000',
  '#800000',
  '#008000',
  '#808000',
  '#000080',
  '#800080',
  '#008080',
  '#c0c0c0',
  '#808080',
  '#ff0000',
  '#00ff00',
  '#ffff00',
  '#0000ff',
  '#ff00ff',
  '#00ffff',
  '#ffffff'
]

export function normalizeCliColor(value: string): string {
  const normalized = value.trim()
  if (/^#[0-9a-f]{3}$/i.test(normalized)) {
    return `#${normalized
      .slice(1)
      .split('')
      .map((channel) => channel + channel)
      .join('')
      .toLowerCase()}`
  }
  if (/^#[0-9a-f]{6}$/i.test(normalized)) return normalized.toLowerCase()
  if (
    cliReportColorPresets.includes(normalized as (typeof cliReportColorPresets)[number]) ||
    /^COLOR_(?:00[0-9]|0[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$/.test(normalized) ||
    /^BG_(?:00[0-9]|0[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$/.test(normalized)
  ) {
    return normalized
  }
  throw new Error(`不支援的 CLI 報表顏色：${value}`)
}

export function isCliColorValue(value: unknown): value is string {
  if (typeof value !== 'string') return false
  try {
    normalizeCliColor(value)
    return true
  } catch {
    return false
  }
}

export function cliColorPreview(
  value: string,
  terminalTextColor = '#d8fff4',
  terminalBackgroundColor = '#101f20'
): { color: string; backgroundColor?: string } {
  if (value === 'REVERSE') {
    return { color: terminalBackgroundColor, backgroundColor: terminalTextColor }
  }
  if (value.endsWith('_BG_WHITE')) {
    return { color: '#ffffff', backgroundColor: ansiColorMap[value] ?? '#800000' }
  }
  if (value === 'RED_BG') {
    return { color: terminalTextColor, backgroundColor: ansiColorMap[value] }
  }
  if (value.startsWith('BG_')) {
    return {
      color: terminalTextColor,
      backgroundColor: xtermColor(Number(value.slice(3)))
    }
  }
  if (value.startsWith('COLOR_')) {
    return { color: xtermColor(Number(value.slice(6))), backgroundColor: terminalBackgroundColor }
  }
  if (value.startsWith('#')) return { color: value }
  if (value === 'RESET')
    return { color: terminalTextColor, backgroundColor: terminalBackgroundColor }
  return { color: ansiColorMap[value] ?? '#d8fff4' }
}

export function cliColorInputValue(value: string): string {
  return cliColorPreview(value).color
}

export function cliColorSwatch(
  value: string,
  terminalTextColor = '#d8fff4',
  terminalBackgroundColor = '#101f20'
): { color: string; backgroundColor: string } {
  if (value.startsWith('COLOR_')) {
    const backgroundColor = xtermColor(Number(value.slice(6)))
    return { color: contrastTextColor(backgroundColor), backgroundColor }
  }
  const preview = cliColorPreview(value, terminalTextColor, terminalBackgroundColor)
  const backgroundColor = preview.backgroundColor ?? preview.color
  const foregroundColor = preview.backgroundColor
    ? preview.color
    : contrastTextColor(backgroundColor)
  return { color: foregroundColor, backgroundColor }
}

function contrastTextColor(background: string): string {
  const channels = background.match(/[0-9a-f]{2}/gi)?.map((channel) => parseInt(channel, 16) / 255)
  if (!channels || channels.length !== 3) return '#ffffff'
  const luminance = channels
    .map((value) => (value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4))
    .reduce((total, value, index) => total + value * [0.2126, 0.7152, 0.0722][index], 0)
  return luminance > 0.42 ? '#15181e' : '#ffffff'
}

function xtermColor(index: number): string {
  if (index < 16) return basicXtermColors[index]
  if (index < 232) {
    const levels = [0, 95, 135, 175, 215, 255]
    const value = index - 16
    return `#${[
      levels[Math.floor(value / 36)],
      levels[Math.floor(value / 6) % 6],
      levels[value % 6]
    ]
      .map((channel) => channel.toString(16).padStart(2, '0'))
      .join('')}`
  }
  const gray = 8 + (index - 232) * 10
  return `#${gray.toString(16).padStart(2, '0').repeat(3)}`
}
