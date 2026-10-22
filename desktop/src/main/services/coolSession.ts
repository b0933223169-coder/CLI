export interface MoodleSessionCookie {
  name: string
  value: string
  domain: string
  expires: number
}

export function isCoolEnglishPageUrl(rawUrl: string): boolean {
  try {
    const url = new URL(rawUrl)
    return (
      url.protocol === 'https:' &&
      (url.hostname === 'www.coolenglish.edu.tw' || url.hostname === 'coolenglish.edu.tw')
    )
  } catch {
    return false
  }
}

export function coolEnglishCookies<T extends MoodleSessionCookie>(cookies: T[]): T[] {
  return cookies.filter((cookie) => {
    const domain = cookie.domain.replace(/^\./, '').toLowerCase()
    return domain === 'www.coolenglish.edu.tw' || domain === 'coolenglish.edu.tw'
  })
}

export function hasUsableMoodleSession(cookies: MoodleSessionCookie[], now = Date.now()): boolean {
  const currentTime = now / 1000
  return cookies.some((cookie) => {
    const domain = cookie.domain.replace(/^\./, '').toLowerCase()
    return (
      cookie.name === 'MoodleSession' &&
      cookie.value.length > 0 &&
      (domain === 'www.coolenglish.edu.tw' || domain === 'coolenglish.edu.tw') &&
      (cookie.expires <= 0 || cookie.expires > currentTime)
    )
  })
}

export function isAuthenticatedCoolEnglishDashboard(
  responseUrl: string,
  status: number,
  html: string
): boolean {
  let url: URL
  try {
    url = new URL(responseUrl)
  } catch {
    return false
  }

  if (!isCoolEnglishPageUrl(responseUrl) || status < 200 || status >= 400) return false
  if (/^\/(?:login(?:\/|\.php|$)|auth(?:\/|$))/i.test(url.pathname)) return false
  const profileGate =
    /\/user\/profile\.php$/i.test(url.pathname) &&
    /<form\b/i.test(html) &&
    /firstname|lastname|gender|birthday|phone|mobile|請填寫|verification|complete profile/i.test(
      html
    ) &&
    !/logout\.php|登出/i.test(html)
  if (profileGate) return false

  const userId = Number(html.match(/["']userId["']\s*:\s*(\d+)/i)?.[1] ?? 0)
  const isDashboard = /^\/(?:my\/?)?$/i.test(url.pathname)
  if (/logout\.php|登出/i.test(html)) return true
  if (
    /<input\b[^>]*(?:type=["']password["']|name=["']username["'])/i.test(html) ||
    /<form\b[^>]*id=["']login["']/i.test(html)
  ) {
    return false
  }
  return (
    (isDashboard && userId > 1) ||
    /log-out|log_out|個人檔案|time_view_detail_by_people\.php/i.test(html)
  )
}

export function classifyCoolEnglishTimeReport(
  responseUrl: string,
  status: number,
  html: string
): 'valid' | 'expired' | 'unknown' {
  let url: URL
  try {
    url = new URL(responseUrl)
  } catch {
    return 'unknown'
  }
  const onCoolEnglish = isCoolEnglishPageUrl(responseUrl)
  const loginRoute = /^\/(?:login(?:\/|\.php|$)|auth(?:\/|$))/i.test(url.pathname)
  if (
    (!onCoolEnglish && /accounts\.google\.com/i.test(url.hostname)) ||
    (onCoolEnglish && loginRoute) ||
    /logintoken|loginredirect/i.test(html) ||
    /<input\b[^>]*(?:type=["']password["']|name=["']username["'])/i.test(html) ||
    /<form\b[^>]*id=["']login["']/i.test(html)
  ) {
    return 'expired'
  }
  if (!onCoolEnglish || status < 200 || status >= 400) return 'unknown'
  const hasReportTable =
    /<table\b[^>]*id=["']sort-table["'][^>]*>/i.test(html) &&
    /<tbody\b[^>]*>[\s\S]*?<tr\b[^>]*>[\s\S]*?<td\b[^>]*>[\s\S]*?<td\b[^>]*>[\s\S]*?<td\b[^>]*>[\s\S]*?<td\b/i.test(
      html
    )
  return hasReportTable ? 'valid' : 'unknown'
}

export function isAuthenticatedCoolEnglishTimeReport(
  responseUrl: string,
  status: number,
  html: string
): boolean {
  return classifyCoolEnglishTimeReport(responseUrl, status, html) === 'valid'
}
