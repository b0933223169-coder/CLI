import type { FontFamily } from './types'

const fontFamilies: readonly FontFamily[] = ['system', 'segoe', 'arial', 'consolas']

export function isFontFamily(value: unknown): value is FontFamily {
  return fontFamilies.some((fontFamily) => fontFamily === value)
}

export function normalizeFontFamily(value: unknown): FontFamily {
  return isFontFamily(value) ? value : 'system'
}

export function fontFamilyStack(font: FontFamily): string {
  switch (font) {
    case 'segoe':
      return '"Segoe UI", "Microsoft JhengHei UI", sans-serif'
    case 'arial':
      return 'Arial, "Microsoft JhengHei UI", sans-serif'
    case 'consolas':
      return 'Consolas, "Microsoft JhengHei UI", monospace'
    default:
      return 'Inter, "Segoe UI", "Microsoft JhengHei UI", sans-serif'
  }
}

export function terminalFontFamilyStack(font: FontFamily): string {
  switch (font) {
    case 'consolas':
      return 'Consolas, "Cascadia Mono", "Courier New", monospace'
    case 'segoe':
    case 'arial':
    case 'system':
    default:
      return '"Cascadia Mono", Consolas, "Courier New", monospace'
  }
}
