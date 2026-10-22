import { app, safeStorage } from 'electron'
import { copyFile, mkdir, readFile, readdir, rename, rm, stat, writeFile } from 'fs/promises'
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from 'path'
import { homedir } from 'os'
import type { AccountRecord, AppSettings, CourseBookmark, StoredCookie } from '../../shared/types'
import { isFontFamily, normalizeFontFamily } from '../../shared/fontSettings'
import { isColorThemePresetId } from '../../shared/colorThemes'
import {
  cliColorMappings,
  defaultCliReportColors,
  isCliColorValue,
  normalizeCliColor
} from '../../shared/cliReportColors'
import { parseNetscapeCookies } from '../../shared/netscapeCookies'
import { isCliAccountLoginNewer } from '../../shared/cliAccountSync'
import { cliPasswordMachineIds, decryptCliPassword } from '../../shared/cliCredentials'
import {
  parseTerminalCourseGroups,
  serializeTerminalCourseGroups,
  mergeTerminalCourseMetadata,
  normalizeCourseAlias,
  reconcileTerminalCourses
} from '../../shared/terminalCourseUrls'
import {
  normalizeSettingsCategoryOrder,
  settingsCategoryIds
} from '../../shared/settingsCategories'

const dataDir = (): string => join(app.getPath('userData'), 'data')
const accountsFile = (): string => join(dataDir(), 'accounts.json')
const cookiesDir = (): string => join(dataDir(), 'cookies')
const urlsFile = (): string => join(dataDir(), 'urls.txt')
const coursesFile = (): string => join(dataDir(), 'courses.json')
const credentialsFile = (): string => join(dataDir(), 'credentials.json')
const settingsFile = (): string => join(dataDir(), 'settings.json')
const cliColorsFile = (cliDataDirectory: string): string => join(cliDataDirectory, 'colors.json')
const defaultSettings: AppSettings = {
  colorThemeId: 'neon',
  fontSize: 13,
  terminalFontSize: 13,
  fontFamily: 'system',
  accentColor: '#54e3c2',
  terminalCursorColor: '#70f5d3',
  terminalTextColor: '#d8fff4',
  terminalBackgroundColor: '#101f20',
  textColor: '#d7fff4',
  useCustomTextColor: true,
  invertColors: false,
  theme: 'dark',
  sidebarMode: 'click',
  terminalLayout: 'vertical',
  splitRatio: 0.68,
  reportWarningColor: '#ef6b73',
  reportThresholdMinutes: 720,
  networkHistoryMode: 'keep',
  networkHistoryRetentionMinutes: 1440,
  networkCaptureRawBodies: false,
  settingsCategoryOrder: [...settingsCategoryIds],
  ...defaultCliReportColors
}

async function atomicWrite(filePath: string, content: string): Promise<void> {
  await mkdir(dirname(filePath), { recursive: true })
  const tempPath = `${filePath}.${process.pid}.${Date.now()}.tmp`
  try {
    await writeFile(tempPath, content, { encoding: 'utf8', mode: 0o600 })
    await rename(tempPath, filePath)
  } finally {
    await rm(tempPath, { force: true })
  }
}

function isInside(parent: string, candidate: string): boolean {
  const rel = relative(resolve(parent), resolve(candidate))
  return rel === '' || (!rel.startsWith(`..${sep}`) && rel !== '..' && !isAbsolute(rel))
}

function safeCookiePath(cookieFile: string): string {
  const candidate = resolve(dataDir(), cookieFile)
  if (!isInside(cookiesDir(), candidate)) {
    throw new Error('帳號 cookie 路徑不在應用程式資料夾內，已阻擋存取。')
  }
  return candidate
}

async function copyLegacyData(sourceDir: string): Promise<boolean> {
  const sourceAccounts = join(sourceDir, 'accounts.json')
  try {
    await stat(sourceAccounts)
  } catch {
    return false
  }

  const targetAccounts = accountsFile()
  try {
    await stat(targetAccounts)
    return false
  } catch {
    // Import only when no app data exists yet.
  }

  const parsed: unknown = JSON.parse(await readFile(sourceAccounts, 'utf8'))
  if (!Array.isArray(parsed)) {
    throw new Error(`舊帳號檔格式錯誤：${sourceAccounts}`)
  }
  await mkdir(cookiesDir(), { recursive: true })
  const migrated: AccountRecord[] = []
  for (const value of parsed) {
    if (!value || typeof value !== 'object') continue
    const record = value as Partial<AccountRecord>
    if (typeof record.name !== 'string' || typeof record.email !== 'string') continue
    const oldCookiePath = resolve(sourceDir, record.cookie_file ?? '')
    if (!isInside(sourceDir, oldCookiePath)) continue
    const cookieName = basename(oldCookiePath)
    const newCookiePath = join(cookiesDir(), cookieName)
    try {
      await copyFile(oldCookiePath, newCookiePath)
    } catch {
      continue
    }
    migrated.push({
      name: record.name,
      email: record.email,
      cookie_file: join('cookies', cookieName),
      ...(record.created_at ? { created_at: record.created_at } : {}),
      ...(record.last_login ? { last_login: record.last_login } : {}),
      ...(record.user_id ? { user_id: record.user_id } : {})
    })
  }
  await atomicWrite(targetAccounts, JSON.stringify(migrated, null, 2))

  const oldUrls = join(sourceDir, 'urls.txt')
  try {
    await copyFile(oldUrls, urlsFile())
  } catch {
    // Course URLs are optional.
  }
  return true
}

