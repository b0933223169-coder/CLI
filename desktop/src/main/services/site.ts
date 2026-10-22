import {
  Browser,
  BrowserContext,
  chromium,
  Page,
  request,
  type APIRequestContext
} from 'playwright'
import { BrowserWindow } from 'electron'
import type { CourseReportRow, LoginMode, StoredCookie } from '../../shared/types'
import { parseTimeReportRows } from '../../shared/timeReportParser'
import { getAccounts, getCookies, saveCredential, saveLogin, setCookieStatus } from './storage'
import {
  beginNetworkSession,
  beginNetworkBodyCapture,
  canCaptureNetworkBody,
  endNetworkSession,
  isNetworkHistoryEnabled,
  isNetworkSessionActive,
  recordNetworkEvent,
  shouldCaptureRawNetworkBodies,
  updateNetworkSessionMode
} from './networkHistory'
import {
  coolEnglishCookies,
  hasUsableMoodleSession,
  isAuthenticatedCoolEnglishDashboard,
  isCoolEnglishPageUrl,
  classifyCoolEnglishTimeReport
} from './coolSession'
import { completeCoolEnglishLogin } from './coolLoginCompletion'
import { formatTerminalCourseStatusLine } from '../../shared/terminalCourseProgress'
import { isGoogleAccountsUrl, isGoogleOAuthProviderHref, isGoogleRecaptchaUrl } from './googleLogin'
import type { NetworkSessionStatus } from './networkSessionState'

const BASE_URL = 'https://www.coolenglish.edu.tw'
const LOGIN_URL = `${BASE_URL}/login/index.php`
const REPORT_URL = `${BASE_URL}/time/time_view_report.php`
const HEADLESS_LOGIN_TIMEOUT_MS = 60_000
const HEADED_LOGIN_TIMEOUT_MS = 15 * 60_000
const LOGIN_POLL_INTERVAL_MS = 500
const SESSION_VALIDATION_RETRY_INTERVAL_MS = 2_000
const logins = new Map<
  number,
  { browser: Browser; context: BrowserContext; email: string; name: string; sessionId: string }
>()
const browsers = new Set<Browser>()
interface SessionWork {
  browser?: Browser
  stopped: boolean
  disconnectedStatus: Exclude<NetworkSessionStatus, 'active' | 'stopped'>
  onCourseProgress?: (status: 'completed' | 'failed' | 'stopped') => void
}
const sessionWork = new Map<string, SessionWork>()

class LoginTimeoutError extends Error {}

function beginSessionWork(
  sessionId: string,
  disconnectedStatus: SessionWork['disconnectedStatus'] = 'failed'
): SessionWork {
  const work: SessionWork = { stopped: false, disconnectedStatus }
  sessionWork.set(sessionId, work)
  return work
}

function attachSessionBrowser(sessionId: string, browser: Browser, work: SessionWork): void {
  work.browser = browser
  browsers.add(browser)
  browser.on('disconnected', () => {
    browsers.delete(browser)
    if (sessionWork.get(sessionId) === work && work.browser === browser) {
      sessionWork.delete(sessionId)
      work.onCourseProgress?.(work.stopped ? 'stopped' : work.disconnectedStatus)
      for (const [windowId, login] of logins) {
        if (login.sessionId === sessionId) logins.delete(windowId)
      }
      void endNetworkSession(sessionId, work.disconnectedStatus).catch((error: unknown) =>
        console.error('無法結束 Playwright 工作階段：', error)
      )
    }
  })
  if (work.stopped && browser.isConnected()) void browser.close()
}

function finishSessionWork(sessionId: string, work: SessionWork): void {
  if (sessionWork.get(sessionId) === work) sessionWork.delete(sessionId)
}

export async function stopNetworkSessionWork(sessionId: string): Promise<void> {
  const work = sessionWork.get(sessionId)
  if (!work) {
    throw new Error('此工作階段已結束或不存在可停止的 Playwright 工作。')
  }
  work.stopped = true
  work.onCourseProgress?.('stopped')
  await endNetworkSession(sessionId, 'stopped')
  if (work.browser?.isConnected()) await work.browser.close()
  if (work.browser) browsers.delete(work.browser)
  finishSessionWork(sessionId, work)
}

function redactUrl(raw: string): string {
  try {
    const url = new URL(raw)
    for (const key of [...url.searchParams.keys()]) {
      if (/pass|token|secret|cookie|auth|session|csrf|code|state|signature/i.test(key)) {
        url.searchParams.set(key, '[REDACTED]')
      }
    }
    url.hash = ''
    url.username = ''
    url.password = ''
    return url.toString()
  } catch {
    return raw
  }
}

function redactHeaders(headers: Record<string, string>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(headers).map(([name, value]) => [
      name,
      /authorization|cookie|token|secret|password|session|api[-_]key/i.test(name)
        ? '[REDACTED]'
        : value
    ])
  )
}

function bodyEncodingForContentType(contentType: string): 'text' | 'hex' {
  return /^(text\/|application\/(?:json|xml|javascript|x-www-form-urlencoded))/i.test(contentType)
    ? 'text'
    : 'hex'
}

