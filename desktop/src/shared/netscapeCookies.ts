import type { StoredCookie } from './types'

export function parseNetscapeCookies(text: string): StoredCookie[] {
  return text.split(/\r?\n/).flatMap((rawLine) => {
    const isHttpOnly = rawLine.startsWith('#HttpOnly_')
    const line = isHttpOnly ? rawLine.slice('#HttpOnly_'.length) : rawLine
    if (!line || (line.startsWith('#') && !isHttpOnly)) return []
    const [domain, , path, secure, expiry, name, ...value] = line.split('\t')
    if (!domain || !path || !name || value.length === 0 || !Number.isFinite(Number(expiry))) {
      return []
    }
    return [
      {
        name,
        value: value.join('\t'),
        domain,
        path,
        secure: secure?.toUpperCase() === 'TRUE',
        httpOnly: isHttpOnly,
        expires: Number.parseInt(expiry ?? '0', 10) || 0
      }
    ]
  })
}