export async function initializeStorage(): Promise<void> {
  await mkdir(cookiesDir(), { recursive: true })
  const downloadsDir = join(homedir(), 'Downloads')
  const downloadCandidates: string[] = []
  try {
    const entries = await readdir(downloadsDir, { withFileTypes: true })
    for (const entry of entries) {
      if (!entry.isDirectory() || !/^cool-gui(?:\s*\(\d+\))?$/i.test(entry.name)) continue
      const projectDir = join(downloadsDir, entry.name)
      downloadCandidates.push(projectDir, join(projectDir, 'cool-gui'))
    }
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
  }
  const legacyCandidates = [resolve(app.getAppPath(), '..'), process.cwd(), ...downloadCandidates]
  for (const candidate of new Set(legacyCandidates)) {
    if (await copyLegacyData(candidate)) break
  }
  for (const account of await getAccounts()) {
    const cookiePath = safeCookiePath(account.cookie_file)
    try {
      await stat(cookiePath)
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') continue
      throw error
    }
    const content = await readFile(cookiePath, 'utf8')
    if (!content.startsWith('#COOL_ENCRYPTED_V1\n')) {
      if (!safeStorage.isEncryptionAvailable()) {
        throw new Error('Windows 系統加密服務不可用，無法安全升級既有 cookie。')
      }
      const encrypted = safeStorage.encryptString(content).toString('base64')
      await atomicWrite(cookiePath, `#COOL_ENCRYPTED_V1\n${encrypted}\n`)
    }
  }
}

export async function getAccounts(): Promise<AccountRecord[]> {
  try {
    const data: unknown = JSON.parse(await readFile(accountsFile(), 'utf8'))
    if (!Array.isArray(data)) throw new Error('帳號檔頂層必須是陣列。')
    const records = data.filter(
      (item): item is AccountRecord =>
        !!item &&
        typeof item.name === 'string' &&
        typeof item.email === 'string' &&
        typeof item.cookie_file === 'string'
    )
    let saved: Record<string, string> = {}
    try {
      saved = JSON.parse(await readFile(credentialsFile(), 'utf8')) as Record<string, string>
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
    }
    return records.map((account) => {
      return {
        ...account,
        hasSavedPassword: typeof saved[account.email.toLowerCase()] === 'string'
      }
    })
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return []
    throw error
  }
}

async function saveAccounts(accounts: AccountRecord[]): Promise<void> {
  await atomicWrite(accountsFile(), JSON.stringify(accounts, null, 2))
}