function trackNetwork(
  context: BrowserContext,
  window: BrowserWindow,
  sessionId: string
): (page: Page) => Promise<void> {
  if (!isNetworkHistoryEnabled()) return async () => undefined
  type RequestInfo = {
    method: string
    url: string
    headers: Record<string, string>
    rawCapture: boolean
    recorded: Promise<void>
  }
  type ResponseInfo = {
    method: string
    url: string
    status: number
    headers: Record<string, string>
    contentType: string
    bodyEncoding: 'text' | 'hex'
    rawCapture: boolean
    time: string
    requestRecorded?: Promise<void>
    pendingData: string[]
    capture?: Awaited<ReturnType<typeof beginNetworkBodyCapture>>
    startCapture?: Promise<void>
    captureError?: string
  }
  const pageAttachments = new WeakMap<Page, Promise<void>>()
  const attachPage = (page: Page): Promise<void> => {
    const attached = pageAttachments.get(page)
    if (attached) return attached
    const setup = (async () => {
      const client = await context.newCDPSession(page)
      const requests = new Map<string, RequestInfo>()
      const responses = new Map<string, ResponseInfo>()
      const record = (event: Parameters<typeof recordNetworkEvent>[2], label: string): void => {
        void recordNetworkEvent(window, sessionId, event).catch((error: unknown) =>
          console.error(`無法保存 Playwright ${label} 紀錄：`, error)
        )
      }
      client.on('Network.requestWillBeSent', (event) => {
        const { request: requestData } = event
        const headers = Object.fromEntries(
          Object.entries(requestData.headers).map(([name, value]) => [name, String(value)])
        )
        const contentType = headers['content-type'] ?? ''
        const info: RequestInfo = {
          method: requestData.method,
          url: requestData.url,
          headers,
          rawCapture: shouldCaptureRawNetworkBodies(),
          recorded: Promise.resolve()
        }
        requests.set(event.requestId, info)
        const requestTime = new Date().toISOString()
        info.recorded = (async () => {
          let capture: Awaited<ReturnType<typeof beginNetworkBodyCapture>> | undefined
          let bodyAttachmentId: string | undefined
          let bodyBytes: number | undefined
          let bodyCaptureError: string | undefined
          if (
            info.rawCapture &&
            (requestData.hasPostData || requestData.postData || requestData.postDataEntries?.length)
          ) {
            try {
              if (/multipart\/form-data/i.test(contentType)) {
                throw new Error(
                  'Chromium CDP 會省略 multipart/form-data 上傳檔案位元組，無法保證完整 request body，因此未保存部分內容。'
                )
              }
              const entries = requestData.postDataEntries
              const entryBytes = entries?.map((entry) => entry.bytes)
              const completeEntryBytes = entryBytes?.filter(
                (value): value is string => typeof value === 'string'
              )
              let bytes: Buffer
              if (completeEntryBytes?.length && completeEntryBytes.length === entryBytes?.length) {
                bytes = Buffer.concat(
                  completeEntryBytes.map((value) => Buffer.from(value, 'base64'))
                )
              } else {
                const { postData, base64Encoded } = await client.send(
                  'Network.getRequestPostData',
                  { requestId: event.requestId }
                )
                bytes = base64Encoded ? Buffer.from(postData, 'base64') : Buffer.from(postData)
              }
              const bodyEncoding = bodyEncodingForContentType(contentType)
              capture = await beginNetworkBodyCapture(sessionId, bodyEncoding, true)
              await capture.appendBase64(bytes.toString('base64'))
              bodyBytes = await capture.finish()
              if (bodyBytes) bodyAttachmentId = capture.id
              else await capture.discard()
            } catch (error) {
              bodyCaptureError = error instanceof Error ? error.message : String(error)
              await capture?.discard()
            }
          }
          if (!isNetworkSessionActive(sessionId)) {
            await capture?.discard()
            return
          }
          record(
            {
              kind: 'request',
              method: info.method,
              url: redactUrl(info.url),
              headers: redactHeaders(info.headers),
              ...(info.rawCapture
                ? {
                    bodyContentType: contentType || '未知格式',
                    bodyEncoding: bodyEncodingForContentType(contentType),
                    bodySource: 'request' as const,
                    bodyStorage: 'raw' as const,
                    ...(bodyAttachmentId ? { bodyAttachmentId, bodyBytes } : {}),
                    ...(bodyCaptureError ? { bodyCaptureError } : {})
                  }
                : {}),
              time: requestTime
            },
            'request'
          )
        })()
      })
      client.on('Network.responseReceived', (event) => {
        const response = event.response
        const requestInfo = requests.get(event.requestId)
        const responseHeaders = Object.fromEntries(
          Object.entries(response.headers).map(([name, value]) => [name, String(value)])
        )
        const info: ResponseInfo = {
          method: requestInfo?.method ?? 'GET',
          url: response.url,
          status: response.status,
          headers: redactHeaders(responseHeaders),
          contentType: response.mimeType,
          rawCapture: requestInfo?.rawCapture ?? shouldCaptureRawNetworkBodies(),
          bodyEncoding: bodyEncodingForContentType(response.mimeType),
          time: new Date().toISOString(),
          requestRecorded: requestInfo?.recorded,
          pendingData: []
        }
        responses.set(event.requestId, info)
        if (!canCaptureNetworkBody(sessionId)) {
          if (info.rawCapture && isNetworkSessionActive(sessionId)) {
            info.captureError = '原始本文擷取已關閉，未保存本文。'
          }
          return
        }
        info.startCapture = (async () => {
          let capture: Awaited<ReturnType<typeof beginNetworkBodyCapture>> | undefined
          try {
            capture = await beginNetworkBodyCapture(sessionId, info.bodyEncoding, info.rawCapture)
            const { bufferedData } = await client.send('Network.streamResourceContent', {
              requestId: event.requestId
            })
            info.pendingData.length = 0
            const bufferedWrite = bufferedData
              ? capture.appendBase64(bufferedData)
              : Promise.resolve()
            info.capture = capture
            await bufferedWrite
          } catch (error) {
            info.captureError = error instanceof Error ? error.message : String(error)
            await capture?.discard()
          }
        })()
      })
      client.on('Network.dataReceived', (event) => {
        const info = responses.get(event.requestId)
        if (!info || !event.data) return
        if (!info.capture) {
          if (info.startCapture) info.pendingData.push(event.data)
          return
        }
        void info.capture.appendBase64(event.data).catch((error: unknown) => {
          info.captureError = error instanceof Error ? error.message : String(error)
        })
      })
      client.on('Network.loadingFinished', (event) => {
        const info = responses.get(event.requestId)
        if (!info) return
        responses.delete(event.requestId)
        requests.delete(event.requestId)
        void (async () => {
          let bodyAttachmentId: string | undefined
          let bodyBytes: number | undefined
          if (info.startCapture) {
            await info.startCapture
            if (info.capture) {
              try {
                bodyBytes = await info.capture.finish()
                if (bodyBytes) bodyAttachmentId = info.capture.id
                else await info.capture.discard()
              } catch (error) {
                info.captureError = error instanceof Error ? error.message : String(error)
                await info.capture.discard()
              }
            }
          }
          if (!isNetworkSessionActive(sessionId)) {
            if (info.capture) await info.capture.discard()
            return
          }
          await info.requestRecorded
          record(
            {
              kind: 'response',
              method: info.method,
              status: info.status,
              url: redactUrl(info.url),
              headers: info.headers,
              ...(info.rawCapture
                ? {
                    bodyContentType: info.contentType,
                    bodySource: 'response' as const,
                    bodyStorage: 'raw' as const,
                    ...(bodyAttachmentId
                      ? {
                          bodyAttachmentId,
                          bodyBytes,
                          bodyEncoding: info.bodyEncoding
                        }
                      : {}),
                    ...(info.captureError ? { bodyCaptureError: info.captureError } : {})
                  }
                : {}),
              time: info.time
            },
            'response'
          )
        })().catch((error: unknown) => console.error('無法完成 Playwright response 紀錄：', error))
      })
      client.on('Network.loadingFailed', (event) => {
        const info = responses.get(event.requestId)
        const requestInfo = requests.get(event.requestId)
        if (info) {
          void (async () => {
            await info.startCapture
            await info.capture?.discard()
          })().catch((error: unknown) => console.error('無法清理未完成的網路本文：', error))
        }
        responses.delete(event.requestId)
        requests.delete(event.requestId)
        record(
          {
            kind: 'failed',
            method: requestInfo?.method,
            url: redactUrl(requestInfo?.url ?? ''),
            message: event.errorText,
            time: new Date().toISOString()
          },
          'failure'
        )
      })
      client.on('close', () => {
        for (const info of responses.values()) {
          void (async () => {
            await info.startCapture
            await info.capture?.discard()
          })().catch((error: unknown) => console.error('無法清理未完成的網路本文：', error))
        }
        responses.clear()
      })
      page.on('close', () => {
        void client.detach().catch(() => undefined)
      })
      await client.send('Network.enable')
    })()
    pageAttachments.set(page, setup)
    return setup
  }

  context.on('page', (page) => {
    void attachPage(page).catch((error: unknown) =>
      console.error('無法啟用 Chromium 網路串流紀錄：', error)
    )
  })
  for (const page of context.pages()) {
    void attachPage(page).catch((error: unknown) =>
      console.error('無法啟用 Chromium 網路串流紀錄：', error)
    )
  }
  return attachPage
}

