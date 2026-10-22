export function isGoogleOAuthProviderHref(href: string): boolean {
  try {
    const url = new URL(href, 'https://www.coolenglish.edu.tw')
    return (
      url.origin === 'https://www.coolenglish.edu.tw' &&
      /^\/auth\/oauth2\/login\.php$/i.test(url.pathname) &&
      url.searchParams.get('id') === '2'
    )
  } catch {
    return false
  }
}

export function isGoogleAccountsUrl(rawUrl: string): boolean {
  try {
    const hostname = new URL(rawUrl).hostname.toLowerCase()
    return (
      hostname === 'accounts.google.com' ||
      hostname.endsWith('.accounts.google.com') ||
      hostname === 'accounts.google.com.tw'
    )
  } catch {
    return false
  }
}

export function isGoogleRecaptchaUrl(rawUrl: string): boolean {
  try {
    const url = new URL(rawUrl)
    const hostname = url.hostname.toLowerCase()
    return (
      ((hostname === 'google.com' || hostname.endsWith('.google.com')) &&
        /^\/recaptcha(?:\/|$)/i.test(url.pathname)) ||
      ((hostname === 'recaptcha.net' || hostname.endsWith('.recaptcha.net')) &&
        /^\/recaptcha(?:\/|$)/i.test(url.pathname))
    )
  } catch {
    return false
  }
}
