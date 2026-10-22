import {
  Activity,
  ArrowLeft,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Command,
  Download,
  ExternalLink,
  FileClock,
  FolderOpen,
  Globe2,
  LayoutDashboard,
  LogIn,
  LoaderCircle,
  LockKeyhole,
  MoreHorizontal,
  Palette,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  TerminalSquare,
  Trash2,
  UserRound,
  UsersRound,
  X
} from 'lucide-react'
import {
  FormEvent,
  Fragment,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react'
import type {
  AccountRecord,
  AppSettings,
  CourseBookmark,
  CourseProgressUpdate,
  CourseReportRow,
  LoginMode,
  NetworkEvent,
  NetworkMode,
  NetworkSession
} from '../../shared/types'
import { fontFamilyStack, normalizeFontFamily } from '../../shared/fontSettings'
import { colorThemePresets, getColorThemePreset } from '../../shared/colorThemes'
import {
  cliColorInputValue,
  cliColorPreview,
  cliColorSwatch,
  cliIndexedBackgroundColors,
  cliIndexedForegroundColors,
  cliReportColorFields,
  cliReportColorPresets,
  defaultCliReportColors,
  type CliReportColorSetting
} from '../../shared/cliReportColors'
import {
  normalizeSettingsCategoryOrder,
  type SettingsCategoryId
} from '../../shared/settingsCategories'
import {
  TERMINAL_LAYOUT_RESIZE_END_EVENT,
  TERMINAL_LAYOUT_RESIZE_START_EVENT
} from '../../shared/terminalResize'
import { TerminalPanel } from './components/TerminalPanel'
import appIcon from './assets/app-icon.png'

type Page = 'home' | 'accounts' | 'courses' | 'reports' | 'network' | 'settings'
type AccountLoginPrompt = {
  email: string
  name: string
  mode: LoginMode
} | null

const navItems: { id: Page; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'home', label: '工作台', icon: LayoutDashboard },
  { id: 'accounts', label: '帳號', icon: UsersRound },
  { id: 'courses', label: '課程網址', icon: BookOpen },
  { id: 'reports', label: '學習報表', icon: FileClock },
  { id: 'network', label: '網路紀錄', icon: Globe2 }
]

const welcomeMessages = [
  '早安，準備好開始了嗎？',
  '今天也替自己留一點學習時間吧。',
  '從一堂課開始，慢慢累積進步。',
  '準備好了嗎？今天的目標由你決定。',
  '每一次練習，都讓下一步更踏實。',
  '新的一天，來替知識加一點點。',
  '不必趕路，穩穩學習也很棒。',
  '今天想先探索哪一門課呢？',
  '一點一滴的努力，都值得被記下。',
  '給自己一段專心學習的時間吧。',
  '準備出發了嗎？你的學習工作台已就緒。',
  '打開課程，讓好奇心帶路。',
  '今天的進步，從現在這一步開始。',
  '保持節奏，你正在累積真正的實力。',
  '想學的事情，就從今天開始吧。',
  '來看看今天能完成什麼小目標。',
  '專注當下，讓每分鐘都成為收穫。',
  '又是適合學點新東西的一天。',
  '循序漸進，也能走得很遠。',
  '課程與進度都在這裡，準備開始吧。',
  '你已經準備好，向前多學一點。',
  '帶著好奇心，開始今天的學習。',
  '每個小小的開始，都可能帶來大進步。',
  '今天也為自己的努力喝采。'
]

function getWelcomeMessage(): string {
  const day = Math.floor(Date.now() / 86_400_000)
  return welcomeMessages[day % welcomeMessages.length]
}

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
  settingsCategoryOrder: [
    'appearance',
    'terminal',
    'workspace',
    'reports',
    'cli-report-colors',
    'network-history',
    'privacy'
  ],
  ...defaultCliReportColors
}

function reportColorPatch(key: CliReportColorSetting, value: string): Partial<AppSettings> {
  switch (key) {
    case 'cliReportTitleColor':
      return { cliReportTitleColor: value }
    case 'cliReportTitleTextColor':
      return { cliReportTitleTextColor: value }
    case 'cliReportHeaderColor':
      return { cliReportHeaderColor: value }
    case 'cliReportCurrentColor':
      return { cliReportCurrentColor: value }
    case 'cliReportBelowColor':
      return { cliReportBelowColor: value }
    case 'cliReportUrlColor':
      return { cliReportUrlColor: value }
    case 'cliReportSeparatorColor':
      return { cliReportSeparatorColor: value }
  }
}