async function launchBrowser(headless: boolean): Promise<Browser> {
  try {
    return await chromium.launch({ headless, channel: 'msedge' })
  } catch (edgeError) {
    try {
      return await chromium.launch({ headless })
    } catch (chromiumError) {
      throw new Error(
        `找不到可用瀏覽器。請安裝 Microsoft Edge，或執行 npx playwright install chromium。\nEdge：${String(edgeError)}\nChromium：${String(chromiumError)}`
      )
    }
  }
}

function toPlaywrightCookies(
  cookies: Array<StoredCookie & { sameSite: 'Lax' }>
): Array<Parameters<BrowserContext['addCookies']>[0][number]> {
  return cookies.map((cookie) => ({
    ...cookie,
    sameSite: cookie.sameSite
  }))
}

async function validateCoolEnglishSession(
  context: BrowserContext,
  baseUrl = BASE_URL,
  pages: Page[] = []
): Promise<boolean> {
  const cookies = coolEnglishCookies(await context.cookies())
  if (!hasUsableMoodleSession(cookies)) return false

  for (const page of pages) {
    try {
      if (page.isClosed() || !isCoolEnglishPageUrl(page.url())) continue
      const renderedHtml = await page.content()
      if (isAuthenticatedCoolEnglishDashboard(page.url(), 200, renderedHtml)) {
        return hasUsableMoodleSession(coolEnglishCookies(await context.cookies()))
      }
    } catch (error) {
      if (!page.isClosed()) throw error
    }
  }

  const response = await context.request.get(`${baseUrl}/my/`, { timeout: 20_000 })
  try {
    if (!isCoolEnglishPageUrl(response.url()) || response.status() >= 400) return false

    const html = await response.text()
    if (isAuthenticatedCoolEnglishDashboard(response.url(), response.status(), html)) {
      return hasUsableMoodleSession(coolEnglishCookies(await context.cookies()))
    }

    const finalUrl = new URL(response.url())
    if (/^\/(?:login(?:\/|\.php|$)|auth(?:\/|$))/i.test(finalUrl.pathname)) return false
    for (const page of pages) {
      if (page.isClosed() || !isCoolEnglishPageUrl(page.url())) continue
      try {
        const pageHtml = await page.content()
        if (isAuthenticatedCoolEnglishDashboard(page.url(), 200, pageHtml)) {
          return hasUsableMoodleSession(coolEnglishCookies(await context.cookies()))
        }
      } catch (error) {
        if (!page.isClosed()) throw error
      }
    }
    return false
  } finally {
    await response.dispose()
  }
}

