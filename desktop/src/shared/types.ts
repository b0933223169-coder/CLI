export interface AccountRecord {
  name: string
  email: string
  cookie_file: string
  created_at?: string
  last_login?: string
  user_id?: string
  cookieObtainedAt?: string
  cookieExpiresAt?: string | null
  cookieExpiredAt?: string
  cookieStatus?: 'valid' | 'expired' | 'unknown'
  cookieCheckedAt?: string
  hasSavedPassword?: boolean
}

export interface CourseReportRow {
  month: string
  platformTime: string
  videoTime: string
  practiceTime: string
  isBelowThreshold?: boolean
}

export interface CourseBookmark {
  url: string
  category: string
  alias?: string
}

export interface StoredCookie {
  name: string
  value: string
  domain: string
  path: string
  secure: boolean
  httpOnly: boolean
  expires: number
}

export interface AppSettings {
  colorThemeId: string
  fontSize: number
  terminalFontSize: number
  fontFamily: FontFamily
  accentColor: string
  terminalCursorColor: string
  terminalTextColor: string
  terminalBackgroundColor: string
  textColor: string
  useCustomTextColor: boolean
  invertColors: boolean
  theme: 'dark' | 'light'
  sidebarMode: 'click' | 'hover'
  terminalLayout: 'vertical' | 'horizontal'
  splitRatio: number
  reportWarningColor: string
  reportThresholdMinutes: number
  networkHistoryMode: 'keep' | 'expire' | 'disabled'
  networkHistoryRetentionMinutes: number
  networkCaptureRawBodies: boolean
  settingsCategoryOrder: string[]
  cliReportTitleColor: string
  cliReportTitleTextColor: string
  cliReportHeaderColor: string
  cliReportCurrentColor: string
  cliReportBelowColor: string
  cliReportUrlColor: string
  cliReportSeparatorColor: string
}

export interface TerminalProfile {
  id: string
  label: string
  command: string
  args: string[]
  cwd?: string
}

export interface TerminalSessionInfo {
  id: string
  profileId: string
  label: string
}

export interface NetworkEvent {
  sessionId: string
  sessionLabel: string
  mode: NetworkMode
  kind: 'request' | 'response' | 'failed'
  method?: string
  status?: number
  url: string
  message?: string
  headers?: Record<string, string>
  bodyPreview?: string
  bodyAttachmentId?: string
  bodySource?: 'request' | 'response'
  bodyStorage?: 'encrypted' | 'raw'
  bodyContentType?: string
  bodyEncoding?: 'text' | 'hex'
  bodyBytes?: number
  bodyCaptureError?: string
  time: string
}

export interface NetworkSession {
  id: string
  label: string
  mode: NetworkMode
  startedAt: string
  endedAt?: string
  status: 'active' | 'completed' | 'failed' | 'stopped'
  events: NetworkEvent[]
  eventCount?: number
}

export interface NetworkSessionSummary {
  id: string
  label: string
  mode: NetworkMode
  startedAt: string
  endedAt?: string
  status: 'active' | 'completed' | 'failed' | 'stopped'
  eventCount: number
}

export type LoginMode = 'headed' | 'headless'
export type NetworkMode = LoginMode | 'direct'

export interface CourseProgressUpdate {
  sessionId: string
  mode: LoginMode
  label: string
  status: 'active' | 'completed' | 'failed' | 'stopped'
  line?: string
}

export type FontFamily = 'system' | 'segoe' | 'arial' | 'consolas'

export interface CoolApi {
  terminal: {
    profiles: () => Promise<TerminalProfile[]>
    start: (profileId: string) => Promise<TerminalSessionInfo>
    ready: (terminalId: string) => void
    stop: (terminalId: string) => void
    write: (terminalId: string, data: string) => void
    resize: (terminalId: string, columns: number, rows: number) => void
    onData: (callback: (terminalId: string, data: string) => void) => () => void
    onExit: (callback: (terminalId: string, code: number) => void) => () => void
  }
  accounts: {
    list: () => Promise<AccountRecord[]>
    onLoginSuccess: (callback: (email: string) => void) => () => void
    onLoginInteractionRequired: (callback: (message: string) => void) => () => void
    onLoginStatus: (callback: (message: string) => void) => () => void
    onCliSync: (callback: (emails: string[]) => void) => () => void
    onCliSyncError: (callback: (message: string) => void) => () => void
    rename: (email: string, name: string) => Promise<AccountRecord[]>
    remove: (email: string) => Promise<AccountRecord[]>
    login: (
      email: string,
      password: string,
      name: string,
      mode: LoginMode
    ) => Promise<AccountRecord[]>
    loginSaved: (email: string, mode: LoginMode) => Promise<AccountRecord[]>
    checkCookie: (email: string) => Promise<AccountRecord[]>
  }
  courses: {
    list: () => Promise<CourseBookmark[]>
    onCliSync: (callback: (courses: CourseBookmark[]) => void) => () => void
    onCliSyncError: (callback: (message: string) => void) => () => void
    add: (urls: string[], category: string, alias: string) => Promise<CourseBookmark[]>
    setCategory: (url: string, category: string) => Promise<CourseBookmark[]>
    remove: (url: string) => Promise<CourseBookmark[]>
    open: (urls: string[], accountEmail: string, mode: LoginMode, label: string) => Promise<void>
  }
  reports: {
    fetch: (accountEmail: string, thresholdMinutes: number) => Promise<CourseReportRow[]>
  }
  events: {
    onNetwork: (callback: (event: NetworkEvent) => void) => () => void
    onSession: (callback: (session: NetworkSessionSummary) => void) => () => void
    onHistoryChanged: (callback: () => void) => () => void
    onCourseProgress: (callback: (update: CourseProgressUpdate) => void) => () => void
    list: () => Promise<NetworkSession[]>
    remove: (sessionIds: string[]) => Promise<NetworkSession[]>
    export: (sessionId: string) => Promise<{ canceled: boolean; filePath?: string }>
    openBody: (sessionId: string, bodyAttachmentId: string) => Promise<void>
    stop: (sessionId: string) => Promise<void>
  }
  settings: {
    get: () => Promise<AppSettings>
    save: (settings: AppSettings) => Promise<AppSettings>
    onCliColors: (callback: (colors: Partial<AppSettings>) => void) => () => void
    onCliColorsError: (callback: (message: string) => void) => () => void
  }
  clipboard: {
    read: () => Promise<string>
    write: (text: string) => void
  }
  app: {
    version: string
    openExternal: (url: string) => void
    minimize: () => void
    toggleMaximize: () => void
    close: () => void
  }
}
