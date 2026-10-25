import type { CourseReportRow } from './types'

function decodeHtmlEntities(value: string): string {
  return value.replace(/&(#x[\da-f]+|#\d+|amp|lt|gt|quot|apos|nbsp);/gi, (entity, code: string) => {
    const normalized = code.toLowerCase()
    if (normalized === 'amp') return '&'
    if (normalized === 'lt') return '<'
    if (normalized === 'gt') return '>'
    if (normalized === 'quot') return '"'
    if (normalized === 'apos') return "'"
    if (normalized === 'nbsp') return ' '
    const numeric = normalized.startsWith('#x')
      ? Number.parseInt(normalized.slice(2), 16)
      : Number.parseInt(normalized.slice(1), 10)
    return Number.isInteger(numeric) && numeric >= 0 && numeric <= 0x10ffff
      ? String.fromCodePoint(numeric)
      : entity
  })
}

function cellText(html: string): string {
  return decodeHtmlEntities(
    html
      .replace(/<br\s*\/?>/gi, ' ')
      .replace(/<\/(?:div|p|li)>/gi, ' ')
      .replace(/<[^>]*>/g, ' ')
  )
    .replace(/\s+/g, ' ')
    .trim()
}

export function parseTimeReportRows(html: string, thresholdMinutes: number): CourseReportRow[] {
  const table = html.match(/<table\b(?=[^>]*\bid=["']sort-table["'])[^>]*>([\s\S]*?)<\/table>/i)
  if (!table) return []

  const rows: CourseReportRow[] = []
  for (const rowMatch of table[1].matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)) {
    const cells = [...rowMatch[1].matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/gi)].map((cell) =>
      cellText(cell[1])
    )
    if (cells.length < 4) continue

    const [, platformTime, videoTime, practiceTime] = cells
    const hours = Number(platformTime.match(/(\d+)\s*小時/)?.[1] ?? 0)
    const minutes = Number(platformTime.match(/(\d+)\s*分鐘/)?.[1] ?? 0)
    rows.push({
      month: cells[0],
      platformTime,
      videoTime,
      practiceTime,
      isBelowThreshold: hours * 60 + minutes < thresholdMinutes
    })
  }
  return rows
}