async function validateTimeReportCookie(
  context: BrowserContext,
  accountEmail: string
): Promise<'valid' | 'expired' | 'unknown'> {
  const account = (await getAccounts()).find(
    (item) => item.email.toLowerCase() === accountEmail.toLowerCase()
  )
  const reportUrl =
    account?.user_id && !['0', '1'].includes(account.user_id)
      ? `${BASE_URL}/time/time_view_detail_by_people.php?id=${encodeURIComponent(account.user_id)}`
      : REPORT_URL
  const response = await context.request.get(reportUrl, { timeout: 20_000 })
  try {
    return classifyTimeReportResponse(
      context,
      response.url(),
      response.status(),
      await response.text()
    )
  } finally {
    await response.dispose()
  }
}

async function classifyTimeReportResponse(
  context: BrowserContext,
  responseUrl: string,
  status: number,
  html: string
): Promise<'valid' | 'expired' | 'unknown'> {
  if (!hasUsableMoodleSession(coolEnglishCookies(await context.cookies(BASE_URL)))) {
    return 'expired'
  }
  return classifyCoolEnglishTimeReport(responseUrl, status, html)
}

function timeReportValidationError(status: 'expired' | 'unknown'): Error {
  return new Error(
    status === 'expired'
      ? 'Cool English 將此 Cookie 導向登入頁或顯示登入表單，請重新登入。'
      : '無法確認 Cookie 狀態：時數頁沒有可辨識的時數表格，可能是暫時性網站錯誤或帳號權限問題。'
  )
}

function isGoogleAccountsPage(page: Page): boolean {
  return isGoogleAccountsUrl(page.url())
}

async function findVisibleGoogleLoginButton(
  page: Page
): Promise<ReturnType<Page['locator']> | null> {
  const buttons = page.locator('a[href*="oauth2/login.php"]')
  for (let index = 0; index < (await buttons.count()); index += 1) {
    const button = buttons.nth(index)
    const href = await button.getAttribute('href')
    if (href && isGoogleOAuthProviderHref(href) && (await button.isVisible())) return button
  }
  return null
}

async function startGoogleLogin(page: Page): Promise<boolean> {
  if (isGoogleAccountsPage(page)) return true
  if (!isCoolEnglishPageUrl(page.url())) return true
  const button = await findVisibleGoogleLoginButton(page)
  if (!button) return false
  await button.click()
  return true
}

async function hasGoogleExtraVerification(page: Page): Promise<boolean> {
  if (page.frames().some((frame) => isGoogleRecaptchaUrl(frame.url()))) return true
  if (!isGoogleAccountsPage(page)) return false
  const challenge = page.locator(
    'input[name="totpPin"], input[name="idvPin"], iframe[src*="recaptcha"], [data-challenge]'
  )
  if ((await challenge.count()) > 0) return true
  const text = await page
    .locator('body')
    .innerText()
    .catch(() => '')
  return /2-step verification|two.step verification|verify it.s you|security key|passkey|驗證碼|兩步驟驗證|確認是你本人|安全金鑰|通行密鑰|captcha/i.test(
    text
  )
}

async function submitGoogleStep(input: ReturnType<Page['locator']>): Promise<void> {
  const page = input.page()
  if (page.isClosed()) return
  const nextButton = page.locator('#identifierNext:visible, #passwordNext:visible').first()
  if ((await nextButton.count()) > 0 && (await nextButton.isEnabled())) {
    await nextButton.click({ noWaitAfter: true, timeout: 3_000 })
    return
  }
  await input.press('Enter', { noWaitAfter: true, timeout: 3_000 })
}

async function advanceGoogleLogin(
  page: Page,
  email: string,
  password: string,
  completedSteps: WeakMap<Page, Set<string>>
): Promise<void> {
  if (!isGoogleAccountsPage(page) || (await hasGoogleExtraVerification(page))) return
  let completed = completedSteps.get(page)
  if (!completed) {
    completed = new Set<string>()
    completedSteps.set(page, completed)
  }

  const passwordInput = page.locator('input[type="password"]').first()
  if ((await passwordInput.count()) > 0 && (await passwordInput.isVisible())) {
    const key = `${page.url()}|password`
    if (!completed.has(key)) {
      await passwordInput.fill(password)
      await submitGoogleStep(passwordInput)
      completed.add(key)
    }
    return
  }

  const emailInput = page.locator('input[type="email"], input[name="identifier"]').first()
  if ((await emailInput.count()) > 0 && (await emailInput.isVisible())) {
    const key = `${page.url()}|email`
    if (!completed.has(key)) {
      await emailInput.fill(email)
      await submitGoogleStep(emailInput)
      completed.add(key)
    }
    return
  }

  const matchingAccount = page
    .locator('button, [role="button"], [role="link"]')
    .filter({ hasText: email })
    .first()
  if ((await matchingAccount.count()) > 0 && (await matchingAccount.isVisible())) {
    const key = `${page.url()}|account`
    if (!completed.has(key)) {
      await matchingAccount.click()
      completed.add(key)
    }
  }
}