function CliColorMenu({
  label,
  value,
  settings,
  onChange
}: {
  label: string
  value: string
  settings: AppSettings
  onChange: (value: string) => void
}): React.JSX.Element {
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const options = [
    ...cliReportColorPresets.map((name) => ({ name, group: '基本色與特殊樣式' })),
    ...cliIndexedForegroundColors.map((name) => ({ name, group: '256 色前景' })),
    ...cliIndexedBackgroundColors.map((name) => ({ name, group: '256 色背景' }))
  ]
  const swatchStyle = (name: string): React.CSSProperties => ({
    ...cliColorSwatch(name, settings.terminalTextColor, settings.terminalBackgroundColor),
    ...(name === 'REVERSE' ? { outline: '1px solid currentColor', outlineOffset: '-1px' } : {})
  })

  useEffect(() => {
    if (!open) return
    menuRef.current?.querySelector<HTMLElement>('[aria-selected="true"]')?.focus()
    const onPointerDown = (event: MouseEvent): void => {
      if (!menuRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const selectedStyle = swatchStyle(value)
  const handleOptionKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>): void => {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return
    event.preventDefault()
    const options = menuRef.current?.querySelectorAll<HTMLElement>('[role="option"]')
    if (!options?.length) return
    const currentIndex = Array.from(options).indexOf(event.currentTarget)
    const nextIndex =
      (currentIndex + (event.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length
    options[nextIndex].focus()
  }

  return (
    <div className="cli-color-menu" ref={menuRef}>
      <button
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label={`${label}顏色，目前 ${value}`}
        className="cli-color-menu-trigger"
        onClick={() => setOpen((isOpen) => !isOpen)}
        style={selectedStyle}
        type="button"
      >
        <span>{value}</span>
        <ChevronDown size={14} />
      </button>
      {open && (
        <div aria-label={`${label}顏色選單`} className="cli-color-menu-list" role="listbox">
          {options.map(({ name, group }, index) => {
            const previousGroup = options[index - 1]?.group
            return (
              <Fragment key={name}>
                {group !== previousGroup && (
                  <div className="cli-color-menu-group" role="presentation">
                    {group}
                  </div>
                )}
                <button
                  aria-selected={value === name}
                  className={`cli-color-menu-option ${value === name ? 'selected' : ''}`}
                  onClick={() => {
                    onChange(name)
                    setOpen(false)
                  }}
                  onKeyDown={handleOptionKeyDown}
                  role="option"
                  style={swatchStyle(name)}
                  type="button"
                >
                  <span>{name}</span>
                  {value === name && <Check size={13} />}
                </button>
              </Fragment>
            )
          })}
          <div className="cli-color-menu-group" role="presentation">
            自訂
          </div>
          <button
            aria-selected={value.startsWith('#')}
            className={`cli-color-menu-option ${value.startsWith('#') ? 'selected' : ''}`}
            onClick={() => setOpen(false)}
            onKeyDown={handleOptionKeyDown}
            role="option"
            style={swatchStyle(value.startsWith('#') ? value : '#777777')}
            type="button"
          >
            <span>{value.startsWith('#') ? value : '使用右側色盤自訂 HEX'}</span>
            {value.startsWith('#') && <Check size={13} />}
          </button>
        </div>
      )}
    </div>
  )
}

function CliReportColorEditor({
  settings,
  onChange
}: {
  settings: AppSettings
  onChange: (patch: Partial<AppSettings>) => void
}): React.JSX.Element {
  const previewStyle = (value: string): React.CSSProperties =>
    cliColorPreview(value, settings.terminalTextColor, settings.terminalBackgroundColor)

  return (
    <>
      <p className="preference-section-note">
        這七項與終端中的 <code>cool -c</code> 共用設定；選擇樣式或用色盤自訂 HEX，兩端會即時同步。
      </p>
      <div className="cli-report-preview" aria-label="CLI 學習報表顏色預覽">
        <div className="cli-report-preview-url" style={previewStyle(settings.cliReportUrlColor)}>
          來源：www.coolenglish.edu.tw
        </div>
        <div
          className="cli-report-preview-title"
          style={previewStyle(settings.cliReportTitleColor)}
        >
          <strong style={previewStyle(settings.cliReportTitleTextColor)}>
            學習時數報表｜測試帳號
          </strong>
        </div>
        <div
          className="cli-report-preview-header"
          style={previewStyle(settings.cliReportHeaderColor)}
        >
          月份 停留 影片 練習
        </div>
        <div
          className="cli-report-preview-current"
          style={previewStyle(settings.cliReportCurrentColor)}
        >
          2026/10 14:20 08:10 06:10 當月
        </div>
        <div
          className="cli-report-preview-below"
          style={previewStyle(settings.cliReportBelowColor)}
        >
          2026/09 07:35 04:10 03:25 未達標
        </div>
        <div
          className="cli-report-preview-separator"
          style={previewStyle(settings.cliReportSeparatorColor)}
        >
          ─────────────────────────────
        </div>
      </div>
      <div className="cli-report-color-list">
        {cliReportColorFields.map((field) => {
          const value = settings[field.setting]
          return (
            <div className="cli-report-color-entry" key={field.key}>
              <div
                className="cli-report-color-row"
                style={cliColorSwatch(
                  value,
                  settings.terminalTextColor,
                  settings.terminalBackgroundColor
                )}
              >
                <div className="cli-report-color-copy">
                  <strong>{field.label}</strong>
                  <small>{field.description}</small>
                  <code>
                    {field.key}: {value}
                  </code>
                </div>
                <div className="cli-report-color-inputs">
                  <CliColorMenu
                    label={field.label}
                    value={value}
                    settings={settings}
                    onChange={(nextValue) => onChange(reportColorPatch(field.setting, nextValue))}
                  />
                  <input
                    aria-label={`自訂${field.label}顏色`}
                    type="color"
                    value={cliColorInputValue(value)}
                    onChange={(event) =>
                      onChange(reportColorPatch(field.setting, event.target.value))
                    }
                  />
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}

function contrastRatio(foreground: string, background: string): number {
  const luminance = (color: string): number => {
    const channels = color.match(/[0-9a-f]{2}/gi)?.map((channel) => parseInt(channel, 16) / 255)
    if (!channels || channels.length !== 3) return 0
    const linear = channels.map((value) =>
      value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
    )
    return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722
  }
  const first = luminance(foreground)
  const second = luminance(background)
  return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05)
}

function textContrastBackground(theme: AppSettings['theme']): string {
  return theme === 'light' ? '#ffffff' : '#252a31'
}

function formatCookieTimestamp(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '時間未知'
  const datePart = date.toLocaleDateString('sv-SE')
  const timePart = date.toLocaleTimeString('sv-SE', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
  return `${datePart} ${timePart}`
}

function invertedTextColor(color: string, theme: AppSettings['theme']): string {
  const channels = color.match(/[0-9a-f]{2}/gi)?.map((channel) => 255 - parseInt(channel, 16))
  const background = textContrastBackground(theme)
  const inverted =
    channels?.length === 3
      ? `#${channels.map((channel) => Math.round(channel).toString(16).padStart(2, '0')).join('')}`
      : theme === 'light'
        ? '#1b1e23'
        : '#e7eaf0'
  if (contrastRatio(inverted, background) >= 4.5) return inverted
  return theme === 'light' ? '#243b53' : '#a5f3df'
}

function App(): React.JSX.Element {
  const [page, setPage] = useState<Page>('home')
  const [accounts, setAccounts] = useState<AccountRecord[]>([])
  const [courses, setCourses] = useState<CourseBookmark[]>([])
  const [selectedEmail, setSelectedEmail] = useState('')
  const [networkEvents, setNetworkEvents] = useState<NetworkEvent[]>([])
  const [networkSessions, setNetworkSessions] = useState<NetworkSession[]>([])
  const [courseProgress, setCourseProgress] = useState<CourseProgressUpdate[]>([])
  const [networkMode, setNetworkMode] = useState<NetworkMode>('headed')
  const [settings, setSettings] = useState<AppSettings>(defaultSettings)
  const [settingsLoaded, setSettingsLoaded] = useState(false)
  const settingsRef = useRef(settings)
  const settingsSaveTimer = useRef<number | null>(null)
  const [report, setReport] = useState<CourseReportRow[]>([])
  const [terminalOpen, setTerminalOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const sidebarRef = useRef<HTMLElement | null>(null)
  const [toast, setToast] = useState<{
    text: string
    kind: 'success' | 'error' | 'info'
  } | null>(null)
  const [busy, setBusy] = useState(false)
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginName, setLoginName] = useState('')
  const [accountLoginPrompt, setAccountLoginPrompt] = useState<AccountLoginPrompt>(null)
  const [accountLoginPassword, setAccountLoginPassword] = useState('')
  const [urlDraft, setUrlDraft] = useState('')
  const [categoryDraft, setCategoryDraft] = useState('')
  const [aliasDraft, setAliasDraft] = useState('')
  const [query, setQuery] = useState('')

  useEffect(() => {
    settingsRef.current = settings
  }, [settings])

  const notify = useCallback((text: string, kind: 'success' | 'error' | 'info' = 'success') => {
    setToast({ text, kind })
    window.setTimeout(() => setToast(null), 4500)
  }, [])

  const refresh = useCallback(async () => {
    const [nextAccounts, nextCourses] = await Promise.all([
      window.cool.accounts.list(),
      window.cool.courses.list()
    ])
    setAccounts(nextAccounts)
    setCourses(nextCourses)
    setSelectedEmail((current) =>
      nextAccounts.some((account) => account.email === current)
        ? current
        : (nextAccounts[0]?.email ?? '')
    )
  }, [])

  useEffect(() => {
    let active = true
    const unsubscribeLoginSuccess = window.cool.accounts.onLoginSuccess(() => {
      notify('登入成功，Cool English MoodleSession 已驗證並加密保存。')
    })
    const unsubscribeLoginInteractionRequired = window.cool.accounts.onLoginInteractionRequired(
      (message) => {
        notify(message)
      }
    )
    const unsubscribeLoginStatus = window.cool.accounts.onLoginStatus((message) => {
      notify(message, 'info')
    })
    const unsubscribeCliSync = window.cool.accounts.onCliSync((emails) => {
      void refresh()
        .then(() =>
          notify(
            emails.length === 1
              ? `已同步終端登入帳號：${emails[0]}`
              : `已同步 ${emails.length} 個終端登入帳號。`
          )
        )
        .catch((error: unknown) =>
          notify(error instanceof Error ? error.message : String(error), 'error')
        )
    })
    const unsubscribeCliSyncError = window.cool.accounts.onCliSyncError((message) => {
      notify(`終端帳號同步失敗：${message}`, 'error')
    })
    const unsubscribeCourseCliSync = window.cool.courses.onCliSync((nextCourses) => {
      if (active) setCourses(nextCourses)
    })
    const unsubscribeCourseCliSyncError = window.cool.courses.onCliSyncError((message) => {
      notify(`終端課程連結同步失敗：${message}`, 'error')
    })
    const unsubscribeCliColors = window.cool.settings.onCliColors((cliColors) => {
      if (!active) return
      const nextSettings = { ...settingsRef.current, ...cliColors }
      settingsRef.current = nextSettings
      setSettings(nextSettings)
      notify('已同步 CLI 顏色設定。')
    })
    const unsubscribeCliColorsError = window.cool.settings.onCliColorsError((message) =>
      notify(`CLI 顏色同步失敗：${message}`, 'error')
    )
    const unsubscribe = window.cool.events.onNetwork((event) => {
      setNetworkEvents((items) => [event, ...items])
      setNetworkSessions((items) =>
        items.map((session) =>
          session.id === event.sessionId
            ? { ...session, events: [...session.events, event] }
            : session
        )
      )
    })
    const unsubscribeSessions = window.cool.events.onSession((summary) => {
      setNetworkSessions((items) => {
        const existing = items.find((item) => item.id === summary.id)
        if (!existing) return [{ ...summary, events: [] }, ...items]
        return items.map((item) =>
          item.id === summary.id
            ? {
                ...item,
                ...summary,
                events: item.events
              }
            : item
        )
      })
    })
    const unsubscribeNetworkHistory = window.cool.events.onHistoryChanged(() => {
      void window.cool.events
        .list()
        .then((nextSessions) => {
          if (!active) return
          setNetworkSessions(nextSessions)
          setNetworkEvents(nextSessions.flatMap((session) => session.events).reverse())
        })
        .catch((error: unknown) =>
          notify(error instanceof Error ? error.message : String(error), 'error')
        )
    })
    const unsubscribeCourseProgress = window.cool.events.onCourseProgress((update) => {
      setCourseProgress((items) => [...items, update])
      setNetworkMode(update.mode)
    })
    void window.cool.settings
      .get()
      .then((nextSettings) => {
        if (!active) return
        setSettings(nextSettings)
        settingsRef.current = nextSettings
        setSettingsLoaded(true)
      })
      .catch((error: unknown) => {
        if (!active) return
        setSettingsLoaded(true)
        notify(error instanceof Error ? error.message : String(error), 'error')
      })
    void Promise.all([
      window.cool.accounts.list(),
      window.cool.courses.list(),
      window.cool.events.list()
    ])
      .then(([nextAccounts, nextCourses, nextSessions]) => {
        if (!active) return
        setAccounts(nextAccounts)
        setCourses(nextCourses)
        setNetworkSessions(nextSessions)
        setNetworkEvents(nextSessions.flatMap((session) => session.events).reverse())
        setSelectedEmail((current) =>
          nextAccounts.some((account) => account.email === current)
            ? current
            : (nextAccounts[0]?.email ?? '')
        )
      })
      .catch((error: unknown) =>
        notify(error instanceof Error ? error.message : String(error), 'error')
      )
    return () => {
      active = false
      unsubscribe()
      unsubscribeSessions()
      unsubscribeNetworkHistory()
      unsubscribeCourseProgress()
      unsubscribeLoginSuccess()
      unsubscribeLoginInteractionRequired()
      unsubscribeLoginStatus()
      unsubscribeCliSync()
      unsubscribeCliSyncError()
      unsubscribeCourseCliSync()
      unsubscribeCourseCliSyncError()
      unsubscribeCliColors()
      unsubscribeCliColorsError()
    }
  }, [notify, refresh])

  const selectedAccount = useMemo(
    () => accounts.find((account) => account.email === selectedEmail),
    [accounts, selectedEmail]
  )

  const withBusy = async (operation: () => Promise<void>): Promise<void> => {
    if (busy) return
    setBusy(true)
    try {
      await operation()
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), 'error')
    } finally {
      setBusy(false)
    }
  }

  const beginLogin = (
    event: FormEvent | React.MouseEvent<HTMLButtonElement>,
    mode: LoginMode
  ): void => {
    event.preventDefault()
    void withBusy(async () => {
      if (!loginEmail.includes('@') || !loginPassword) {
        throw new Error('請輸入有效的 Google Email 與密碼。')
      }
      const nextAccounts = await window.cool.accounts.login(
        loginEmail.trim(),
        loginPassword,
        loginName.trim(),
        mode
      )
      setAccounts(nextAccounts)
      setSelectedEmail(loginEmail.trim())
      setLoginEmail('')
      setLoginPassword('')
      setLoginName('')
    })
  }

  const checkCookie = (email: string): void => {
    void withBusy(async () => {
      const nextAccounts = await window.cool.accounts.checkCookie(email)
      setAccounts(nextAccounts)
      const account = nextAccounts.find((item) => item.email.toLowerCase() === email.toLowerCase())
      if (account?.cookieStatus === 'valid') {
        notify(`已確認 ${account.name} 可使用 Cookie 讀取學習時數。`)
      } else if (account?.cookieStatus === 'expired') {
        notify(`${account.name} 的 Cookie 已被 Cool English 導向登入頁，請重新登入。`, 'error')
      } else {
        notify('目前無法判定 Cookie 狀態；網站沒有回傳可辨識的時數表格，請稍後再試。', 'error')
      }
    })
  }

  const loginSaved = (email: string, mode: LoginMode): void => {
    void withBusy(async () => {
      setAccounts(await window.cool.accounts.loginSaved(email, mode))
      setSelectedEmail(email)
    })
  }

  const loginLinkedAccount = async (
    email: string,
    password: string,
    name: string,
    mode: LoginMode
  ): Promise<boolean> => {
    if (busy) return false
    setBusy(true)
    try {
      setAccounts(await window.cool.accounts.login(email, password, name, mode))
      setSelectedEmail(email)
      return true
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), 'error')
      return false
    } finally {
      setBusy(false)
    }
  }

  const removeAccount = (account: AccountRecord): void => {
    if (!window.confirm(`確定要移除 ${account.name} 嗎？這也會刪除本機 cookie。`)) return
    void withBusy(async () => {
      setAccounts(await window.cool.accounts.remove(account.email))
      await refresh()
      notify(`已移除帳號 ${account.name}。`)
    })
  }

  const deleteNetworkSessions = async (sessionIds: string[]): Promise<void> => {
    const nextSessions = await window.cool.events.remove(sessionIds)
    setNetworkSessions(nextSessions)
    setNetworkEvents(nextSessions.flatMap((session) => session.events))
    notify(`已刪除 ${sessionIds.length} 筆網路紀錄。`)
  }

  const stopNetworkSession = async (sessionId: string): Promise<void> => {
    if (!window.confirm('確定要停止此工作階段？只會關閉它所屬的 Playwright 工作與瀏覽器。')) {
      return
    }
    try {
      await window.cool.events.stop(sessionId)
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), 'error')
    }
  }

  const renameAccount = (account: AccountRecord, name: string): void => {
    void withBusy(async () => {
      setAccounts(await window.cool.accounts.rename(account.email, name))
      notify('帳號名稱已更新。')
    })
  }

  const addCourses = (event: FormEvent): void => {
    event.preventDefault()
    void withBusy(async () => {
      const urls = urlDraft
        .split(/\s+/)
        .map((url) => url.trim().replace(/[.,;)>]+$/, ''))
        .filter((url) => /^https?:\/\//i.test(url))
      if (!urls.length) throw new Error('請貼上至少一個 http 或 https 課程網址。')
      const next = await window.cool.courses.add(urls, categoryDraft, aliasDraft)
      setCourses(next)
      setUrlDraft('')
      setCategoryDraft('')
      setAliasDraft('')
      notify(`已儲存 ${urls.length} 個網址。`)
    })
  }

  const openCourses = (urls: string[], label: string, mode: LoginMode): void => {
    if (!selectedEmail) {
      setPage('accounts')
      notify('請先登入並選擇帳號。', 'error')
      return
    }
    if (settings.networkHistoryMode === 'disabled') {
      setCourseProgress([])
      setNetworkMode(mode)
      setPage('network')
    }
    void withBusy(async () => {
      await window.cool.courses.open(urls, selectedEmail, mode, label)
      notify(
        settings.networkHistoryMode === 'disabled'
          ? `已${mode === 'headed' ? '在有頭瀏覽器' : '於背景無頭瀏覽器'}開啟 ${urls.length} 個網址；逐筆進度顯示在「網路紀錄 > 正在運行 > ${mode === 'headed' ? '有頭紀錄' : '無頭紀錄'}」，不會保存網路事件。`
          : mode === 'headed'
            ? `已在有頭瀏覽器開啟 ${urls.length} 個網址；Playwright 歷史會將它們合併為一次工作階段。`
            : `已在背景無頭瀏覽器開啟 ${urls.length} 個網址；工作階段會持續執行，請到「網路紀錄 > 正在運行」手動終止。`
      )
    })
  }

  const fetchReport = (): void => {
    if (!selectedEmail) {
      setPage('accounts')
      notify('請先登入並選擇帳號。', 'error')
      return
    }
    void withBusy(async () => {
      setReport(await window.cool.reports.fetch(selectedEmail, settings.reportThresholdMinutes))
      setPage('reports')
      notify('學習報表已更新。')
    })
  }

  const updateCourseCategory = (url: string, category: string): void => {
    void withBusy(async () => {
      setCourses(await window.cool.courses.setCategory(url, category))
      notify('課程分類已更新。')
    })
  }

  const removeCourse = (url: string): void => {
    void withBusy(async () => {
      setCourses(await window.cool.courses.remove(url))
      notify('已從清單移除網址。')
    })
  }

  const saveSettings = (next: AppSettings): void => {
    setSettings(next)
    settingsRef.current = next
    if (settingsSaveTimer.current !== null) window.clearTimeout(settingsSaveTimer.current)
    settingsSaveTimer.current = window.setTimeout(() => {
      const pending = settingsRef.current
      void window.cool.settings
        .save(pending)
        .then((saved) => {
          if (settingsRef.current === pending) setSettings(saved)
        })
        .catch((error: unknown) =>
          notify(error instanceof Error ? error.message : String(error), 'error')
        )
    }, 300)
  }

  const filteredAccounts = accounts.filter((account) =>
    `${account.name} ${account.email}`.toLowerCase().includes(query.toLowerCase())
  )
  if (!settingsLoaded) {
    return (
      <main className="app-loading" role="status" aria-live="polite">
        載入工作區設定…
      </main>
    )
  }

  const activeColorPreset = getColorThemePreset(settings.colorThemeId)

  return (
    <main
      className="app-shell"
      data-theme={settings.theme}
      data-inverted={settings.invertColors}
      data-custom-text-color={
        settings.useCustomTextColor &&
        !settings.invertColors &&
        contrastRatio(settings.textColor, textContrastBackground(settings.theme)) >= 4.5
      }
      style={
        {
          '--accent': settings.accentColor,
          '--interface-background-color':
            activeColorPreset?.interfaceBackgroundColor ??
            (settings.theme === 'light' ? '#eef1f5' : '#0d0f13'),
          '--interface-surface-color':
            activeColorPreset?.interfaceSurfaceColor ??
            (settings.theme === 'light' ? '#f9fafc' : '#15181e'),
          '--custom-text-color': settings.textColor,
          '--inverted-text-color': invertedTextColor(
            settings.useCustomTextColor
              ? settings.textColor
              : settings.theme === 'light'
                ? '#1b1e23'
                : '#e7eaf0',
            settings.theme
          ),
          '--app-font-family': fontFamilyStack(settings.fontFamily),
          '--ui-font-scale': String(settings.fontSize / 13)
        } as React.CSSProperties
      }
    >
      <header className="titlebar">
        <div className="titlebar-center">
          <span className="live-dot" />
          <span>本機工作階段</span>
          <span className="titlebar-separator">·</span>
          <span>{selectedAccount?.name ?? '尚未選擇帳號'}</span>
          <ChevronDown size={13} />
        </div>
        <div className="titlebar-actions">
          <button
            className="icon-button"
            title={terminalOpen ? '隱藏終端' : '顯示終端'}
            onClick={() => setTerminalOpen((value) => !value)}
          >
            <TerminalSquare size={16} />
          </button>
          <button
            className="window-control minimize"
            aria-label="Minimize"
            onClick={() => window.cool.app.minimize()}
          />
          <button
            className="window-control maximize"
            aria-label="Maximize"
            onClick={() => window.cool.app.toggleMaximize()}
          />
          <button
            className="window-control close"
            aria-label="Close"
            onClick={() => window.cool.app.close()}
          />
        </div>
      </header>

      <div
        className="workbench"
        data-sidebar-open={sidebarOpen}
        onMouseMove={(event) => {
          if (settings.sidebarMode !== 'hover') return
          if (event.clientX <= 12) {
            setSidebarOpen(true)
            return
          }
          const sidebarRight = sidebarRef.current?.getBoundingClientRect().right ?? 236
          if (sidebarOpen && event.clientX > sidebarRight) setSidebarOpen(false)
        }}
      >
        <aside className="sidebar" id="workspace-sidebar" ref={sidebarRef}>
          <button
            className="sidebar-brand-toggle"
            type="button"
            aria-label={sidebarOpen ? '隱藏側邊選單' : '顯示側邊選單'}
            aria-expanded={sidebarOpen}
            aria-controls="workspace-sidebar"
            title={sidebarOpen ? '隱藏側邊選單' : '顯示側邊選單'}
            onClick={() => setSidebarOpen((open) => !open)}
          >
            <img src={appIcon} alt="" />
          </button>
          <nav className="primary-nav">
            {navItems.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                className={`nav-item ${page === id ? 'active' : ''}`}
                onClick={() => setPage(id)}
              >
                <Icon size={17} strokeWidth={1.8} />
                <span>{label}</span>
                {id === 'accounts' && accounts.length > 0 && (
                  <span className="nav-count">{accounts.length}</span>
                )}
                {id === 'network' && networkEvents.length > 0 && (
                  <span className="nav-count">{networkEvents.length}</span>
                )}
              </button>
            ))}
          </nav>

          <div className="sidebar-spacer" />
          <div className="sidebar-section-title">
            <span>已連結帳號</span>
            <button
              className="mini-icon-button"
              title="新增帳號"
              onClick={() => setPage('accounts')}
            >
              <Plus size={14} />
            </button>
          </div>
          <div className="account-mini-list">
            {accounts.slice(0, 5).map((account) => (
              <button
                className={`account-mini ${account.email === selectedEmail ? 'selected' : ''}`}
                key={account.email}
                onClick={() => setSelectedEmail(account.email)}
              >
                <span className="avatar">{account.name.slice(0, 1).toUpperCase()}</span>
                <span className="account-mini-name">{account.name}</span>
                <span className={`online-indicator ${account.cookieStatus ?? 'unknown'}`} />
              </button>
            ))}
            {!accounts.length && <div className="empty-side-note">尚未新增帳號</div>}
          </div>

          <div className="sidebar-bottom">
            <button className="nav-item" onClick={() => setPage('settings')}>
              <Settings2 size={17} strokeWidth={1.8} />
              <span>設定</span>
            </button>
            <div className="profile-row">
              <div className="profile-avatar">C</div>
              <div className="profile-copy">
                <strong>Cool Workspace</strong>
                <span>Desktop · {window.cool.app.version}</span>
              </div>
              <MoreHorizontal size={17} className="muted-icon" />
            </div>
          </div>
        </aside>

        <section className="main-column">
          <div className="page-topbar">
            <div className="breadcrumbs">
              <span>cool</span>
              <span className="crumb-slash">/</span>
              <strong>{navItems.find((item) => item.id === page)?.label ?? '設定'}</strong>
            </div>
            <div className="topbar-right">
              {page === 'accounts' && (
                <label className="search-box">
                  <Search size={15} />
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="搜尋帳號"
                  />
                  <kbd>⌘ K</kbd>
                </label>
              )}
              <button className="icon-button help-button" title="說明">
                <CircleHelp size={16} />
              </button>
            </div>
          </div>

          <div
            className={`main-layout ${settings.terminalLayout} ${terminalOpen ? '' : 'terminal-hidden'}`}
            style={{ '--split-ratio': `${settings.splitRatio * 100}%` } as React.CSSProperties}
          >
            <div className="page-content">
              {page === 'home' && (
                <HomePage
                  accounts={accounts}
                  courses={courses}
                  selectedAccount={selectedAccount}
                  onNavigate={setPage}
                  onRefresh={() => void refresh()}
                  onFetchReport={fetchReport}
                />
              )}
              {page === 'accounts' && (
                <AccountsPage
                  accounts={filteredAccounts}
                  busy={busy}
                  email={loginEmail}
                  password={loginPassword}
                  name={loginName}
                  selectedEmail={selectedEmail}
                  onEmail={setLoginEmail}
                  onPassword={setLoginPassword}
                  onName={setLoginName}
                  onBegin={beginLogin}
                  onSelect={setSelectedEmail}
                  onRename={renameAccount}
                  onRemove={removeAccount}
                  onCheckCookie={checkCookie}
                  onAutoLogin={loginSaved}
                  onLoginWithPassword={loginLinkedAccount}
                  loginPrompt={accountLoginPrompt}
                  loginPassword={accountLoginPassword}
                  onOpenLoginPrompt={(email, name, mode) => {
                    setAccountLoginPassword('')
                    setAccountLoginPrompt({ email, name, mode })
                  }}
                  onLoginPassword={setAccountLoginPassword}
                  onCloseLoginPrompt={() => {
                    setAccountLoginPassword('')
                    setAccountLoginPrompt(null)
                  }}
                />
              )}
              {page === 'courses' && (
                <CoursesPage
                  courses={courses}
                  accounts={accounts}
                  selectedEmail={selectedEmail}
                  draft={urlDraft}
                  category={categoryDraft}
                  alias={aliasDraft}
                  categories={[...new Set(courses.map((course) => course.category))]}
                  busy={busy}
                  onDraft={setUrlDraft}
                  onCategory={setCategoryDraft}
                  onAlias={setAliasDraft}
                  onAdd={addCourses}
                  onOpen={openCourses}
                  onSetCategory={updateCourseCategory}
                  onRemove={removeCourse}
                />
              )}
              {page === 'reports' && (
                <ReportsPage
                  accounts={accounts}
                  selectedEmail={selectedEmail}
                  rows={report}
                  settings={settings}
                  busy={busy}
                  onSelect={setSelectedEmail}
                  onFetch={fetchReport}
                />
              )}
              {page === 'network' && (
                <NetworkPage
                  sessions={networkSessions}
                  courseProgress={courseProgress}
                  mode={networkMode}
                  onModeChange={setNetworkMode}
                  onDeleteSessions={deleteNetworkSessions}
                  onStopSession={stopNetworkSession}
                  onExportSession={(sessionId) => window.cool.events.export(sessionId)}
                />
              )}
              {page === 'settings' && <SettingsPage settings={settings} onChange={saveSettings} />}
            </div>

            {terminalOpen && (
              <div
                className="terminal-split-handle"
                onPointerDown={(event) => {
                  if (event.button !== 0) return
                  event.preventDefault()
                  const layout = event.currentTarget.parentElement
                  if (!(layout instanceof HTMLElement)) return
                  const pointerId = event.pointerId
                  let pendingRatio = settingsRef.current.splitRatio
                  let resizeFrame: number | null = null
                  const applyRatio = (): void => {
                    const next = { ...settingsRef.current, splitRatio: pendingRatio }
                    settingsRef.current = next
                    setSettings(next)
                    resizeFrame = null
                  }
                  layout.classList.add('is-resizing')
                  window.dispatchEvent(new Event(TERMINAL_LAYOUT_RESIZE_START_EVENT))
                  const move = (moveEvent: PointerEvent): void => {
                    if (moveEvent.pointerId !== pointerId) return
                    const bounds = layout.getBoundingClientRect()
                    const ratio =
                      settings.terminalLayout === 'vertical'
                        ? (moveEvent.clientY - bounds.top) / bounds.height
                        : (moveEvent.clientX - bounds.left) / bounds.width
                    pendingRatio = Math.max(0.3, Math.min(0.8, ratio))
                    if (resizeFrame === null) resizeFrame = requestAnimationFrame(applyRatio)
                  }
                  const stop = (): void => {
                    layout.classList.remove('is-resizing')
                    window.removeEventListener('pointermove', move)
                    window.removeEventListener('pointerup', stop)
                    window.removeEventListener('pointercancel', stop)
                    window.removeEventListener('blur', stop)
                    if (resizeFrame !== null) cancelAnimationFrame(resizeFrame)
                    applyRatio()
                    window.dispatchEvent(new Event(TERMINAL_LAYOUT_RESIZE_END_EVENT))
                    void saveSettings(settingsRef.current)
                  }
                  window.addEventListener('pointermove', move)
                  window.addEventListener('pointerup', stop, { once: true })
                  window.addEventListener('pointercancel', stop, { once: true })
                  window.addEventListener('blur', stop, { once: true })
                }}
              />
            )}
            <section className={`terminal-dock ${terminalOpen ? '' : 'is-hidden'}`}>
              <TerminalPanel
                terminalFontSize={settings.terminalFontSize}
                fontFamily={settings.fontFamily}
                terminalCursorColor={settings.terminalCursorColor}
                terminalTextColor={settings.terminalTextColor}
                terminalBackgroundColor={settings.terminalBackgroundColor}
                isVisible={terminalOpen}
              />
            </section>
          </div>

          <footer className="statusbar">
            <div className="status-left">
              <span className="status-branch">
                <Command size={12} /> cool
              </span>
              <span>
                <Check size={12} /> Ready
              </span>
            </div>
            <div className="status-right">
              <span>
                <ShieldCheck size={12} /> Local data
              </span>
              <span>TypeScript</span>
              <span>UTF-8</span>
            </div>
          </footer>
        </section>
      </div>

      {toast && (
        <div className={`toast ${toast.kind}`}>
          {toast.kind === 'success' ? (
            <Check size={16} />
          ) : toast.kind === 'error' ? (
            <X size={16} />
          ) : (
            <Activity size={16} />
          )}
          <span>{toast.text}</span>
          <button onClick={() => setToast(null)} aria-label="Dismiss">
            <X size={14} />
          </button>
        </div>
      )}
      {busy && (
        <div className="busy-indicator">
          <LoaderCircle size={15} className="spin" />
          正在處理
        </div>
      )}
    </main>
  )
}

function PageHeading({
  eyebrow,
  title,
  description,
  action
}: {
  eyebrow: string
  title: string
  description: string
  action?: ReactNode
}): React.JSX.Element {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  )
}

function HomePage({
  accounts,
  courses,
  selectedAccount,
  onNavigate,
  onRefresh,
  onFetchReport
}: {
  accounts: AccountRecord[]
  courses: CourseBookmark[]
  selectedAccount?: AccountRecord
  onNavigate: (page: Page) => void
  onRefresh: () => void
  onFetchReport: () => void
}): React.JSX.Element {
  return (
    <div className="content-wrap">
      <div className="welcome-line">
        <div>
          <div className="eyebrow">YOUR LEARNING WORKSPACE</div>
          <h1>{getWelcomeMessage()}</h1>
          <p>管理 Cool English 帳號、課程與學習進度，所有資料都保存在這台裝置。</p>
        </div>
        <button className="button secondary" onClick={onRefresh}>
          <RefreshCw size={15} /> 重新整理
        </button>
      </div>

      <div className="stats-grid">
        <StatCard
          icon={<UsersRound size={17} />}
          label="已連結帳號"
          value={accounts.length}
          note="個本機帳號"
          tone="mint"
        />
        <StatCard
          icon={<BookOpen size={17} />}
          label="已儲存課程"
          value={courses.length}
          note="個課程網址"
          tone="blue"
        />
        <StatCard
          icon={<Activity size={17} />}
          label="網路事件"
          value="Live"
          note="瀏覽器事件記錄"
          tone="purple"
        />
        <StatCard
          icon={<Clock3 size={17} />}
          label="目前帳號"
          value={selectedAccount?.name ?? '—'}
          note={selectedAccount?.email ?? '尚未登入'}
          tone="orange"
        />
      </div>

      <section className="hero-card">
        <div className="hero-copy">
          <div className="hero-icon">
            <FileClock size={20} />
          </div>
          <div className="eyebrow">LEARNING OVERVIEW</div>
          <h2>掌握你的學習進度</h2>
          <p>快速查看學習時間報表，或從上次使用的課程繼續。</p>
          <div className="hero-actions">
            <button className="button primary" onClick={onFetchReport}>
              查看學習報表 <ArrowUpRight size={15} />
            </button>
            <button className="button ghost" onClick={() => onNavigate('courses')}>
              瀏覽課程
            </button>
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="art-orbit orbit-one" />
          <div className="art-orbit orbit-two" />
          <div className="art-core">
            <Activity size={36} />
          </div>
          <div className="art-spark spark-one" />
          <div className="art-spark spark-two" />
          <div className="art-spark spark-three" />
        </div>
      </section>

      <div className="section-heading">
        <div>
          <h2>快速開始</h2>
          <p>常用工作流程</p>
        </div>
      </div>
      <div className="quick-grid">
        <QuickAction
          icon={<UserRound size={17} />}
          title="管理帳號"
          detail="新增或整理已連結的帳號"
          onClick={() => onNavigate('accounts')}
        />
        <QuickAction
          icon={<FolderOpen size={17} />}
          title="整理課程網址"
          detail="儲存並快速開啟課程頁面"
          onClick={() => onNavigate('courses')}
        />
        <QuickAction
          icon={<Globe2 size={17} />}
          title="查看網路紀錄"
          detail="檢查瀏覽器 request / response"
          onClick={() => onNavigate('network')}
        />
      </div>
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
  note,
  tone
}: {
  icon: ReactNode
  label: string
  value: string | number
  note: string
  tone: string
}): React.JSX.Element {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${tone}`}>{icon}</div>
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      <span className="stat-note">{note}</span>
    </div>
  )
}

function QuickAction({
  icon,
  title,
  detail,
  onClick
}: {
  icon: ReactNode
  title: string
  detail: string
  onClick: () => void
}): React.JSX.Element {
  return (
    <button className="quick-card" onClick={onClick}>
      <span className="quick-icon">{icon}</span>
      <span className="quick-copy">
        <strong>{title}</strong>
        <small>{detail}</small>
      </span>
      <ArrowUpRight size={15} className="quick-arrow" />
    </button>
  )
}

function AccountsPage({
  accounts,
  busy,
  email,
  password,
  name,
  selectedEmail,
  onEmail,
  onPassword,
  onName,
  onBegin,
  onSelect,
  onRename,
  onRemove,
  onCheckCookie,
  onAutoLogin,
  onLoginWithPassword,
  loginPrompt,
  loginPassword,
  onOpenLoginPrompt,
  onLoginPassword,
  onCloseLoginPrompt
}: {
  accounts: AccountRecord[]
  busy: boolean
  email: string
  password: string
  name: string
  selectedEmail: string
  onEmail: (value: string) => void
  onPassword: (value: string) => void
  onName: (value: string) => void
  onBegin: (event: FormEvent | React.MouseEvent<HTMLButtonElement>, mode: LoginMode) => void
  onSelect: (email: string) => void
  onRename: (account: AccountRecord, name: string) => void
  onRemove: (account: AccountRecord) => void
  onCheckCookie: (email: string) => void
  onAutoLogin: (email: string, mode: LoginMode) => void
  onLoginWithPassword: (
    email: string,
    password: string,
    name: string,
    mode: LoginMode
  ) => Promise<boolean>
  loginPrompt: AccountLoginPrompt
  loginPassword: string
  onOpenLoginPrompt: (email: string, name: string, mode: LoginMode) => void
  onLoginPassword: (password: string) => void
  onCloseLoginPrompt: () => void
}): React.JSX.Element {
  const [editingEmail, setEditingEmail] = useState('')
  const [editingName, setEditingName] = useState('')
  const [loginMenuEmail, setLoginMenuEmail] = useState('')
  const [submittingLogin, setSubmittingLogin] = useState(false)
  const saveName = (account: AccountRecord): void => {
    setEditingEmail('')
    onRename(account, editingName)
  }
  const beginAccountLogin = (account: AccountRecord, mode: LoginMode): void => {
    if (account.hasSavedPassword) {
      onAutoLogin(account.email, mode)
      return
    }
    onOpenLoginPrompt(account.email, account.name, mode)
  }
  const submitAccountLogin = async (event: FormEvent): Promise<void> => {
    event.preventDefault()
    if (!loginPrompt || !loginPassword || submittingLogin) return
    setSubmittingLogin(true)
    try {
      const succeeded = await onLoginWithPassword(
        loginPrompt.email,
        loginPassword,
        loginPrompt.name,
        loginPrompt.mode
      )
      if (succeeded) onCloseLoginPrompt()
    } finally {
      setSubmittingLogin(false)
    }
  }

  return (
    <div className="content-wrap">
      <PageHeading
        eyebrow="ACCOUNTS"
        title="帳號管理"
        description="帳密以 Windows 系統加密保存，cookie 獨立加密並追蹤有效期限。"
      />
      <section className="panel login-panel">
        <div className="panel-heading">
          <div className="panel-heading-icon">
            <LockKeyhole size={17} />
          </div>
          <div>
            <h2>連結帳號</h2>
            <p>嘗試以提供的帳密登入；遇到驗證碼或雙重驗證時，請使用有頭模式完成網站要求。</p>
          </div>
        </div>
        <form className="login-form" onSubmit={(event) => onBegin(event, 'headed')}>
          <label className="field">
            <span>Google Email</span>
            <input
              value={email}
              onChange={(event) => onEmail(event.target.value)}
              placeholder="name@example.com"
              type="email"
              required
            />
          </label>
          <label className="field">
            <span>密碼</span>
            <input
              value={password}
              onChange={(event) => onPassword(event.target.value)}
              placeholder="Google / Cool English 密碼"
              type="password"
              autoComplete="current-password"
              required
            />
          </label>
          <label className="field">
            <span>
              顯示名稱 <small>選填</small>
            </span>
            <input
              value={name}
              onChange={(event) => onName(event.target.value)}
              placeholder="例如：我的學校帳號"
              maxLength={64}
            />
          </label>
          <div className="login-mode-actions">
            <button
              className="button primary"
              type="button"
              disabled={busy}
              onClick={(event) => onBegin(event, 'headed')}
            >
              <ExternalLink size={15} /> 有頭自動登入
            </button>
            <button
              className="button secondary"
              type="button"
              disabled={busy}
              onClick={(event) => onBegin(event, 'headless')}
            >
              無頭自動登入
            </button>
          </div>
        </form>
        <div className="privacy-note">
          <ShieldCheck size={14} />
          <span>密碼由 Windows DPAPI 加密保存，cookie 另行加密保存；不會將明文憑證寫入檔案。</span>
        </div>
      </section>

      <div className="section-heading account-list-heading">
        <div>
          <h2>
            已連結帳號 <span className="heading-count">{accounts.length}</span>
          </h2>
          <p>選取帳號後，課程與報表會使用此登入狀態。</p>
        </div>
      </div>
      <section className="account-table">
        <div className="table-head account-row">
          <span>帳號</span>
          <span>電子郵件</span>
          <span>最後登入</span>
          <span>狀態</span>
          <span />
        </div>
        {accounts.map((account) => (
          <div
            className={`table-row account-row ${selectedEmail === account.email ? 'row-selected' : ''}`}
            key={account.email}
          >
            {editingEmail === account.email ? (
              <div className="account-name-editor">
                <input
                  aria-label={`編輯 ${account.email} 的帳號名稱`}
                  autoFocus
                  maxLength={64}
                  value={editingName}
                  onChange={(event) => setEditingName(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') saveName(account)
                    if (event.key === 'Escape') setEditingEmail('')
                  }}
                />
                <button
                  className="mini-icon-button"
                  title="儲存名稱"
                  aria-label="儲存名稱"
                  disabled={busy}
                  onClick={() => saveName(account)}
                >
                  <Check size={14} />
                </button>
                <button
                  className="mini-icon-button"
                  title="取消編輯"
                  aria-label="取消編輯"
                  onClick={() => setEditingEmail('')}
                >
                  <X size={14} />
                </button>
              </div>
            ) : (
              <button
                className="account-select"
                aria-pressed={selectedEmail === account.email}
                onClick={() => onSelect(account.email)}
              >
                <span className="avatar">{account.name.slice(0, 1).toUpperCase()}</span>
                <strong>{account.name}</strong>
                {selectedEmail === account.email && (
                  <small className="account-selected-label">已選取</small>
                )}
              </button>
            )}
            <span className="table-muted">{account.email}</span>
            <span className="table-muted">
              {account.last_login?.replace('T', ' ').slice(0, 16) ?? '—'}
            </span>
            <span className={`status-pill cookie-status ${account.cookieStatus ?? 'unknown'}`}>
              <span className="status-indicator" />
              <span className="cookie-status-label">
                {account.cookieStatus === 'valid'
                  ? '有效'
                  : account.cookieStatus === 'expired'
                    ? '已過期'
                    : '待檢查'}
              </span>
              <small>
                {account.cookieStatus === 'expired' && account.cookieExpiredAt
                  ? `過期確認 ${formatCookieTimestamp(account.cookieExpiredAt)}`
                  : account.cookieExpiresAt
                    ? `到期 ${formatCookieTimestamp(account.cookieExpiresAt)}`
                    : account.cookieStatus === 'valid'
                      ? 'Session cookie'
                      : `取得 ${account.cookieObtainedAt ? formatCookieTimestamp(account.cookieObtainedAt) : '—'}`}
              </small>
            </span>
            <div
              className="row-actions"
              onBlur={(event) => {
                if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
                  setLoginMenuEmail('')
                }
              }}
              onKeyDown={(event) => {
                if (event.key === 'Escape') setLoginMenuEmail('')
              }}
            >
              <button
                className="mini-icon-button"
                title="選擇有頭或無頭登入"
                aria-label={`重新登入 ${account.name}`}
                aria-haspopup="menu"
                aria-expanded={loginMenuEmail === account.email}
                disabled={busy}
                onClick={() =>
                  setLoginMenuEmail((current) => (current === account.email ? '' : account.email))
                }
              >
                <LogIn size={14} />
              </button>
              {loginMenuEmail === account.email && (
                <div className="account-login-menu" role="menu" aria-label="選擇登入方式">
                  <button
                    role="menuitem"
                    disabled={busy}
                    onClick={() => {
                      setLoginMenuEmail('')
                      beginAccountLogin(account, 'headed')
                    }}
                  >
                    有頭登入
                  </button>
                  <button
                    role="menuitem"
                    disabled={busy}
                    onClick={() => {
                      setLoginMenuEmail('')
                      beginAccountLogin(account, 'headless')
                    }}
                  >
                    無頭登入
                  </button>
                </div>
              )}
              <button
                className="mini-icon-button"
                title="檢查 Cookie 有效性"
                disabled={busy}
                onClick={() => onCheckCookie(account.email)}
              >
                <RefreshCw size={14} />
              </button>
              <button
                className="mini-icon-button"
                title="編輯帳號名稱"
                aria-label={`編輯 ${account.name} 的帳號名稱`}
                disabled={busy}
                onClick={() => {
                  setEditingEmail(account.email)
                  setEditingName(account.name)
                }}
              >
                <Pencil size={14} />
              </button>
              <button
                className="mini-icon-button danger-hover"
                title="移除帳號"
                onClick={() => onRemove(account)}
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}
        {!accounts.length && (
          <div className="empty-state compact">
            <UsersRound size={22} />
            <strong>尚未連結帳號</strong>
            <span>完成上方登入流程後，帳號會出現在這裡。</span>
          </div>
        )}
      </section>
      {loginPrompt && (
        <div className="account-login-backdrop">
          <form
            className="account-login-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="account-login-title"
            onSubmit={(event) => void submitAccountLogin(event)}
          >
            <h2 id="account-login-title">
              {loginPrompt.mode === 'headed' ? '有頭登入' : '無頭登入'}：{loginPrompt.name}
            </h2>
            <p>{loginPrompt.email} 尚未保存密碼。請輸入密碼以更新登入狀態與 Cookie。</p>
            <label className="field">
              <span>Google / Cool English 密碼</span>
              <input
                type="password"
                autoFocus
                autoComplete="current-password"
                value={loginPassword}
                onChange={(event) => onLoginPassword(event.target.value)}
                required
              />
            </label>
            <div className="login-mode-actions">
              <button className="button primary" type="submit" disabled={busy || submittingLogin}>
                {busy || submittingLogin ? '登入中…' : '開始登入'}
              </button>
              <button
                className="button secondary"
                type="button"
                disabled={busy || submittingLogin}
                onClick={onCloseLoginPrompt}
              >
                取消
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}

function CoursesPage({
  courses,
  accounts,
  selectedEmail,
  draft,
  category,
  alias,
  categories,
  busy,
  onDraft,
  onCategory,
  onAlias,
  onAdd,
  onOpen,
  onSetCategory,
  onRemove
}: {
  courses: CourseBookmark[]
  accounts: AccountRecord[]
  selectedEmail: string
  draft: string
  category: string
  alias: string
  categories: string[]
  busy: boolean
  onDraft: (value: string) => void
  onCategory: (value: string) => void
  onAlias: (value: string) => void
  onAdd: (event: FormEvent) => void
  onOpen: (urls: string[], label: string, mode: LoginMode) => void
  onSetCategory: (url: string, category: string) => void
  onRemove: (url: string) => void
}): React.JSX.Element {
  const groupedCourses = new Map<string, CourseBookmark[]>()
  courses.forEach((course) => {
    const groupName = course.alias?.trim() || course.category
    const group = groupedCourses.get(groupName) ?? []
    group.push(course)
    groupedCourses.set(groupName, group)
  })

  return (
    <div className="content-wrap">
      <PageHeading
        eyebrow="COURSE LIBRARY"
        title="課程網址"
        description="集中整理常用課程連結，並使用選取的 Cool English 帳號開啟。"
        action={
          <span className="selection-chip">
            <UserRound size={14} />
            {accounts.find((item) => item.email === selectedEmail)?.name ?? '未選擇帳號'}
          </span>
        }
      />
      <form className="panel add-url-panel" onSubmit={onAdd}>
        <div className="panel-heading">
          <div className="panel-heading-icon blue">
            <Plus size={17} />
          </div>
          <div>
            <h2>新增課程網址</h2>
            <p>可一次貼上多個網址，每行一個。</p>
          </div>
        </div>
        <textarea
          value={draft}
          onChange={(event) => onDraft(event.target.value)}
          placeholder={'https://www.coolenglish.edu.tw/course/view.php?id=...\nhttps://...'}
          rows={3}
        />
        <label className="field course-category-field">
          <span>分類</span>
          <input
            list="course-categories"
            value={category}
            onChange={(event) => onCategory(event.target.value)}
            placeholder="例如：英文課程、作業、常用"
            maxLength={64}
          />
          <datalist id="course-categories">
            {categories.map((item) => (
              <option key={item} value={item} />
            ))}
          </datalist>
        </label>
        <label className="field course-category-field">
          <span>
            連結別名 <small>相同別名可批次開啟</small>
          </span>
          <input
            value={alias}
            onChange={(event) => onAlias(event.target.value)}
            placeholder="例如：test"
            maxLength={64}
          />
        </label>
        <div className="form-bottom">
          <span>支援 http / https 網址；分類可自由輸入</span>
          <button className="button primary" type="submit" disabled={busy}>
            <Plus size={15} /> 儲存網址
          </button>
        </div>
      </form>
      <div className="section-heading">
        <div>
          <h2>
            已儲存網址 <span className="heading-count">{courses.length}</span>
          </h2>
          <p>每個別名代表一組連結；「開啟全部」會以同一個 Playwright 工作階段載入整組網址。</p>
        </div>
      </div>
      <div className="course-list">
        {[...groupedCourses.entries()].map(([groupName, groupCourses]) => (
          <section className="course-group" key={groupName}>
            <div className="course-group-heading">
              <FolderOpen size={15} />
              <h3>{groupName}</h3>
              <span>{groupCourses.length}</span>
              <div className="course-group-actions">
                <button
                  className="button mode-button headed small"
                  type="button"
                  onClick={() =>
                    onOpen(
                      groupCourses.map((course) => course.url),
                      groupName,
                      'headed'
                    )
                  }
                  disabled={busy || !selectedEmail}
                  title={
                    !selectedEmail
                      ? '請先選擇已登入的 Cool English 帳號'
                      : '在可見瀏覽器開啟全部連結'
                  }
                  aria-label={`以有頭瀏覽器開啟全部 ${groupCourses.length} 個 ${groupName} 連結`}
                >
                  <ExternalLink size={13} /> 開啟全部 · 有頭瀏覽器
                </button>
                <button
                  className="button mode-button headless small"
                  type="button"
                  onClick={() =>
                    onOpen(
                      groupCourses.map((course) => course.url),
                      groupName,
                      'headless'
                    )
                  }
                  disabled={busy || !selectedEmail}
                  title={
                    !selectedEmail ? '請先選擇已登入的 Cool English 帳號' : '在背景開啟全部連結'
                  }
                  aria-label={`以無頭背景模式開啟全部 ${groupCourses.length} 個 ${groupName} 連結`}
                >
                  <Globe2 size={13} /> 開啟全部 · 無頭背景
                </button>
              </div>
            </div>
            {groupCourses.map((course) => {
              let hostname = course.url
              try {
                hostname = new URL(course.url).hostname
              } catch {
                /* Invalid legacy entries remain visible for removal. */
              }
              return (
                <div className="course-item" key={course.url}>
                  <div className="course-index">
                    {String(courses.findIndex((item) => item.url === course.url) + 1).padStart(
                      2,
                      '0'
                    )}
                  </div>
                  <div className="course-favicon">
                    <Globe2 size={17} />
                  </div>
                  <div className="course-meta">
                    <strong>{hostname}</strong>
                    <span title={course.url}>{course.url}</span>
                  </div>
                  <select
                    className="course-category-select"
                    value={course.category}
                    onChange={(event) => {
                      if (event.target.value === '__new_category__') {
                        const category = window.prompt('輸入新分類名稱', course.category)
                        if (category?.trim()) onSetCategory(course.url, category)
                        else event.currentTarget.value = course.category
                        return
                      }
                      onSetCategory(course.url, event.target.value)
                    }}
                    disabled={busy}
                    aria-label={`變更 ${hostname} 的分類`}
                  >
                    {[...new Set([course.category, ...categories, '未分類'])].map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                    <option value="__new_category__">＋ 新增分類…</option>
                  </select>
                  <div className="course-open-actions">
                    <button
                      className="button mode-button headed small"
                      type="button"
                      onClick={() => onOpen([course.url], groupName, 'headed')}
                      disabled={busy || !selectedEmail}
                      title={
                        !selectedEmail
                          ? '請先選擇已登入的 Cool English 帳號'
                          : '在可見瀏覽器開啟此連結'
                      }
                      aria-label={`以有頭瀏覽器開啟 ${hostname}`}
                    >
                      <ExternalLink size={14} /> 有頭瀏覽器
                    </button>
                    <button
                      className="button mode-button headless small"
                      type="button"
                      onClick={() => onOpen([course.url], groupName, 'headless')}
                      disabled={busy || !selectedEmail}
                      title={
                        !selectedEmail ? '請先選擇已登入的 Cool English 帳號' : '在背景開啟此連結'
                      }
                      aria-label={`以無頭背景模式開啟 ${hostname}`}
                    >
                      <Globe2 size={13} /> 無頭背景
                    </button>
                  </div>
                  <button
                    className="mini-icon-button danger-hover"
                    title="移除網址"
                    onClick={() => onRemove(course.url)}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              )
            })}
          </section>
        ))}
        {!courses.length && (
          <div className="empty-state">
            <BookOpen size={25} />
            <strong>課程清單目前是空的</strong>
            <span>貼上課程連結後，就能在這裡快速開啟。</span>
          </div>
        )}
      </div>
    </div>
  )
}

function ReportsPage({
  accounts,
  selectedEmail,
  rows,
  settings,
  busy,
  onSelect,
  onFetch
}: {
  accounts: AccountRecord[]
  selectedEmail: string
  rows: CourseReportRow[]
  settings: AppSettings
  busy: boolean
  onSelect: (email: string) => void
  onFetch: () => void
}): React.JSX.Element {
  const currentMonth = new Date().toLocaleDateString('sv-SE').slice(0, 7).replace('-', '/')
  return (
    <div className="content-wrap">
      <PageHeading
        eyebrow="LEARNING REPORT"
        title="學習報表"
        description="從 Cool English 取得帳號可查看的學習時間紀錄。"
        action={
          <button className="button primary" onClick={onFetch} disabled={busy || !selectedEmail}>
            <RefreshCw size={15} /> 更新報表
          </button>
        }
      />
      <div className="report-toolbar">
        <label className="field inline-field">
          <span>使用帳號</span>
          <select
            value={selectedEmail}
            onChange={(event) => onSelect(event.target.value)}
            disabled={!accounts.length}
          >
            {accounts.map((account) => (
              <option key={account.email} value={account.email}>
                {account.name} · {account.email}
              </option>
            ))}
          </select>
        </label>
        <span className="report-source">
          <ShieldCheck size={14} /> 直接讀取官方報表
        </span>
      </div>
      <div className="report-table">
        <div className="table-head report-row">
          <span>學習月份</span>
          <span>停留平台時間</span>
          <span>觀看影片時間</span>
          <span>練習時間</span>
          <span>狀態</span>
        </div>
        {rows.map((row) => {
          const isCurrentMonth = row.month === currentMonth
          const warning = row.isBelowThreshold
          return (
            <div
              className={`table-row report-row ${warning ? 'below-threshold' : ''}`}
              key={row.month}
              style={
                warning
                  ? ({ '--warning-color': settings.reportWarningColor } as React.CSSProperties)
                  : undefined
              }
            >
              <strong>{row.month}</strong>
              <span>{row.platformTime}</span>
              <span>{row.videoTime}</span>
              <span>{row.practiceTime}</span>
              <span className="report-target">
                {warning
                  ? isCurrentMonth
                    ? '當月未達標'
                    : '未達標'
                  : isCurrentMonth
                    ? '當月'
                    : ''}
              </span>
            </div>
          )
        })}
        {!rows.length && (
          <div className="empty-state">
            <FileClock size={25} />
            <strong>尚無報表資料</strong>
            <span>選擇帳號後，按「更新報表」載入最新資料。</span>
          </div>
        )}
      </div>
      <p className="report-disclaimer">
        報表內容由網站提供；若登入已過期，請先至「帳號」重新登入並更新 cookie。
      </p>
    </div>
  )
}

function NetworkPage({
  sessions,
  courseProgress,
  mode,
  onModeChange,
  onDeleteSessions,
  onStopSession,
  onExportSession
}: {
  sessions: NetworkSession[]
  courseProgress: CourseProgressUpdate[]
  mode: NetworkMode
  onModeChange: (mode: NetworkMode) => void
  onDeleteSessions: (sessionIds: string[]) => Promise<void>
  onStopSession: (sessionId: string) => Promise<void>
  onExportSession: (sessionId: string) => Promise<{ canceled: boolean; filePath?: string }>
}): React.JSX.Element {
  const [view, setView] = useState<'active' | 'history'>('active')
  const [detailFormat, setDetailFormat] = useState<'formatted' | 'raw'>('formatted')
  const [rawRevision, setRawRevision] = useState(0)
  const [selectedSessionId, setSelectedSessionId] = useState('')
  const [selectingFor, setSelectingFor] = useState<NetworkMode | null>(null)
  const [selectedSessionIds, setSelectedSessionIds] = useState<Set<string>>(new Set())
  const [exportingSession, setExportingSession] = useState(false)
  const [exportFeedback, setExportFeedback] = useState('')
  const visibleSessions = sessions.filter(
    (session) =>
      (view === 'active' ? session.status === 'active' : session.status !== 'active') &&
      session.mode === mode
  )
  const visibleCourseProgress =
    view === 'active' ? courseProgress.filter((update) => update.mode === mode) : []
  const progressSessions = visibleCourseProgress.reduce<
    Map<
      string,
      {
        mode: LoginMode
        label: string
        status: CourseProgressUpdate['status']
        lines: string[]
      }
    >
  >((grouped, update) => {
    const current = grouped.get(update.sessionId) ?? {
      mode: update.mode,
      label: update.label,
      status: update.status,
      lines: []
    }
    current.status = update.status
    if (update.line) current.lines.push(update.line)
    grouped.set(update.sessionId, current)
    return grouped
  }, new Map())
  const headedCount = sessions.filter(
    (session) =>
      session.mode === 'headed' &&
      (view === 'active' ? session.status === 'active' : session.status !== 'active')
  ).length
  const headlessCount = sessions.filter(
    (session) =>
      session.mode === 'headless' &&
      (view === 'active' ? session.status === 'active' : session.status !== 'active')
  ).length
  const directCount = sessions.filter(
    (session) =>
      session.mode === 'direct' &&
      (view === 'active' ? session.status === 'active' : session.status !== 'active')
  ).length
  const selectedSession = sessions.find((session) => session.id === selectedSessionId)
  const toggleSessionSelection = (sessionId: string): void => {
    setSelectedSessionIds((current) => {
      const next = new Set(current)
      if (next.has(sessionId)) next.delete(sessionId)
      else next.add(sessionId)
      return next
    })
  }
  const deleteSelectedSessions = async (): Promise<void> => {
    const ids = visibleSessions
      .filter((session) => selectedSessionIds.has(session.id))
      .map((session) => session.id)
    if (!ids.length) return
    if (
      !window.confirm(
        `確定刪除選取的 ${ids.length} 筆${mode === 'headed' ? '有頭' : mode === 'headless' ? '無頭' : '直接請求'}歷史紀錄？此操作無法復原。`
      )
    )
      return
    try {
      await onDeleteSessions(ids)
      setSelectedSessionIds(new Set())
      setSelectingFor(null)
    } catch (error) {
      window.alert(error instanceof Error ? error.message : String(error))
    }
  }
  const toggleSelectAll = (): void => {
    const visibleIds = visibleSessions.map((session) => session.id)
    const hasAll = visibleIds.length > 0 && visibleIds.every((id) => selectedSessionIds.has(id))
    setSelectedSessionIds((current) => {
      const next = new Set(current)
      for (const id of visibleIds) {
        if (hasAll) next.delete(id)
        else next.add(id)
      }
      return next
    })
  }
  const beginSelecting = (targetMode: NetworkMode): void => {
    onModeChange(targetMode)
    setSelectedSessionId('')
    setSelectedSessionIds(new Set())
    setSelectingFor(targetMode)
  }
  const exportSession = async (sessionId: string): Promise<void> => {
    setExportingSession(true)
    setExportFeedback('')
    try {
      const result = await onExportSession(sessionId)
      if (!result.canceled) setExportFeedback(`已匯出：${result.filePath ?? 'JSON 檔案'}`)
    } catch (error) {
      setExportFeedback(error instanceof Error ? error.message : String(error))
    } finally {
      setExportingSession(false)
    }
  }

  if (selectedSession) {
    return (
      <div className="content-wrap">
        <PageHeading
          eyebrow="NETWORK SESSION"
          title={selectedSession.label}
          description={`${new Date(selectedSession.startedAt).toLocaleString()} · ${selectedSession.eventCount ?? selectedSession.events.length} 個網路事件`}
          action={
            <div className="network-detail-actions">
              {view === 'history' && selectedSession.status !== 'active' && (
                <button
                  className="button secondary"
                  disabled={exportingSession}
                  onClick={() => void exportSession(selectedSession.id)}
                >
                  <Download size={15} /> {exportingSession ? '匯出中…' : '匯出 JSON'}
                </button>
              )}
              <button className="button secondary" onClick={() => setSelectedSessionId('')}>
                <ArrowLeft size={15} /> 返回{view === 'active' ? '進行中' : '歷史紀錄'}
              </button>
            </div>
          }
        />
        {exportFeedback && (
          <p className="network-export-feedback" role="status">
            {exportFeedback}
          </p>
        )}
        <div className="network-session-detail">
          <div className="network-session-detail-heading">
            <span className={`network-mode ${selectedSession.mode}`}>
              {selectedSession.mode === 'headed'
                ? '有頭'
                : selectedSession.mode === 'headless'
                  ? '無頭'
                  : '直接請求'}
            </span>
            <span className={`session-status ${selectedSession.status}`}>
              {selectedSession.status === 'active'
                ? '執行中'
                : selectedSession.status === 'completed'
                  ? '完成'
                  : selectedSession.status === 'stopped'
                    ? '已停止'
                    : '失敗'}
            </span>
            {detailFormat === 'raw' && (
              <button
                className="button secondary"
                onClick={() => setRawRevision((revision) => revision + 1)}
              >
                <RefreshCw size={14} /> 更新原始數據
              </button>
            )}
            <div className="network-detail-format-tabs" role="tablist" aria-label="數據顯示方式">
              <button
                type="button"
                role="tab"
                aria-selected={detailFormat === 'formatted'}
                className={detailFormat === 'formatted' ? 'selected' : ''}
                onClick={() => setDetailFormat('formatted')}
              >
                排版檢視
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={detailFormat === 'raw'}
                className={detailFormat === 'raw' ? 'selected' : ''}
                onClick={() => setDetailFormat('raw')}
              >
                原始數據
              </button>
            </div>
          </div>
          {detailFormat === 'formatted' ? (
            <div className="network-session-events">
              {selectedSession.events
                .slice()
                .reverse()
                .map((event, index) => (
                  <NetworkEventRow event={event} key={`${event.time}-${index}`} />
                ))}
              {!selectedSession.events.length && <span>此工作階段尚無網路事件。</span>}
            </div>
          ) : (
            <div className="network-raw-data">
              <iframe
                key={`${selectedSession.id}-${rawRevision}`}
                className="network-raw-frame"
                title="此工作階段原始網路數據"
                src={`cool-body://${selectedSession.id}/raw?revision=${rawRevision}`}
              />
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="content-wrap">
      <PageHeading
        eyebrow="NETWORK INSPECTOR"
        title="網路紀錄"
        description="檢視瀏覽器工作階段及報表直接請求的 request、response 與失敗事件。本文是否保存由「設定 > 網路紀錄」控制；關閉時不保存 request／response 本文，開啟原始擷取時則以未加密原始位元組保存。"
        action={
          <div className="network-view-tabs">
            <button
              className={view === 'active' ? 'selected' : ''}
              onClick={() => {
                setSelectedSessionId('')
                setSelectingFor(null)
                setSelectedSessionIds(new Set())
                setView('active')
              }}
            >
              正在運行
            </button>
            <button
              className={view === 'history' ? 'selected' : ''}
              onClick={() => {
                setSelectedSessionId('')
                setSelectingFor(null)
                setSelectedSessionIds(new Set())
                setView('history')
              }}
            >
              歷史紀錄
            </button>
          </div>
        }
      />
      <div className="network-toolbar">
        <span>{visibleSessions.length} 個工作階段</span>
        <span>
          {mode === 'headed' ? '有頭' : mode === 'headless' ? '無頭' : '直接請求'} · 依執行批次分組
        </span>
      </div>
      <div className="network-mode-tabs-wrap">
        <div className="network-mode-tabs" role="tablist" aria-label="切換登入模式紀錄">
          <div className="network-mode-tab-group headed">
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'headed'}
              className={`mode-tab headed ${mode === 'headed' ? 'selected' : ''}`}
              onClick={() => {
                setSelectedSessionId('')
                setSelectedSessionIds(new Set())
                setSelectingFor(null)
                onModeChange('headed')
              }}
            >
              有頭紀錄 <span>{headedCount}</span>
            </button>
            {view === 'history' && (
              <button
                className={`network-mode-delete headed ${selectingFor === 'headed' ? 'selecting' : ''}`}
                type="button"
                title="選取有頭歷史紀錄以刪除"
                aria-label="刪除有頭紀錄"
                disabled={headedCount === 0}
                onClick={() => beginSelecting('headed')}
              >
                <Trash2 size={15} />
              </button>
            )}
          </div>
          <div className="network-mode-tab-group headless">
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'headless'}
              className={`mode-tab headless ${mode === 'headless' ? 'selected' : ''}`}
              onClick={() => {
                setSelectedSessionId('')
                setSelectedSessionIds(new Set())
                setSelectingFor(null)
                onModeChange('headless')
              }}
            >
              無頭紀錄 <span>{headlessCount}</span>
            </button>
            {view === 'history' && (
              <button
                className={`network-mode-delete headless ${selectingFor === 'headless' ? 'selecting' : ''}`}
                type="button"
                title="選取無頭歷史紀錄以刪除"
                aria-label="刪除無頭紀錄"
                disabled={headlessCount === 0}
                onClick={() => beginSelecting('headless')}
              >
                <Trash2 size={15} />
              </button>
            )}
          </div>
          <div className="network-mode-tab-group direct">
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'direct'}
              className={`mode-tab direct ${mode === 'direct' ? 'selected' : ''}`}
              onClick={() => {
                setSelectedSessionId('')
                setSelectedSessionIds(new Set())
                setSelectingFor(null)
                onModeChange('direct')
              }}
            >
              直接請求 <span>{directCount}</span>
            </button>
            {view === 'history' && (
              <button
                className={`network-mode-delete direct ${selectingFor === 'direct' ? 'selecting' : ''}`}
                type="button"
                title="選取直接請求歷史紀錄以刪除"
                aria-label="刪除直接請求紀錄"
                disabled={directCount === 0}
                onClick={() => beginSelecting('direct')}
              >
                <Trash2 size={15} />
              </button>
            )}
          </div>
        </div>
      </div>
      {selectingFor === mode && view === 'history' && (
        <div className="network-selection-toolbar">
          <label>
            <input
              type="checkbox"
              checked={
                visibleSessions.length > 0 &&
                visibleSessions.every((session) => selectedSessionIds.has(session.id))
              }
              onChange={toggleSelectAll}
            />
            全選本頁 {mode === 'headed' ? '有頭' : mode === 'headless' ? '無頭' : '直接請求'}紀錄
          </label>
          <span>已選 {selectedSessionIds.size} 筆</span>
          <button
            className="button danger network-selection-delete"
            type="button"
            disabled={!selectedSessionIds.size}
            onClick={() => void deleteSelectedSessions()}
          >
            <Trash2 size={14} /> 刪除選取
          </button>
          <button
            className="button ghost"
            type="button"
            onClick={() => {
              setSelectingFor(null)
              setSelectedSessionIds(new Set())
            }}
          >
            取消
          </button>
        </div>
      )}
      <div className="network-list">
        {[...progressSessions.entries()].map(([sessionId, progress]) => (
          <article className="network-session" key={sessionId}>
            <div className="network-session-header">
              <span className={`network-mode ${progress.mode}`}>
                {progress.mode === 'headed' ? '有頭' : '無頭'}
              </span>
              <strong>{progress.label}</strong>
              <span>即時進度 · 未保存網路事件</span>
              <span className={`session-status ${progress.status}`}>
                {progress.status === 'active'
                  ? '執行中'
                  : progress.status === 'completed'
                    ? '完成'
                    : progress.status === 'stopped'
                      ? '已停止'
                      : '失敗'}
              </span>
              {progress.status === 'active' && (
                <button
                  className="button danger network-session-stop"
                  type="button"
                  aria-label={`終止課程開啟：${progress.label}`}
                  onClick={() => void onStopSession(sessionId)}
                >
                  <X size={14} /> 終止
                </button>
              )}
            </div>
            {!!progress.lines.length && (
              <pre className="network-course-progress-log" role="log" aria-live="polite">
                {progress.lines.join('')}
              </pre>
            )}
          </article>
        ))}
        {visibleSessions.map((session) => (
          <article
            className={`network-session ${selectedSessionIds.has(session.id) ? 'selected-for-delete' : ''}`}
            key={session.id}
          >
            <div className="network-session-header">
              {selectingFor === mode && view === 'history' && (
                <input
                  type="checkbox"
                  aria-label={`選取 ${session.label}`}
                  checked={selectedSessionIds.has(session.id)}
                  onChange={() => toggleSessionSelection(session.id)}
                />
              )}
              <span className={`network-mode ${session.mode}`}>
                {session.mode === 'headed'
                  ? '有頭'
                  : session.mode === 'headless'
                    ? '無頭'
                    : '直接請求'}
              </span>
              <strong>{session.label}</strong>
              <span>{new Date(session.startedAt).toLocaleString()}</span>
              <span>{session.eventCount ?? session.events.length} events</span>
              <span className={`session-status ${session.status}`}>
                {session.status === 'active'
                  ? '執行中'
                  : session.status === 'completed'
                    ? '完成'
                    : session.status === 'stopped'
                      ? '已停止'
                      : '失敗'}
              </span>
              {view === 'active' && session.status === 'active' && (
                <button
                  className="button danger network-session-stop"
                  type="button"
                  aria-label={`終止工作階段：${session.label}`}
                  onClick={() => void onStopSession(session.id)}
                >
                  <X size={14} /> 終止
                </button>
              )}
              <button
                className="button ghost network-session-open"
                disabled={selectingFor === mode}
                onClick={() => setSelectedSessionId(session.id)}
              >
                看數據
              </button>
            </div>
          </article>
        ))}
        {!visibleSessions.length && !visibleCourseProgress.length && (
          <div className="empty-state">
            <Globe2 size={25} />
            <strong>
              {view === 'active'
                ? mode === 'direct'
                  ? '目前沒有進行中的直接請求'
                  : '目前沒有進行中的瀏覽器工作階段'
                : '尚無歷史紀錄'}
            </strong>
            <span>
              {mode === 'headed' ? '有頭' : mode === 'headless' ? '無頭' : '直接請求'}
              {view === 'active' ? '執行登入、開啟課程或報表' : '工作階段完成後'}
              ，這裡會保存實際網路事件。
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

function NetworkEventRow({ event }: { event: NetworkEvent }): React.JSX.Element {
  return (
    <div className="network-event">
      <span className={`event-kind ${event.kind}`}>
        {event.kind === 'request' ? 'REQ' : event.kind === 'response' ? 'RES' : 'ERR'}
      </span>
      <span className="event-method">{event.method ?? '—'}</span>
      <span className="event-url" title={event.url}>
        {event.url}
      </span>
      {event.status && (
        <span className={`event-status ${event.status >= 400 ? 'bad' : ''}`}>{event.status}</span>
      )}
      {event.message && <span className="event-message">{event.message}</span>}
      <time>{new Date(event.time).toLocaleTimeString()}</time>
      {(event.headers || event.bodyPreview || event.bodyAttachmentId || event.bodyCaptureError) && (
        <details className="network-details">
          <summary>檢視傳輸內容</summary>
          {event.headers && (
            <>
              <strong>Headers</strong>
              <pre>{JSON.stringify(event.headers, null, 2)}</pre>
            </>
          )}
          {event.bodyPreview && (
            <>
              <strong>Body preview</strong>
              <pre>{event.bodyPreview}</pre>
            </>
          )}
          {event.bodyAttachmentId && (
            <>
              <strong>
                {event.bodySource === 'request' ? '完整 Request Body' : '完整 Response Body'} ·{' '}
                {event.bodyBytes?.toLocaleString() ?? '未知'} bytes ·{' '}
                {event.bodyContentType ?? '未知格式'}
                {event.bodyStorage === 'raw' ? ' · 原始、未加密位元組' : ' · 系統加密保存'}
              </strong>
              <button
                className="button secondary"
                onClick={() =>
                  void window.cool.events
                    .openBody(event.sessionId, event.bodyAttachmentId!)
                    .catch((error: unknown) =>
                      window.alert(error instanceof Error ? error.message : String(error))
                    )
                }
              >
                在應用程式視窗開啟本文
              </button>
            </>
          )}
          {event.bodyCaptureError && (
            <>
              <strong>
                {event.bodySource === 'request' ? 'Request' : 'Response'} 本文擷取失敗
              </strong>
              <pre>{event.bodyCaptureError}</pre>
            </>
          )}
        </details>
      )}
    </div>
  )
}

function SettingsPage({
  settings,
  onChange
}: {
  settings: AppSettings
  onChange: (settings: AppSettings) => void
}): React.JSX.Element {
  type SectionId = SettingsCategoryId
  const [section, setSection] = useState<SectionId | null>(null)
  const [reorderMode, setReorderMode] = useState(false)
  const [draggedCategory, setDraggedCategory] = useState<SectionId | null>(null)
  const categoryClickTimer = useRef<number | null>(null)
  const update = (partial: Partial<AppSettings>): void => {
    const customizesColors = [
      'accentColor',
      'terminalCursorColor',
      'terminalTextColor',
      'terminalBackgroundColor',
      'textColor',
      'theme',
      'useCustomTextColor'
    ].some((key) => Object.hasOwn(partial, key))
    onChange({
      ...settings,
      ...partial,
      ...(customizesColors ? { colorThemeId: 'custom' } : {})
    })
  }
  const applyPreset = (id: string): void => {
    const preset = getColorThemePreset(id)
    if (!preset) return
    onChange({
      ...settings,
      colorThemeId: preset.id,
      theme: preset.theme,
      accentColor: preset.accentColor,
      textColor: preset.textColor,
      useCustomTextColor: true,
      invertColors: false,
      terminalCursorColor: preset.terminalCursorColor,
      terminalTextColor: preset.terminalTextColor,
      terminalBackgroundColor: preset.terminalBackgroundColor
    })
  }
  const sectionItems: {
    id: SectionId
    title: string
    description: string
    icon: typeof Settings2
  }[] = [
    {
      id: 'appearance',
      title: '外觀與配色',
      description: '24 組內建風格、介面色彩與字體',
      icon: Palette
    },
    {
      id: 'terminal',
      title: '終端',
      description: '終端字體、文字顏色與工作區配置',
      icon: TerminalSquare
    },
    {
      id: 'workspace',
      title: '工作區',
      description: '頁面與終端的排列方式',
      icon: SlidersHorizontal
    },
    {
      id: 'reports',
      title: '學習報表',
      description: '未達標顏色與每月時數門檻',
      icon: Activity
    },
    {
      id: 'cli-report-colors',
      title: 'CLI 報表配色',
      description: '自訂 cool -c 學習報表的七種顏色',
      icon: Palette
    },
    {
      id: 'network-history',
      title: '網路紀錄',
      description: '管理紀錄開關與自動刪除時間',
      icon: Globe2
    },
    {
      id: 'privacy',
      title: '資料與隱私',
      description: '本機資料保護與帳號 Cookie',
      icon: ShieldCheck
    }
  ]
  const sectionTitles: Record<SectionId, string> = {
    appearance: '外觀與配色',
    terminal: '終端',
    workspace: '工作區',
    reports: '學習報表',
    'cli-report-colors': 'CLI 報表配色',
    'network-history': '網路紀錄',
    privacy: '資料與隱私'
  }
  const selectedPreset = getColorThemePreset(settings.colorThemeId)
  const retentionUnit =
    settings.networkHistoryRetentionMinutes % (24 * 60) === 0
      ? { label: '天', minutes: 24 * 60 }
      : settings.networkHistoryRetentionMinutes % 60 === 0
        ? { label: '小時', minutes: 60 }
        : { label: '分鐘', minutes: 1 }
  const retentionValue = settings.networkHistoryRetentionMinutes / retentionUnit.minutes
  const orderedSectionItems = normalizeSettingsCategoryOrder(settings.settingsCategoryOrder)
    .map((id) => sectionItems.find((item) => item.id === id))
    .filter((item): item is (typeof sectionItems)[number] => item !== undefined)
  const reorderCategory = (targetId: SectionId): void => {
    if (!draggedCategory || draggedCategory === targetId) return
    const next = orderedSectionItems.map((item) => item.id)
    const fromIndex = next.indexOf(draggedCategory)
    const toIndex = next.indexOf(targetId)
    if (fromIndex < 0 || toIndex < 0) return
    next.splice(fromIndex, 1)
    next.splice(toIndex, 0, draggedCategory)
    update({ settingsCategoryOrder: next })
    setDraggedCategory(null)
  }

  return (
    <div className="content-wrap settings-page">
      <PageHeading
        eyebrow="PREFERENCES"
        title={section ? sectionTitles[section] : '設定'}
        description={
          section
            ? '調整此分類的偏好設定，變更會即時套用並自動保存。'
            : '選擇一個設定分類，進入專屬頁面調整。'
        }
      />
      {section ? (
        <>
          <button className="settings-back-button" type="button" onClick={() => setSection(null)}>
            <ArrowLeft size={15} /> 所有設定
          </button>
          {section === 'appearance' && (
            <>
              <section className="panel preference-controls">
                <div className="settings-section-heading">
                  <h2>內建配色風格</h2>
                  <span>{colorThemePresets.length} 種風格</span>
                </div>
                <p className="preference-section-note">
                  每種風格都有自己的介面背景與卡片色，不是只有黑白切換；同時套用強調色與終端配色。
                </p>
                <div className="color-theme-grid">
                  {colorThemePresets.map((preset) => (
                    <button
                      key={preset.id}
                      className={`color-theme-card ${settings.colorThemeId === preset.id ? 'selected' : ''}`}
                      type="button"
                      aria-pressed={settings.colorThemeId === preset.id}
                      onClick={() => applyPreset(preset.id)}
                    >
                      <span
                        className={`color-theme-preview ${preset.theme}`}
                        aria-label={`${preset.name}介面背景、卡片與終端配色預覽`}
                        style={{
                          background: preset.interfaceBackgroundColor,
                          borderColor: preset.interfaceSurfaceColor
                        }}
                      >
                        <i style={{ background: preset.interfaceSurfaceColor }} />
                        <i style={{ background: preset.accentColor }} />
                        <i style={{ background: preset.terminalBackgroundColor }} />
                        <i style={{ background: preset.terminalTextColor }} />
                      </span>
                      <span className="color-theme-name">{preset.name}</span>
                      <span className="color-theme-group">
                        {preset.group} · {preset.theme === 'dark' ? '深色' : '淺色'}
                      </span>
                    </button>
                  ))}
                </div>
                <p className="preference-help">目前風格：{selectedPreset?.name ?? '自訂配色'}</p>
              </section>
              <section className="panel preference-controls">
                <h2>自訂介面顏色</h2>
                <label className="preference-control">
                  <span>外觀</span>
                  <select
                    value={settings.theme}
                    onChange={(event) =>
                      update({ theme: event.target.value as AppSettings['theme'] })
                    }
                  >
                    <option value="dark">深色</option>
                    <option value="light">淺色</option>
                  </select>
                </label>
                <label className="preference-control">
                  <span>強調色</span>
                  <input
                    aria-label="選擇介面強調色"
                    type="color"
                    value={settings.accentColor}
                    onChange={(event) => update({ accentColor: event.target.value })}
                  />
                </label>
                <label className="preference-control">
                  <span>自訂介面文字色</span>
                  <input
                    aria-label="啟用自訂介面文字顏色"
                    type="checkbox"
                    checked={settings.useCustomTextColor}
                    onChange={(event) => update({ useCustomTextColor: event.target.checked })}
                  />
                </label>
                <label className="preference-control">
                  <span>介面文字色</span>
                  <input
                    aria-label="選擇介面文字顏色"
                    type="color"
                    value={settings.textColor}
                    disabled={!settings.useCustomTextColor}
                    onChange={(event) => update({ textColor: event.target.value })}
                  />
                </label>
                <label className="preference-control">
                  <span>反轉介面文字顏色（不變更背景）</span>
                  <input
                    aria-label="反轉介面文字顏色"
                    type="checkbox"
                    checked={settings.invertColors}
                    onChange={(event) => update({ invertColors: event.target.checked })}
                  />
                </label>
                {settings.useCustomTextColor && (
                  <p className="preference-help">
                    文字對比{' '}
                    {contrastRatio(
                      settings.textColor,
                      textContrastBackground(settings.theme)
                    ).toFixed(1)}
                    :1；低於 4.5:1 時會使用易讀的主題文字色。狀態與操作元件保留各自的對比色。
                  </p>
                )}
              </section>
              <section className="panel preference-controls">
                <h2>介面字體</h2>
                <label className="preference-control">
                  <span>字體家族</span>
                  <select
                    value={settings.fontFamily}
                    onChange={(event) =>
                      update({ fontFamily: normalizeFontFamily(event.target.value) })
                    }
                  >
                    <option value="system">系統預設（Inter／微軟正黑體）</option>
                    <option value="segoe">Segoe UI／微軟正黑體</option>
                    <option value="arial">Arial／微軟正黑體</option>
                    <option value="consolas">Consolas／微軟正黑體</option>
                  </select>
                </label>
                <div className="preference-control font-size-preference">
                  <span>
                    介面字體大小 <strong>{settings.fontSize}px</strong>
                  </span>
                  <div className="font-size-control">
                    <button
                      className="font-size-step"
                      type="button"
                      aria-label="縮小介面字體"
                      disabled={settings.fontSize <= 10}
                      onClick={() => update({ fontSize: Math.max(10, settings.fontSize - 1) })}
                    >
                      A−
                    </button>
                    <input
                      type="range"
                      min="10"
                      max="24"
                      value={settings.fontSize}
                      aria-label="介面字體大小"
                      onChange={(event) => update({ fontSize: Number(event.target.value) })}
                    />
                    <button
                      className="font-size-step"
                      type="button"
                      aria-label="放大介面字體"
                      disabled={settings.fontSize >= 24}
                      onClick={() => update({ fontSize: Math.min(24, settings.fontSize + 1) })}
                    >
                      A+
                    </button>
                  </div>
                </div>
              </section>
            </>
          )}
          {section === 'terminal' && (
            <>
              <section className="panel preference-controls">
                <h2>終端字體</h2>
                <p className="preference-section-note">
                  終端使用等寬字體；此設定與介面字體大小分開保存。
                </p>
                <div className="preference-control font-size-preference">
                  <span>
                    終端字體大小 <strong>{settings.terminalFontSize}px</strong>
                  </span>
                  <div className="font-size-control">
                    <button
                      className="font-size-step"
                      type="button"
                      aria-label="縮小終端字體"
                      disabled={settings.terminalFontSize <= 10}
                      onClick={() =>
                        update({ terminalFontSize: Math.max(10, settings.terminalFontSize - 1) })
                      }
                    >
                      A−
                    </button>
                    <input
                      type="range"
                      min="10"
                      max="24"
                      value={settings.terminalFontSize}
                      aria-label="終端字體大小"
                      onChange={(event) => update({ terminalFontSize: Number(event.target.value) })}
                    />
                    <button
                      className="font-size-step"
                      type="button"
                      aria-label="放大終端字體"
                      disabled={settings.terminalFontSize >= 24}
                      onClick={() =>
                        update({ terminalFontSize: Math.min(24, settings.terminalFontSize + 1) })
                      }
                    >
                      A+
                    </button>
                  </div>
                </div>
              </section>
              <section className="panel preference-controls">
                <h2>終端顏色</h2>
                <label className="preference-control">
                  <span>游標顏色</span>
                  <input
                    aria-label="選擇終端游標顏色"
                    type="color"
                    value={settings.terminalCursorColor}
                    onChange={(event) => update({ terminalCursorColor: event.target.value })}
                  />
                </label>
                <label className="preference-control">
                  <span>文字顏色</span>
                  <input
                    aria-label="選擇終端文字顏色"
                    type="color"
                    value={settings.terminalTextColor}
                    onChange={(event) => update({ terminalTextColor: event.target.value })}
                  />
                </label>
                <label className="preference-control">
                  <span>背景顏色</span>
                  <input
                    aria-label="選擇終端背景顏色"
                    type="color"
                    value={settings.terminalBackgroundColor}
                    onChange={(event) => update({ terminalBackgroundColor: event.target.value })}
                  />
                </label>
                <p className="preference-help">
                  游標、文字與背景顏色會和終端中的 `cool -c` 雙向同步。
                </p>
              </section>
            </>
          )}
          {section === 'workspace' && (
            <section className="panel preference-controls">
              <h2>工作區配置</h2>
              <label className="preference-control">
                <span>側邊選單顯示方式</span>
                <select
                  value={settings.sidebarMode}
                  onChange={(event) =>
                    update({ sidebarMode: event.target.value as AppSettings['sidebarMode'] })
                  }
                >
                  <option value="click">點擊圖示顯示，再次點擊隱藏</option>
                  <option value="hover">滑鼠靠近左側顯示，移出右側隱藏</option>
                </select>
              </label>
              <label className="preference-control">
                <span>終端與頁面排列</span>
                <select
                  value={settings.terminalLayout}
                  onChange={(event) =>
                    update({ terminalLayout: event.target.value as AppSettings['terminalLayout'] })
                  }
                >
                  <option value="vertical">上下分割</option>
                  <option value="horizontal">左右分割</option>
                </select>
              </label>
              <label className="preference-control">
                <span>
                  工作區比例 <strong>{Math.round(settings.splitRatio * 100)}%</strong>
                </span>
                <input
                  type="range"
                  min="30"
                  max="80"
                  value={Math.round(settings.splitRatio * 100)}
                  onChange={(event) => update({ splitRatio: Number(event.target.value) / 100 })}
                />
              </label>
            </section>
          )}
          {section === 'reports' && (
            <section className="panel preference-controls">
              <h2>學習報表</h2>
              <label className="preference-control">
                <span>未達標文字顏色</span>
                <input
                  type="color"
                  value={settings.reportWarningColor}
                  onChange={(event) => update({ reportWarningColor: event.target.value })}
                />
              </label>
              <label className="preference-control">
                <span>每月未達標門檻</span>
                <select
                  value={settings.reportThresholdMinutes}
                  onChange={(event) =>
                    update({ reportThresholdMinutes: Number(event.target.value) })
                  }
                >
                  {[6, 8, 10, 12, 15, 20, 30, 40].map((hours) => (
                    <option key={hours} value={hours * 60}>
                      {hours} 小時
                    </option>
                  ))}
                </select>
              </label>
            </section>
          )}
          {section === 'cli-report-colors' && (
            <section className="panel preference-controls">
              <h2>CLI 報表配色</h2>
              <CliReportColorEditor settings={settings} onChange={update} />
            </section>
          )}
          {section === 'network-history' && (
            <>
              <section className="panel preference-controls">
                <h2>網路紀錄管理</h2>
                <p className="preference-section-note">
                  不限制工作階段或事件筆數。永久保留會持續增加本機儲存空間；可選擇定期清除舊工作階段。
                </p>
                <label className="preference-control">
                  <span>紀錄方式</span>
                  <select
                    value={settings.networkHistoryMode}
                    onChange={(event) =>
                      update({
                        networkHistoryMode: event.target.value as AppSettings['networkHistoryMode']
                      })
                    }
                  >
                    <option value="keep">持續紀錄，永久保留</option>
                    <option value="expire">持續紀錄，定時刪除舊紀錄</option>
                    <option value="disabled">永久不紀錄新網路事件</option>
                  </select>
                </label>
                <label className="preference-control">
                  <span>記錄原始 Request／Response 本文</span>
                  <input
                    type="checkbox"
                    checked={settings.networkCaptureRawBodies}
                    onChange={(event) => update({ networkCaptureRawBodies: event.target.checked })}
                  />
                </label>
                <p className="preference-help">
                  關閉時不保存任何 request／response 本文，只保留網路事件及已遮蔽的
                  URL／Headers，以避免大量本文造成記憶體與效能問題。開啟後，新請求會以原始位元組保存本文，不遮蔽、不截斷、不加密；內容僅留本機，可能包含密碼、Cookie、權杖或個人資料。設定只影響之後的新請求；Chromium
                  CDP 無法提供的 multipart 上傳檔案內容會標示擷取失敗，不會保存不完整本文。
                </p>
                {settings.networkHistoryMode === 'expire' && (
                  <label className="preference-control">
                    <span>工作階段結束後保留</span>
                    <span className="network-retention-input">
                      <input
                        aria-label="網路紀錄保留時間"
                        type="number"
                        min="1"
                        max={Math.floor(52_560_000 / retentionUnit.minutes)}
                        step="1"
                        value={retentionValue}
                        onChange={(event) => {
                          const value = Number(event.target.value)
                          if (
                            !Number.isSafeInteger(value) ||
                            value < 1 ||
                            value > Math.floor(52_560_000 / retentionUnit.minutes)
                          ) {
                            return
                          }
                          update({
                            networkHistoryRetentionMinutes: value * retentionUnit.minutes
                          })
                        }}
                      />
                      <select
                        aria-label="網路紀錄保留時間單位"
                        value={retentionUnit.minutes}
                        onChange={(event) => {
                          const minutes = Number(event.target.value)
                          update({
                            networkHistoryRetentionMinutes: Math.max(
                              1,
                              Math.min(52_560_000, Math.round(retentionValue * minutes))
                            )
                          })
                        }}
                      >
                        <option value="1">分鐘</option>
                        <option value="60">小時</option>
                        <option value="1440">天</option>
                      </select>
                    </span>
                  </label>
                )}
                <p className="preference-help">
                  {settings.networkHistoryMode === 'disabled'
                    ? '停用期間不會新增網路紀錄；既有紀錄會保留，除非另行刪除。'
                    : settings.networkHistoryMode === 'expire'
                      ? `工作階段結束 ${retentionValue} ${retentionUnit.label}後自動刪除整筆紀錄。`
                      : '所有網路工作階段與事件都會保留，直到你手動刪除。'}
                </p>
              </section>
            </>
          )}
          {section === 'privacy' && (
            <>
              <section className="panel settings-card">
                <div className="settings-row">
                  <div className="settings-row-icon">
                    <ShieldCheck size={17} />
                  </div>
                  <div>
                    <strong>本機加密儲存</strong>
                    <p>密碼與 cookie 分開存放，並以 Windows 系統加密保護，不會上傳。</p>
                  </div>
                  <span className="status-pill">
                    <span className="status-indicator" /> 已啟用
                  </span>
                </div>
                <div className="settings-row">
                  <div className="settings-row-icon">
                    <LockKeyhole size={17} />
                  </div>
                  <div>
                    <strong>帳密與 Cookie</strong>
                    <p>Cookie 依實際登入狀態驗證；Session cookie 以線上檢查判定狀態。</p>
                  </div>
                </div>
              </section>
              <div className="settings-note">
                <CircleHelp size={16} />
                <span>
                  移轉舊版資料時，請保留原專案資料夾中的 <code>accounts.json</code> 與{' '}
                  <code>cookies</code>；啟動時會自動嘗試匯入。
                </span>
              </div>
            </>
          )}
        </>
      ) : (
        <>
          <div className="settings-category-tools">
            <p>
              {reorderMode
                ? '拖曳分類卡片調整順序，完成後按「完成排序」。'
                : '雙擊任一分類卡片進入排序模式，可拖曳調整排列。'}
            </p>
            {reorderMode && (
              <button
                className="button secondary"
                type="button"
                onClick={() => {
                  setReorderMode(false)
                  setDraggedCategory(null)
                }}
              >
                完成排序
              </button>
            )}
          </div>
          <div className={`settings-category-grid ${reorderMode ? 'reordering' : ''}`}>
            {orderedSectionItems.map((item) => {
              const Icon = item.icon
              return (
                <button
                  key={item.id}
                  className={`settings-category-card ${draggedCategory === item.id ? 'dragging' : ''}`}
                  type="button"
                  draggable={reorderMode}
                  title={reorderMode ? '拖曳到目標位置以重新排序' : '雙擊以調整分類順序'}
                  onClick={() => {
                    if (reorderMode) return
                    if (categoryClickTimer.current !== null)
                      window.clearTimeout(categoryClickTimer.current)
                    categoryClickTimer.current = window.setTimeout(() => {
                      setSection(item.id)
                      categoryClickTimer.current = null
                    }, 220)
                  }}
                  onDoubleClick={() => {
                    if (categoryClickTimer.current !== null) {
                      window.clearTimeout(categoryClickTimer.current)
                      categoryClickTimer.current = null
                    }
                    setReorderMode((value) => !value)
                    setDraggedCategory(null)
                  }}
                  onDragStart={(event) => {
                    if (!reorderMode) {
                      event.preventDefault()
                      return
                    }
                    setDraggedCategory(item.id)
                    event.dataTransfer.effectAllowed = 'move'
                    event.dataTransfer.setData('text/plain', item.id)
                  }}
                  onDragOver={(event) => {
                    if (reorderMode) {
                      event.preventDefault()
                      event.dataTransfer.dropEffect = 'move'
                    }
                  }}
                  onDrop={(event) => {
                    event.preventDefault()
                    reorderCategory(item.id)
                  }}
                  onDragEnd={() => setDraggedCategory(null)}
                >
                  <span className="settings-category-icon">
                    <Icon size={19} />
                  </span>
                  <span className="settings-category-copy">
                    <strong>{item.title}</strong>
                    <small>{item.description}</small>
                  </span>
                  <ArrowUpRight size={16} className="settings-category-arrow" />
                </button>
              )
            })}
            <section className="panel settings-about-card">
              <div className="settings-row-icon">
                <Activity size={17} />
              </div>
              <div className="settings-about-copy">
                <strong>Cool Desktop</strong>
                <p>版本 {window.cool.app.version}</p>
                <p>早期測試版本：v0.0.1，感謝白老鼠協助測試。</p>
                <p>
                  作者：
                  <a
                    href="https://www.instagram.com/c.pls._/"
                    onClick={(event) => {
                      event.preventDefault()
                      window.cool.app.openExternal(event.currentTarget.href)
                    }}
                  >
                    Instagram
                  </a>
                </p>
                <p>
                  白老鼠：
                  <a
                    href="https://www.instagram.com/wzhe_1231/"
                    onClick={(event) => {
                      event.preventDefault()
                      window.cool.app.openExternal(event.currentTarget.href)
                    }}
                  >
                    Instagram
                  </a>
                </p>
                <p>
                  問題討論群組：私訊作者加入（
                  <a
                    href="https://www.instagram.com/c.pls._/"
                    onClick={(event) => {
                      event.preventDefault()
                      window.cool.app.openExternal(event.currentTarget.href)
                    }}
                  >
                    Instagram
                  </a>
                  ）
                </p>
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  )
}

export default App