export async function renameAccount(email: string, name: string): Promise<AccountRecord[]> {
  const nextName = name.trim()
  if (!nextName || nextName.length > 64 || /[\\/*?:"<>|\n\t]/.test(nextName)) {
    throw new Error('名稱不可為空、超過 64 字，或包含不合法字元。')
  }

  const accounts = await getAccounts()
  const target = accounts.find((account) => account.email === email)
  if (!target) throw new Error('找不到指定帳號。')
  if (
    accounts.some(
      (account) => account !== target && account.name.toLowerCase() === nextName.toLowerCase()
    )
  ) {
    throw new Error('此帳號名稱已被使用。')
  }
  target.name = nextName
  await saveAccounts(accounts)
  return accounts
}

export async function setCookieStatus(
  email: string,
  status: 'valid' | 'expired' | 'unknown'
): Promise<AccountRecord[]> {
  const accounts = await getAccounts()
  const account = accounts.find((item) => item.email.toLowerCase() === email.toLowerCase())
  if (!account) throw new Error('找不到指定帳號。')
  account.cookieStatus = status
  account.cookieCheckedAt = new Date().toISOString()
  if (status === 'expired') account.cookieExpiredAt = account.cookieCheckedAt
  else if (status === 'valid') delete account.cookieExpiredAt
  await saveAccounts(accounts)
  return getAccounts()
}

export async function removeAccount(email: string): Promise<AccountRecord[]> {
  const accounts = await getAccounts()
  const index = accounts.findIndex((account) => account.email === email)
  if (index < 0) throw new Error('找不到指定帳號。')
  const [removed] = accounts.splice(index, 1)
  const cookiePath = safeCookiePath(removed.cookie_file)
  await saveAccounts(accounts)
  await rm(cookiePath, { force: true })
  await removeCredential(email)
  return accounts
}

export async function saveCredential(email: string, password: string): Promise<void> {
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error('Windows 系統加密服務目前不可用，為保護密碼已取消儲存。')
  }
  if (!password) throw new Error('密碼不可為空白。')
  const file = credentialsFile()
  let credentials: Record<string, string> = {}
  try {
    credentials = JSON.parse(await readFile(file, 'utf8')) as Record<string, string>
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
  }
  credentials[email.toLowerCase()] = safeStorage.encryptString(password).toString('base64')
  await atomicWrite(file, JSON.stringify(credentials, null, 2))
}

export async function getCredential(email: string): Promise<string | undefined> {
  let credentials: Record<string, string>
  try {
    credentials = JSON.parse(await readFile(credentialsFile(), 'utf8')) as Record<string, string>
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return undefined
    throw error
  }
  const encrypted = credentials[email.toLowerCase()]
  if (!encrypted) return undefined
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error('Windows 系統加密服務目前不可用，無法解密已儲存的密碼。')
  }
  return safeStorage.decryptString(Buffer.from(encrypted, 'base64'))
}

async function removeCredential(email: string): Promise<void> {
  let credentials: Record<string, string> = {}
  try {
    credentials = JSON.parse(await readFile(credentialsFile(), 'utf8')) as Record<string, string>
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return
    throw error
  }
  delete credentials[email.toLowerCase()]
  await atomicWrite(credentialsFile(), JSON.stringify(credentials, null, 2))
}

export async function readCliColors(
  cliDataDirectory: string
): Promise<Partial<Pick<AppSettings, (typeof cliColorMappings)[number][1]>>> {
  let parsed: unknown
  try {
    parsed = JSON.parse(await readFile(cliColorsFile(cliDataDirectory), 'utf8'))
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return {}
    throw error
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('CLI 顏色設定檔格式錯誤。')
  }
  const raw = parsed as Record<string, unknown>
  const values: Partial<Pick<AppSettings, (typeof cliColorMappings)[number][1]>> = {}
  for (const [cliKey, appKey] of cliColorMappings) {
    const value = raw[cliKey]
    if (!isCliColorValue(value)) continue
    if (appKey.startsWith('terminal') && !/^#[0-9a-f]{6}$/i.test(value)) continue
    Object.assign(values, { [appKey]: normalizeCliColor(value) })
  }
  return values
}

async function writeCliColors(cliDataDirectory: string, settings: AppSettings): Promise<void> {
  const file = cliColorsFile(cliDataDirectory)
  let colors: Record<string, unknown> = {}
  try {
    const parsed: unknown = JSON.parse(await readFile(file, 'utf8'))
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('CLI 顏色設定檔格式錯誤。')
    }
    colors = parsed as Record<string, unknown>
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
  }
  for (const [cliKey, appKey] of cliColorMappings) {
    colors[cliKey] = normalizeCliColor(settings[appKey])
  }
  await atomicWrite(file, JSON.stringify(colors, null, 2))
}

export async function getSettings(cliDataDirectory?: string): Promise<AppSettings> {
  let merged: AppSettings
  let initializeSettings = false
  try {
    const settings: unknown = JSON.parse(await readFile(settingsFile(), 'utf8'))
    if (!settings || typeof settings !== 'object' || Array.isArray(settings)) {
      throw new Error('設定檔格式錯誤。')
    }
    const storedSettings = settings as Partial<AppSettings>
    if (
      JSON.stringify(normalizeSettingsCategoryOrder(storedSettings.settingsCategoryOrder)) !==
      JSON.stringify(storedSettings.settingsCategoryOrder)
    ) {
      initializeSettings = true
    }
    merged = { ...defaultSettings, ...storedSettings }
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
    merged = { ...defaultSettings }
    initializeSettings = true
  }
  for (const [cliKey, appKey] of cliColorMappings) {
    const value = merged[appKey]
    const isTerminalColor = cliKey.startsWith('terminal_')
    const normalized =
      isCliColorValue(value) && (!isTerminalColor || /^#[0-9a-f]{6}$/i.test(value))
        ? normalizeCliColor(value)
        : defaultSettings[appKey]
    Object.assign(merged, { [appKey]: normalized })
  }
  if (!['keep', 'expire', 'disabled'].includes(merged.networkHistoryMode)) {
    merged.networkHistoryMode = defaultSettings.networkHistoryMode
  }
  if (
    !Number.isSafeInteger(merged.networkHistoryRetentionMinutes) ||
    merged.networkHistoryRetentionMinutes < 1 ||
    merged.networkHistoryRetentionMinutes > 52_560_000
  ) {
    merged.networkHistoryRetentionMinutes = defaultSettings.networkHistoryRetentionMinutes
  }
  if (!['click', 'hover'].includes(merged.sidebarMode)) {
    merged.sidebarMode = defaultSettings.sidebarMode
  }
  if (typeof merged.networkCaptureRawBodies !== 'boolean') {
    merged.networkCaptureRawBodies = defaultSettings.networkCaptureRawBodies
  }
  merged.settingsCategoryOrder = normalizeSettingsCategoryOrder(merged.settingsCategoryOrder)
  if (cliDataDirectory) {
    const cliColors = await readCliColors(cliDataDirectory)
    const synced = { ...merged, ...cliColors }
    if (
      cliColorMappings.some(([, key]) => merged[key] !== synced[key]) ||
      Object.keys(cliColors).length !== cliColorMappings.length
    ) {
      await writeCliColors(cliDataDirectory, synced)
    }
    if (initializeSettings || cliColorMappings.some(([, key]) => merged[key] !== synced[key])) {
      await atomicWrite(settingsFile(), JSON.stringify(synced, null, 2))
    }
    merged = synced
  } else if (initializeSettings) {
    await atomicWrite(settingsFile(), JSON.stringify(merged, null, 2))
  }
  return {
    ...merged,
    colorThemeId: isColorThemePresetId(merged.colorThemeId) ? merged.colorThemeId : 'custom',
    fontFamily: normalizeFontFamily(merged.fontFamily)
  }
}

export async function saveSettings(
  settings: AppSettings,
  cliDataDirectory?: string
): Promise<AppSettings> {
  if (
    !Number.isInteger(settings.fontSize) ||
    settings.fontSize < 10 ||
    settings.fontSize > 24 ||
    (settings.colorThemeId !== 'custom' && !isColorThemePresetId(settings.colorThemeId)) ||
    !Number.isInteger(settings.terminalFontSize) ||
    settings.terminalFontSize < 10 ||
    settings.terminalFontSize > 24 ||
    !isFontFamily(settings.fontFamily) ||
    !/^#[0-9a-f]{6}$/i.test(settings.accentColor) ||
    !/^#[0-9a-f]{6}$/i.test(settings.terminalCursorColor) ||
    !/^#[0-9a-f]{6}$/i.test(settings.terminalTextColor) ||
    !/^#[0-9a-f]{6}$/i.test(settings.terminalBackgroundColor) ||
    !/^#[0-9a-f]{6}$/i.test(settings.textColor) ||
    cliColorMappings.some(
      ([cliKey, appKey]) =>
        !isCliColorValue(settings[appKey]) ||
        (cliKey.startsWith('terminal_') && !/^#[0-9a-f]{6}$/i.test(settings[appKey]))
    ) ||
    typeof settings.useCustomTextColor !== 'boolean' ||
    typeof settings.invertColors !== 'boolean' ||
    !/^#[0-9a-f]{6}$/i.test(settings.reportWarningColor) ||
    !['dark', 'light'].includes(settings.theme) ||
    !['click', 'hover'].includes(settings.sidebarMode) ||
    !['vertical', 'horizontal'].includes(settings.terminalLayout) ||
    !Number.isFinite(settings.splitRatio) ||
    settings.splitRatio < 0.3 ||
    settings.splitRatio > 0.8 ||
    !Number.isInteger(settings.reportThresholdMinutes) ||
    settings.reportThresholdMinutes < 1 ||
    settings.reportThresholdMinutes > 1440 ||
    !['keep', 'expire', 'disabled'].includes(settings.networkHistoryMode) ||
    typeof settings.networkCaptureRawBodies !== 'boolean' ||
    !Array.isArray(settings.settingsCategoryOrder) ||
    JSON.stringify(normalizeSettingsCategoryOrder(settings.settingsCategoryOrder)) !==
      JSON.stringify(settings.settingsCategoryOrder) ||
    !Number.isSafeInteger(settings.networkHistoryRetentionMinutes) ||
    settings.networkHistoryRetentionMinutes < 1 ||
    settings.networkHistoryRetentionMinutes > 52_560_000
  ) {
    throw new Error('設定值不合法，請檢查字體、顏色、版面比例與報表門檻。')
  }
  await atomicWrite(settingsFile(), JSON.stringify(settings, null, 2))
  if (cliDataDirectory) await writeCliColors(cliDataDirectory, settings)
  return settings
}

export async function saveLogin(
  email: string,
  displayName: string,
  cookies: StoredCookie[],
  userId?: string
): Promise<AccountRecord[]> {
  const host = 'www.coolenglish.edu.tw'
  const valid = cookies.filter((cookie) => {
    const domain = cookie.domain.replace(/^\./, '').toLowerCase()
    return domain === host || domain === 'coolenglish.edu.tw'
  })
  if (
    !valid.some(
      (cookie) =>
        cookie.name === 'MoodleSession' &&
        cookie.value.length > 0 &&
        (cookie.expires <= 0 || cookie.expires > Date.now() / 1000)
    )
  ) {
    throw new Error('尚未取得有效的 MoodleSession，請先在登入視窗完成登入。')
  }
  const cookieName = `${Buffer.from(email).toString('base64url').slice(0, 48)}.txt`
  const cookiePath = join(cookiesDir(), cookieName)
  const lines = [
    '# Netscape HTTP Cookie File',
    '# Generated by cool desktop app; keep private.',
    ...valid.map((cookie) => {
      const domain = cookie.domain.replace(/[\t\r\n]/g, ' ').trim()
      const name = cookie.name.replace(/[\t\r\n ]/g, '_')
      const value = cookie.value.replace(/[\t\r\n]/g, ' ')
      const path = cookie.path.replace(/[\t\r\n]/g, ' ') || '/'
      const includeSubdomains = domain.startsWith('.')
      const expiry = cookie.expires > 0 ? Math.floor(cookie.expires) : 0
      const line = `${domain}\t${includeSubdomains ? 'TRUE' : 'FALSE'}\t${path}\t${cookie.secure ? 'TRUE' : 'FALSE'}\t${expiry}\t${name}\t${value}`
      return cookie.httpOnly ? `#HttpOnly_${line}` : line
    })
  ]
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error('Windows 系統加密服務目前不可用，為保護 cookie 已取消儲存。')
  }
  const serializedCookies = `${lines.join('\n')}\n`
  const expires = valid
    .filter(
      (cookie) =>
        cookie.name === 'MoodleSession' &&
        cookie.value.length > 0 &&
        cookie.expires > Date.now() / 1000
    )
    .map((cookie) => cookie.expires)
  const cookieExpiresAt = expires.length
    ? new Date(Math.min(...expires) * 1000).toISOString()
    : null
  await atomicWrite(
    cookiePath,
    `#COOL_ENCRYPTED_V1\n${safeStorage.encryptString(serializedCookies).toString('base64')}\n`
  )

  const accounts = await getAccounts()
  const existing = accounts.find((account) => account.email.toLowerCase() === email.toLowerCase())
  const now = new Date().toISOString().slice(0, 19)
  if (existing) {
    existing.name = displayName.trim() || existing.name
    existing.cookie_file = join('cookies', cookieName)
    existing.last_login = now
    existing.cookieObtainedAt = new Date().toISOString()
    existing.cookieExpiresAt = cookieExpiresAt
    existing.cookieStatus = 'valid'
    existing.cookieCheckedAt = new Date().toISOString()
    if (userId) existing.user_id = userId
  } else {
    const baseName = displayName.trim() || email.split('@')[0]
    let name = baseName
    let suffix = 2
    while (accounts.some((account) => account.name.toLowerCase() === name.toLowerCase())) {
      name = `${baseName}${suffix++}`
    }
    accounts.push({
      name,
      email,
      cookie_file: join('cookies', cookieName),
      created_at: now,
      last_login: now,
      cookieObtainedAt: new Date().toISOString(),
      cookieExpiresAt,
      cookieStatus: 'valid',
      cookieCheckedAt: new Date().toISOString(),
      ...(userId ? { user_id: userId } : {})
    })
  }
  await saveAccounts(accounts)
  return accounts
}

export async function syncCliAccounts(sourceDir: string): Promise<string[]> {
  const sourceAccountsPath = join(sourceDir, 'accounts.json')
  let sourceAccounts: unknown
  try {
    sourceAccounts = JSON.parse(await readFile(sourceAccountsPath, 'utf8'))
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return []
    throw error
  }
  if (!Array.isArray(sourceAccounts)) {
    throw new Error('終端帳號檔格式錯誤，無法同步帳號。')
  }

  const savedAccounts = await getAccounts()
  const changedEmails: string[] = []
  for (const item of sourceAccounts) {
    if (!item || typeof item !== 'object') continue
    const sourceAccount = item as Record<string, unknown>
    const {
      name,
      email,
      cookie_file: cookieFile,
      last_login: lastLogin,
      user_id: userId,
      password_enc: passwordEnc,
      password_len: passwordLength
    } = sourceAccount
    if (typeof name !== 'string' || typeof email !== 'string' || typeof cookieFile !== 'string') {
      continue
    }
    const sourceCookiePath = resolve(sourceDir, cookieFile)
    if (!isInside(sourceDir, sourceCookiePath)) {
      throw new Error(`終端帳號 ${email} 的 cookie 路徑不合法，已阻止同步。`)
    }
    const sourceStat = await stat(sourceCookiePath).catch((error: unknown) => {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') return undefined
      throw error
    })
    if (!sourceStat?.isFile()) continue

    const existing = savedAccounts.find(
      (account) => account.email.toLowerCase() === email.toLowerCase()
    )
    const savedTimestamp = existing ? Date.parse(existing.last_login ?? '') || 0 : 0
    let changed = false
    // accounts.json is rewritten when any account changes; use each account's
    // own login timestamp so another account's login cannot refresh this cookie.
    const accountWasLoggedInAgain = isCliAccountLoginNewer(lastLogin, savedTimestamp)
    if (!existing || accountWasLoggedInAgain) {
      const text = await readFile(sourceCookiePath, 'utf8')
      if (text.startsWith('#COOL_ENCRYPTED_V1')) {
        throw new Error(`終端帳號 ${email} 的 cookie 格式不支援同步。`)
      }
      const cookies = parseNetscapeCookies(text)
      await saveLogin(email, name, cookies, typeof userId === 'string' ? userId : undefined)
      changed = true
    }

    if (
      typeof passwordEnc === 'string' &&
      (typeof passwordLength !== 'number' ||
        !Number.isInteger(passwordLength) ||
        passwordLength < 1 ||
        passwordLength > 512)
    ) {
      throw new Error(`終端帳號 ${email} 的已保存密碼資料不完整，無法安全同步。`)
    }
    if (typeof passwordEnc === 'string') {
      const hasDesktopPassword = await getCredential(email)
      if (!hasDesktopPassword || accountWasLoggedInAgain) {
        const password = decryptCliPassword(
          passwordEnc,
          typeof passwordLength === 'number' ? passwordLength : undefined,
          await cliPasswordMachineIds()
        )
        await saveCredential(email, password)
        changed = true
      }
    }
    if (changed) changedEmails.push(email)
  }
  return [...new Set(changedEmails)]
}

export async function syncDesktopAccountsToCli(targetDir: string): Promise<void> {
  const cliAccountsPath = join(targetDir, 'accounts.json')
  let cliAccounts: unknown = []
  try {
    cliAccounts = JSON.parse(await readFile(cliAccountsPath, 'utf8'))
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
  }
  if (!Array.isArray(cliAccounts)) {
    throw new Error('終端帳號檔格式錯誤，無法同步桌面帳號。')
  }

  const accounts = await getAccounts()
  const nextCliAccounts = [...cliAccounts]
  for (const account of accounts) {
    const encryptedPath = safeCookiePath(account.cookie_file)
    let cookies = await readFile(encryptedPath, 'utf8')
    if (cookies.startsWith('#COOL_ENCRYPTED_V1\n')) {
      if (!safeStorage.isEncryptionAvailable()) {
        throw new Error('Windows 系統加密服務目前不可用，無法同步桌面帳號 Cookie。')
      }
      const encoded = cookies.split(/\r?\n/)[1]
      if (!encoded) throw new Error(`帳號 ${account.email} 的加密 Cookie 格式錯誤。`)
      cookies = safeStorage.decryptString(Buffer.from(encoded, 'base64'))
    } else {
      throw new Error(`帳號 ${account.email} 的 Cookie 尚未加密，已阻止同步。`)
    }

    const matchIndex = nextCliAccounts.findIndex(
      (item) =>
        !!item &&
        typeof item === 'object' &&
        typeof (item as Record<string, unknown>).email === 'string' &&
        ((item as Record<string, unknown>).email as string).toLowerCase() ===
          account.email.toLowerCase()
    )
    const existing =
      matchIndex >= 0 ? (nextCliAccounts[matchIndex] as Record<string, unknown>) : undefined
    const existingCookiePathValue = existing?.cookie_file
    const existingCookiePath =
      typeof existingCookiePathValue === 'string'
        ? resolve(targetDir, existingCookiePathValue)
        : undefined
    const currentCookiePath =
      typeof existingCookiePathValue === 'string' &&
      existingCookiePath &&
      isInside(join(targetDir, 'cookies'), existingCookiePath)
        ? existingCookiePathValue
        : join(
            'cookies',
            `desktop-${Buffer.from(account.email).toString('base64url').slice(0, 48)}.txt`
          )
    const cliCookiePath = resolve(targetDir, currentCookiePath)
    if (!isInside(join(targetDir, 'cookies'), cliCookiePath)) {
      throw new Error(`終端帳號 ${account.email} 的 Cookie 路徑不在 cookies 目錄內。`)
    }
    let existingCookie = ''
    try {
      existingCookie = await readFile(cliCookiePath, 'utf8')
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
    }
    if (existingCookie !== cookies) await atomicWrite(cliCookiePath, cookies)

    const updated = {
      ...(existing ?? {}),
      name: account.name,
      email: account.email,
      cookie_file: currentCookiePath,
      ...(account.created_at ? { created_at: account.created_at } : {}),
      ...(account.last_login ? { last_login: account.last_login } : {}),
      ...(account.user_id ? { user_id: account.user_id } : {})
    }
    if (matchIndex >= 0) nextCliAccounts[matchIndex] = updated
    else nextCliAccounts.push(updated)
  }
  if (JSON.stringify(nextCliAccounts) !== JSON.stringify(cliAccounts)) {
    await atomicWrite(cliAccountsPath, JSON.stringify(nextCliAccounts, null, 2))
  }
}

export async function removeCliAccount(email: string, targetDir: string): Promise<void> {
  const cliAccountsPath = join(targetDir, 'accounts.json')
  let cliAccounts: unknown
  try {
    cliAccounts = JSON.parse(await readFile(cliAccountsPath, 'utf8'))
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return
    throw error
  }
  if (!Array.isArray(cliAccounts)) {
    throw new Error('終端帳號檔格式錯誤，無法同步帳號移除。')
  }

  const removed = cliAccounts.filter(
    (item) =>
      !!item &&
      typeof item === 'object' &&
      typeof (item as Record<string, unknown>).email === 'string' &&
      ((item as Record<string, unknown>).email as string).toLowerCase() === email.toLowerCase()
  ) as Array<Record<string, unknown>>
  const remaining = cliAccounts.filter((item) => !removed.includes(item))
  const referencedCookiePaths = new Set(
    remaining.flatMap((item) =>
      item &&
      typeof item === 'object' &&
      typeof (item as Record<string, unknown>).cookie_file === 'string'
        ? [resolve(targetDir, (item as Record<string, unknown>).cookie_file as string)]
        : []
    )
  )
  for (const account of removed) {
    if (typeof account.cookie_file !== 'string') continue
    const cookiePath = resolve(targetDir, account.cookie_file)
    if (
      isInside(join(targetDir, 'cookies'), cookiePath) &&
      !referencedCookiePaths.has(cookiePath)
    ) {
      await rm(cookiePath, { force: true })
    }
  }
  await atomicWrite(cliAccountsPath, JSON.stringify(remaining, null, 2))
}

export async function getCookies(
  email: string
): Promise<Array<StoredCookie & { sameSite: 'Lax' }>> {
  const account = (await getAccounts()).find((item) => item.email === email)
  if (!account) throw new Error('找不到指定帳號。')
  let text = await readFile(safeCookiePath(account.cookie_file), 'utf8')
  if (text.startsWith('#COOL_ENCRYPTED_V1\n')) {
    if (!safeStorage.isEncryptionAvailable()) {
      throw new Error('Windows 系統加密服務目前不可用，無法解密帳號 cookie。')
    }
    text = safeStorage.decryptString(Buffer.from(text.split(/\r?\n/)[1], 'base64'))
  } else {
    if (!safeStorage.isEncryptionAvailable()) {
      throw new Error('Windows 系統加密服務不可用，無法安全讀取既有 cookie。')
    }
    text = text.replace(/^\uFEFF/, '')
    const encrypted = safeStorage.encryptString(text).toString('base64')
    await atomicWrite(safeCookiePath(account.cookie_file), `#COOL_ENCRYPTED_V1\n${encrypted}\n`)
  }
  return text.split(/\r?\n/).flatMap((line) => {
    if (!line || (line.startsWith('#') && !line.startsWith('#HttpOnly_'))) return []
    const normalized = line.startsWith('#HttpOnly_') ? line.slice('#HttpOnly_'.length) : line
    const parts = normalized.split('\t')
    if (parts.length < 7) return []
    const expiry = Number.parseInt(parts[4], 10)
    return [
      {
        name: parts[5],
        value: parts.slice(6).join('\t'),
        domain: parts[0].replace(/^\./, ''),
        path: parts[2] || '/',
        secure: parts[3].toUpperCase() === 'TRUE',
        httpOnly: line.startsWith('#HttpOnly_'),
        expires: Number.isFinite(expiry) && expiry > 0 ? expiry : -1,
        sameSite: 'Lax' as const
      }
    ]
  })
}

export async function getCourses(): Promise<CourseBookmark[]> {
  try {
    const parsed: unknown = JSON.parse(await readFile(coursesFile(), 'utf8'))
    if (!Array.isArray(parsed)) throw new Error('課程資料檔格式錯誤。')
    const courses = parsed.filter(
      (item): item is CourseBookmark =>
        !!item &&
        typeof item === 'object' &&
        typeof item.url === 'string' &&
        typeof item.category === 'string'
    )
    const normalized = courses.map((item) => ({
      ...item,
      alias: normalizeCourseAlias(item.category, item.alias)
    }))
    if (normalized.some((item, index) => item.alias !== courses[index].alias)) {
      await atomicWrite(coursesFile(), JSON.stringify(normalized, null, 2))
    }
    return normalized
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
  }

  let legacyUrls: string[] = []
  try {
    legacyUrls = (await readFile(urlsFile(), 'utf8'))
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => /^https?:\/\//i.test(line))
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
  }
  const migrated = [...new Set(legacyUrls)].map((url) => ({ url, category: '未分類' }))
  await atomicWrite(coursesFile(), JSON.stringify(migrated, null, 2))
  return migrated
}

async function saveCourses(courses: CourseBookmark[]): Promise<CourseBookmark[]> {
  const cleaned = courses
    .filter((course, index) => courses.findIndex((item) => item.url === course.url) === index)
    .map((course) => ({ ...course, alias: course.alias?.trim() || course.category }))
  for (const { url, category } of cleaned) {
    let parsed: URL
    try {
      parsed = new URL(url)
    } catch {
      throw new Error(`無效網址：${url}`)
    }
    if (!['http:', 'https:'].includes(parsed.protocol))
      throw new Error('只接受 http 或 https 網址。')
    if (!category.trim() || category.length > 64) {
      throw new Error('課程分類不可空白，且不得超過 64 個字元。')
    }
    const alias = cleaned.find((course) => course.url === url)?.alias
    if (!alias?.trim() || alias.length > 64) {
      throw new Error('連結別名不可空白，且不得超過 64 個字元。')
    }
  }
  await atomicWrite(coursesFile(), JSON.stringify(cleaned, null, 2))
  return cleaned
}

export async function addCourses(
  urls: string[],
  category: string,
  alias: string
): Promise<CourseBookmark[]> {
  const current = await getCourses()
  const normalizedCategory = category.trim() || '未分類'
  const normalizedAlias = alias.trim() || normalizedCategory
  return saveCourses([
    ...current,
    ...urls.map((url) => ({
      url: url.trim(),
      category: normalizedCategory,
      alias: normalizedAlias
    }))
  ])
}

export async function setCourseCategory(url: string, category: string): Promise<CourseBookmark[]> {
  const normalizedCategory = category.trim()
  if (!normalizedCategory || normalizedCategory.length > 64) {
    throw new Error('課程分類不可空白，且不得超過 64 個字元。')
  }
  const current = await getCourses()
  const target = current.find((course) => course.url === url)
  if (!target) throw new Error('找不到指定課程網址。')
  const previousCategory = target.category
  target.category = normalizedCategory
  if (target.alias === previousCategory) target.alias = normalizedCategory
  return saveCourses(current)
}

export async function removeCourse(url: string): Promise<CourseBookmark[]> {
  const current = await getCourses()
  return saveCourses(current.filter((course) => course.url !== url))
}

export async function importCliCourseUrls(cliDataDirectory: string): Promise<void> {
  const cliUrlsPath = join(cliDataDirectory, 'urls.txt')
  let cliGroups: Array<{ name: string; urls: string[] }> = []
  try {
    cliGroups = parseTerminalCourseGroups(await readFile(cliUrlsPath, 'utf8'))
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
  }
  if (!cliGroups.length) return
  const courses = await getCourses()
  const courseByUrl = new Map(courses.map((course) => [course.url, course]))
  for (const group of cliGroups) {
    for (const url of group.urls) {
      const current = courseByUrl.get(url)
      const metadata = mergeTerminalCourseMetadata(
        current ? { category: current.category, alias: current.alias } : undefined,
        group
      )
      courseByUrl.set(url, { url, ...metadata })
    }
  }
  await saveCourses([...courseByUrl.values()])
}

export async function syncCliCourseUrls(
  cliDataDirectory: string,
  previousContents: string
): Promise<CourseBookmark[]> {
  const cliUrlsPath = join(cliDataDirectory, 'urls.txt')
  let currentContents: string
  try {
    currentContents = await readFile(cliUrlsPath, 'utf8')
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return getCourses()
    throw error
  }
  const reconciled = reconcileTerminalCourses(await getCourses(), previousContents, currentContents)
  return saveCourses(reconciled)
}

export async function initializeCliCourseUrls(cliDataDirectory: string): Promise<void> {
  await importCliCourseUrls(cliDataDirectory)
  await writeCliCourseUrls(cliDataDirectory)
}

export async function writeCliCourseUrls(cliDataDirectory: string): Promise<string> {
  const courses = await getCourses()
  const groups = new Map<string, { name: string; category: string; urls: string[] }>()
  for (const course of courses) {
    const name = course.alias?.trim() || course.category
    const key = JSON.stringify([course.category, name])
    const group = groups.get(key) ?? { name, category: course.category, urls: [] }
    group.urls.push(course.url)
    groups.set(key, group)
  }
  const contents = serializeTerminalCourseGroups([...groups.values()])
  await atomicWrite(join(cliDataDirectory, 'urls.txt'), contents)
  return contents
}