export async function beginLogin(
  window: BrowserWindow,
  email: string,
  password: string,
  name: string,
  mode: LoginMode
): Promise<Awaited<ReturnType<typeof getAccounts>>> {
  if (!email.includes('@') || !password) throw new Error('請輸入有效的 Email 與密碼。')
  const id = window.id
  const previous = logins.get(id)
  if (previous) {
    logins.delete(id)
    await previous.browser.close()
    await endNetworkSession(previous.sessionId, 'failed')
  }
  const sessionId = await beginNetworkSession(mode, `登入 ${email}`)
  const work = beginSessionWork(sessionId)
  let browser: Browser | undefined
  try {
    browser = await launchBrowser(mode === 'headless')
    attachSessionBrowser(sessionId, browser, work)
    const context = await browser.newContext()
    const attachNetworkPage = trackNetwork(context, window, sessionId)
    logins.set(id, { browser, context, email, name, sessionId })
    const page = await context.newPage()
    await attachNetworkPage(page)
    await page.goto(LOGIN_URL, { waitUntil: 'domcontentloaded', timeout: 30_000 })
  } catch (error) {
    logins.delete(id)
    if (browser) {
      browsers.delete(browser)
      await browser.close()
    }
    finishSessionWork(sessionId, work)
    await endNetworkSession(sessionId, 'failed')
    throw error
  }

  if (!browser) throw new Error('無法啟動登入瀏覽器。')
  let loginBrowser: Browser = browser
  const initialContext = logins.get(id)?.context
  if (!initialContext) throw new Error('登入瀏覽器工作階段已中斷。')
  let loginContext: BrowserContext = initialContext
  const startedGooglePages = new WeakSet<Page>()
  const completedGoogleSteps = new WeakMap<Page, Set<string>>()
  let runningHeadless = mode === 'headless'
  let reportedCoolEnglishPage = false
  let deadline =
    Date.now() + (runningHeadless ? HEADLESS_LOGIN_TIMEOUT_MS : HEADED_LOGIN_TIMEOUT_MS)
  let lastValidationError: string | undefined
  let lastValidationAt = 0
  let wakeCurrent: () => void = () => {}
  let wakePromise = new Promise<void>((resolve) => {
    wakeCurrent = resolve
  })
  const wake = (): void => {
    wakeCurrent()
    wakePromise = new Promise<void>((resolve) => {
      wakeCurrent = resolve
    })
  }
  const watchPage = (page: Page): void => {
    page.on('domcontentloaded', wake)
    page.on('framenavigated', wake)
    page.on('close', wake)
    page.on('requestfinished', (request) => {
      try {
        const hostname = new URL(request.url()).hostname
        if (hostname === 'accounts.google.com' || hostname.endsWith('.accounts.google.com')) wake()
      } catch {
        return
      }
    })
  }
  const watchContext = (context: BrowserContext): void => {
    for (const page of context.pages()) watchPage(page)
    context.on('page', (page) => {
      watchPage(page)
      wake()
    })
  }
  const watchBrowser = (browserToWatch: Browser): void => {
    browserToWatch.on('disconnected', wake)
  }
  watchContext(loginContext)
  watchBrowser(loginBrowser)

  const switchToVisibleBrowser = async (currentPage: Page): Promise<void> => {
    const previousBrowser = loginBrowser
    const state = await loginContext.storageState()
    const currentUrl = currentPage.url()
    const visibleBrowser = await launchBrowser(false)
    try {
      const visibleContext = await visibleBrowser.newContext({ storageState: state })
      const attachNetworkPage = trackNetwork(visibleContext, window, sessionId)
      const visiblePage = await visibleContext.newPage()
      await attachNetworkPage(visiblePage)
      await visiblePage.goto(currentUrl, { waitUntil: 'domcontentloaded', timeout: 30_000 })
      await updateNetworkSessionMode(sessionId, 'headed')
      loginBrowser = visibleBrowser
      loginContext = visibleContext
      logins.set(id, { browser: visibleBrowser, context: visibleContext, email, name, sessionId })
      attachSessionBrowser(sessionId, visibleBrowser, work)
      watchContext(visibleContext)
      watchBrowser(visibleBrowser)
      runningHeadless = false
      deadline = Date.now() + HEADED_LOGIN_TIMEOUT_MS
      if (!window.isDestroyed()) {
        window.webContents.send(
          'accounts:login-interaction-required',
          '無頭登入遇到 reCAPTCHA 或額外驗證，已切換到可見瀏覽器。請在瀏覽器中完成驗證，成功後會自動驗證並保存 Cookie。'
        )
      }
    } catch (error) {
      if (visibleBrowser.isConnected()) await visibleBrowser.close()
      browsers.delete(visibleBrowser)
      throw new Error(
        `無法將無頭登入安全切換到可見瀏覽器：${error instanceof Error ? error.message : String(error)}`
      )
    }
    if (previousBrowser.isConnected()) await previousBrowser.close()
    browsers.delete(previousBrowser)
  }

  try {
    while (loginBrowser.isConnected() && Date.now() < deadline && !work.stopped) {
      const pages = loginContext.pages()
      let switchedToVisible = false
      for (const currentPage of pages) {
        if (currentPage.isClosed()) continue
        if (!startedGooglePages.has(currentPage) && !isGoogleAccountsPage(currentPage)) {
          startedGooglePages.add(currentPage)
          try {
            const started = await startGoogleLogin(currentPage)
            if (!started && runningHeadless) {
              throw new Error(
                '無法在 Cool English 登入頁辨識 Google 登入按鈕，未輸入帳密或儲存 cookie。'
              )
            }
          } catch (error) {
            if (runningHeadless) throw error
            console.warn('無法自動開啟 Google 登入，請在有頭瀏覽器中手動操作：', error)
          }
        }
        if (runningHeadless && (await hasGoogleExtraVerification(currentPage))) {
          const recaptchaDetected = currentPage
            .frames()
            .some((frame) => isGoogleRecaptchaUrl(frame.url()))
          console.info(
            recaptchaDetected
              ? '無頭登入偵測到 Google reCAPTCHA，改用可見瀏覽器等待使用者驗證。'
              : '無頭登入偵測到額外驗證，改用可見瀏覽器等待使用者驗證。'
          )
          await switchToVisibleBrowser(currentPage)
          switchedToVisible = true
          break
        }
        await advanceGoogleLogin(currentPage, email, password, completedGoogleSteps).catch(
          (error: unknown) => {
            if (runningHeadless) throw error
            console.warn('Google 登入步驟需手動完成，瀏覽器會保持開啟：', error)
          }
        )
      }
      if (switchedToVisible) continue

      const currentPages = loginContext.pages().filter((page) => !page.isClosed())
      const targetSitePage = currentPages.some((page) => isCoolEnglishPageUrl(page.url()))
      if (targetSitePage) {
        if (!reportedCoolEnglishPage) {
          reportedCoolEnglishPage = true
          if (!window.isDestroyed()) {
            window.webContents.send(
              'accounts:login-status',
              '已偵測到 Cool English 頁面，正在檢查登入狀態；MoodleSession 驗證完成前不會標記成功。'
            )
          }
        }
        const cookies = coolEnglishCookies(await loginContext.cookies())
        const hasSessionCookie = hasUsableMoodleSession(cookies)
        let siteConfirmed = false
        if (
          hasSessionCookie &&
          Date.now() - lastValidationAt >= SESSION_VALIDATION_RETRY_INTERVAL_MS
        ) {
          lastValidationAt = Date.now()
          let validationError: string | undefined
          const targetPage = currentPages.find((page) => isCoolEnglishPageUrl(page.url()))
          const validationBaseUrl = targetPage ? new URL(targetPage.url()).origin : BASE_URL
          try {
            siteConfirmed = await validateCoolEnglishSession(
              loginContext,
              validationBaseUrl,
              currentPages
            )
          } catch (error) {
            validationError = error instanceof Error ? error.message : String(error)
          }
          lastValidationError = siteConfirmed
            ? undefined
            : (validationError ??
              '網站尚未以 Cool English 登入頁面確認 MoodleSession；請完成任何待處理的帳號驗證。')
        }
        if (siteConfirmed) {
          if (work.stopped || !loginBrowser.isConnected()) {
            throw new Error('登入工作階段已中斷，未保存 cookie。')
          }
          const userId = await detectUserId(pages)
          let accounts: Awaited<ReturnType<typeof getAccounts>> | undefined
          await completeCoolEnglishLogin({
            cookies,
            filterCookies: coolEnglishCookies,
            hasUsableSession: hasUsableMoodleSession,
            validate: async () => siteConfirmed && loginBrowser.isConnected() && !work.stopped,
            persist: async (verifiedCookies) => {
              accounts = await saveLogin(email, name, verifiedCookies, userId)
              await saveCredential(email, password)
            },
            markCompleted: async () => {
              logins.delete(id)
              await endNetworkSession(sessionId, 'completed')
              finishSessionWork(sessionId, work)
              if (!window.isDestroyed()) {
                window.webContents.send('accounts:login-success', email)
              }
            },
            closeBrowser: async () => {
              await loginBrowser.close()
              browsers.delete(loginBrowser)
            }
          })
          if (!accounts) throw new Error('登入完成但帳號資料未回傳。')
          return accounts
        }
      }
      const pendingWake = wakePromise
      let deadlineTimer: NodeJS.Timeout | undefined
      await Promise.race([
        pendingWake,
        new Promise<void>((resolve) => {
          deadlineTimer = setTimeout(
            resolve,
            Math.min(LOGIN_POLL_INTERVAL_MS, Math.max(0, deadline - Date.now()))
          )
        })
      ])
      if (deadlineTimer) clearTimeout(deadlineTimer)
    }

    if (work.stopped) throw new Error('登入工作階段已停止。')
    if (!loginBrowser.isConnected()) {
      throw new Error('登入瀏覽器已關閉，尚未完成登入或取得可用的 MoodleSession cookie。')
    }
    if (Date.now() >= deadline) {
      throw new LoginTimeoutError(
        `${runningHeadless ? '無頭' : '有頭'}登入逾時，未確認並保存有效的 MoodleSession cookie。${lastValidationError ? ` 最近檢查：${lastValidationError}` : ''}`
      )
    }
    throw new Error(
      lastValidationError
        ? `${runningHeadless ? '無頭' : '有頭'}登入未能完成或驗證 Cool English 登入狀態：${lastValidationError}。未儲存 Cookie。`
        : `${runningHeadless ? '無頭' : '有頭'}登入未能在時限內完成 Google 登入並驗證 MoodleSession。若網站要求 MFA、CAPTCHA 或額外驗證，請在可見瀏覽器完成；未儲存 Cookie。`
    )
  } catch (error) {
    if (!runningHeadless && loginBrowser.isConnected() && !(error instanceof LoginTimeoutError)) {
      await endNetworkSession(sessionId, 'failed')
      throw new Error(
        `有頭瀏覽器仍保持開啟，但登入或 cookie 安全保存未完成；未宣稱成功。${error instanceof Error ? ` ${error.message}` : ` ${String(error)}`}`
      )
    }
    logins.delete(id)
    if (loginBrowser.isConnected()) await loginBrowser.close()
    browsers.delete(loginBrowser)
    await endNetworkSession(sessionId, 'failed')
    throw error
  } finally {
    if (runningHeadless || work.stopped || !loginBrowser.isConnected()) {
      finishSessionWork(sessionId, work)
    }
  }
}

async function detectUserId(pages: Page[]): Promise<string | undefined> {
  for (const page of pages) {
    try {
      const html = await page.content()
      const match =
        html.match(/time_view_detail_by_people\.php\?id=(\d+)/) ??
        html.match(/"userId"\s*:\s*(\d+)/)
      if (match?.[1] && !['0', '1'].includes(match[1])) return match[1]
    } catch {
      continue
    }
  }
  return undefined
}

export async function openCourses(
  window: BrowserWindow,
  urls: string[],
  accountEmail: string,
  mode: LoginMode,
  label: string,
  onCourseProgress?: (update: {
    sessionId: string
    mode: LoginMode
    label: string
    status: 'active' | 'completed' | 'failed' | 'stopped'
    line?: string
  }) => void
): Promise<void> {
  const targets = urls.map((url) => new URL(url))
  if (!targets.length || targets.some((target) => !['http:', 'https:'].includes(target.protocol))) {
    throw new Error('只接受一個以上的 http 或 https 網址。')
  }
  const shouldPublishCourseProgress = !isNetworkHistoryEnabled()
  const sessionId = await beginNetworkSession(mode, label)
  const work = beginSessionWork(sessionId, mode === 'headed' ? 'completed' : 'failed')
  const publishProgress = (update: {
    status: 'active' | 'completed' | 'failed' | 'stopped'
    line?: string
  }): void => {
    if (shouldPublishCourseProgress) {
      onCourseProgress?.({ sessionId, mode, label, ...update })
    }
  }
  work.onCourseProgress = (status) => publishProgress({ status })
  publishProgress({ status: 'active' })
  let browser: Browser
  try {
    browser = await launchBrowser(mode === 'headless')
  } catch (error) {
    publishProgress({ status: 'failed' })
    finishSessionWork(sessionId, work)
    await endNetworkSession(sessionId, 'failed')
    throw error
  }
  attachSessionBrowser(sessionId, browser, work)
  if (work.stopped) {
    finishSessionWork(sessionId, work)
    return
  }
  try {
    const context = await browser.newContext()
    const attachNetworkPage = trackNetwork(context, window, sessionId)
    await context.addCookies(toPlaywrightCookies(await getCookies(accountEmail)))
    const historyEnabled = isNetworkHistoryEnabled()
    let openedCount = 0
    const progressLabel = (title: string): string =>
      label ? `${label}: ${title.slice(0, 40)}` : title.slice(0, 40)
    for (const [index, target] of targets.entries()) {
      const page = await context.newPage()
      await attachNetworkPage(page)
      try {
        await page.goto(target.toString(), { waitUntil: 'domcontentloaded', timeout: 30_000 })
        if (!historyEnabled) {
          const title = (await page.title()).split('|')[0].trim() || target.toString()
          const pageContent = (await page.content()).slice(0, 2000).toLowerCase()
          const redirectedToLogin =
            /\/login(?:\/|\.php|$)/i.test(page.url()) || pageContent.includes('logintoken')
          if (redirectedToLogin) {
            publishProgress({
              status: 'active',
              line: formatTerminalCourseStatusLine(index + 1, progressLabel(title), 'WARN')
            })
            await page.close()
          } else {
            openedCount += 1
            publishProgress({
              status: 'active',
              line: formatTerminalCourseStatusLine(index + 1, progressLabel(title), 'OK')
            })
          }
        } else {
          openedCount += 1
        }
      } catch (error) {
        if (historyEnabled) throw error
        if (!page.isClosed()) await page.close()
        publishProgress({
          status: 'active',
          line: formatTerminalCourseStatusLine(index + 1, progressLabel(target.toString()), 'WARN')
        })
      }
    }
    if (!historyEnabled && openedCount === 0) {
      throw new Error('沒有成功開啟任何課程連結，請檢查登入 Cookie 或課程網址。')
    }
  } catch (error) {
    if (work.stopped) return
    publishProgress({ status: 'failed' })
    await endNetworkSession(sessionId, 'failed')
    browsers.delete(browser)
    await browser.close()
    throw error
  } finally {
    if (work.stopped || !browser.isConnected()) {
      finishSessionWork(sessionId, work)
    }
  }
}

export async function fetchReport(
  window: BrowserWindow,
  accountEmail: string,
  thresholdMinutes: number
): Promise<CourseReportRow[]> {
  const sessionId = await beginNetworkSession('direct', `學習報表 ${accountEmail}`)
  let success = false
  let apiContext: APIRequestContext | undefined
  try {
    const cookies = coolEnglishCookies(await getCookies(accountEmail)).filter(
      (cookie) => cookie.expires <= 0 || cookie.expires > Date.now() / 1000
    )
    if (!hasUsableMoodleSession(cookies)) {
      throw new Error('帳號沒有有效的 Cool English MoodleSession，請重新登入。')
    }
    const cookieHeader = cookies.map((cookie) => `${cookie.name}=${cookie.value}`).join('; ')
    const requestContext = await request.newContext({
      extraHTTPHeaders: {
        Cookie: cookieHeader,
        Referer: `${BASE_URL}/`,
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
      }
    })
    apiContext = requestContext
    const account = (await getAccounts()).find((item) => item.email === accountEmail)
    const storedUserId =
      account?.user_id && !['0', '1'].includes(account.user_id) ? account.user_id : undefined
    const getHtml = async (url: string): Promise<{ url: string; status: number; html: string }> => {
      await recordNetworkEvent(window, sessionId, {
        kind: 'request',
        method: 'GET',
        url: redactUrl(url),
        headers: { referer: `${BASE_URL}/` },
        time: new Date().toISOString()
      })
      let response
      try {
        response = await requestContext.get(url, { timeout: 30_000 })
      } catch (error) {
        await recordNetworkEvent(window, sessionId, {
          kind: 'failed',
          method: 'GET',
          url: redactUrl(url),
          message: error instanceof Error ? error.message : String(error),
          time: new Date().toISOString()
        })
        throw error
      }
      const finalUrl = response.url()
      const status = response.status()
      try {
        const rawCapture = shouldCaptureRawNetworkBodies()
        let bodyAttachmentId: string | undefined
        let bodyBytes: number | undefined
        let bodyCaptureError: string | undefined
        const contentType = response.headers()['content-type'] ?? ''
        if (rawCapture) {
          let capture: Awaited<ReturnType<typeof beginNetworkBodyCapture>> | undefined
          try {
            const body = await response.body()
            capture = await beginNetworkBodyCapture(sessionId, 'text', true)
            await capture.appendBase64(body.toString('base64'))
            bodyBytes = await capture.finish()
            if (bodyBytes) bodyAttachmentId = capture.id
            else await capture.discard()
          } catch (error) {
            bodyCaptureError = error instanceof Error ? error.message : String(error)
            await capture?.discard()
          }
        }
        await recordNetworkEvent(window, sessionId, {
          kind: 'response',
          method: 'GET',
          status,
          url: redactUrl(finalUrl),
          headers: redactHeaders(response.headers()),
          ...(rawCapture
            ? {
                bodySource: 'response',
                bodyStorage: 'raw',
                bodyContentType: contentType || '未知格式',
                bodyEncoding: bodyEncodingForContentType(contentType),
                ...(bodyAttachmentId ? { bodyAttachmentId, bodyBytes } : {}),
                ...(bodyCaptureError ? { bodyCaptureError } : {})
              }
            : {}),
          time: new Date().toISOString()
        })
        const html = await response.text()
        return { url: finalUrl, status, html }
      } finally {
        await response.dispose()
      }
    }

    let reportUrl = storedUserId
      ? `${BASE_URL}/time/time_view_detail_by_people.php?id=${encodeURIComponent(storedUserId)}`
      : ''
    let reportHtml = ''
    let reportResponseUrl = reportUrl
    let reportStatus = 0
    if (!reportUrl) {
      for (const probeUrl of [`${BASE_URL}/user/profile.php`, REPORT_URL, `${BASE_URL}/my/`]) {
        const probe = await getHtml(probeUrl)
        if (!isCoolEnglishPageUrl(probe.url) || /\/(?:login|auth)(?:\/|\.php|$)/i.test(probe.url)) {
          throw new Error('登入狀態已過期，請重新登入並更新帳號 cookie。')
        }
        if (classifyCoolEnglishTimeReport(probe.url, probe.status, probe.html) === 'expired') {
          throw timeReportValidationError('expired')
        }
        const userId =
          probe.html.match(/time_view_detail_by_people\.php\?id=(\d+)/)?.[1] ??
          probe.html.match(/["']userId["']\s*:\s*(\d+)/)?.[1] ??
          probe.html.match(/user\/profile\.php\?id=(\d+)/)?.[1]
        if (userId && !['0', '1'].includes(userId)) {
          reportUrl = `${BASE_URL}/time/time_view_detail_by_people.php?id=${userId}`
          break
        }
        if (classifyCoolEnglishTimeReport(probe.url, probe.status, probe.html) === 'valid') {
          reportUrl = probe.url
          reportHtml = probe.html
          reportResponseUrl = probe.url
          reportStatus = probe.status
          break
        }
      }
    }
    if (!reportHtml) {
      if (!reportUrl) reportUrl = REPORT_URL
      const result = await getHtml(reportUrl)
      reportResponseUrl = result.url
      reportStatus = result.status
      reportHtml = result.html
    }
    const reportState = classifyCoolEnglishTimeReport(reportResponseUrl, reportStatus, reportHtml)
    if (reportState === 'expired') throw timeReportValidationError(reportState)
    if (reportState !== 'valid') throw timeReportValidationError('unknown')
    const records = parseTimeReportRows(reportHtml, thresholdMinutes)
    if (!records.length) throw new Error('頁面沒有可讀取的學習時間資料。')
    success = true
    return records
  } finally {
    try {
      await endNetworkSession(sessionId, success ? 'completed' : 'failed')
    } finally {
      await apiContext?.dispose()
    }
  }
}

export async function checkCookie(
  window: BrowserWindow,
  email: string
): Promise<Awaited<ReturnType<typeof setCookieStatus>>> {
  const sessionId = await beginNetworkSession('headless', `Cookie 有效性檢查 ${email}`)
  const work = beginSessionWork(sessionId)
  let browser: Browser
  try {
    browser = await launchBrowser(true)
  } catch (error) {
    finishSessionWork(sessionId, work)
    await endNetworkSession(sessionId, 'failed')
    throw error
  }
  attachSessionBrowser(sessionId, browser, work)
  try {
    const context = await browser.newContext()
    trackNetwork(context, window, sessionId)
    await context.addCookies(toPlaywrightCookies(await getCookies(email)))
    const status = await validateTimeReportCookie(context, email)
    const accounts = await setCookieStatus(email, status)
    await endNetworkSession(sessionId, 'completed')
    return accounts
  } catch (error) {
    if (!work.stopped) await setCookieStatus(email, 'unknown')
    await endNetworkSession(sessionId, 'failed')
    throw error
  } finally {
    await endNetworkSession(sessionId, 'failed')
    await browser.close()
    finishSessionWork(sessionId, work)
  }
}

export async function closeBrowsers(): Promise<void> {
  await Promise.allSettled([...browsers].map((browser) => browser.close()))
  browsers.clear()
  logins.clear()
  sessionWork.clear()
}
