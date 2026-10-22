import { app, BrowserWindow, clipboard, dialog, ipcMain, protocol, shell } from 'electron'
import { spawn, type IPty } from 'node-pty'
import { execFileSync } from 'child_process'
import { dirname, join, resolve } from 'path'
import { accessSync, constants as fsConstants, existsSync, unwatchFile, watchFile } from 'fs'
import { readFile, writeFile } from 'fs/promises'
import { homedir } from 'os'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import {
  getAccounts,
  addCourses,
  getCourses,
  importCliCourseUrls,
  initializeCliCourseUrls,
  initializeStorage,
  removeAccount,
  removeCliAccount,
  removeCourse,
  renameAccount,
  setCourseCategory,
  getSettings,
  saveSettings,
  readCliColors,
  getCredential,
  syncCliAccounts,
  syncCliCourseUrls,
  syncDesktopAccountsToCli,
  writeCliCourseUrls
} from './services/storage'
import {
  beginLogin,
  checkCookie,
  closeBrowsers,
  fetchReport,
  openCourses,
  stopNetworkSessionWork
} from './services/site'
import {
  initializeNetworkHistory,
  configureNetworkHistory,
  listNetworkSessions,
  removeNetworkSessions,
  streamNetworkBody,
  streamNetworkSessionExport,
  streamNetworkSessionRaw
} from './services/networkHistory'
import type { CourseProgressUpdate, TerminalProfile } from '../shared/types'
import { cliColorMappings } from '../shared/cliReportColors'
import { projectStartupArgs, projectStartupInput } from '../shared/terminalProfiles'
import { TerminalOutputGate } from '../shared/terminalOutputGate'

type TerminalSession = { pty: IPty; lineBuffer: string; output: TerminalOutputGate }
const terminals = new Map<number, Map<string, TerminalSession>>()
let cliAccountsPath: string | undefined
let cliAccountsSnapshot: string | undefined
let cliAccountsSyncTimer: NodeJS.Timeout | undefined
let cliAccountsSyncRunning = false
let cliAccountsSyncAgain = false
let cliCourseUrlsPath: string | undefined
let cliCourseUrlsSyncTimer: NodeJS.Timeout | undefined
let cliCourseUrlsSyncRunning = false
let cliCourseUrlsSyncAgain = false
let cliCourseUrlsSnapshot: string | undefined
let cliColorsPath: string | undefined
let cliColorsTimer: NodeJS.Timeout | undefined
let cliColorsSnapshot: string | undefined

protocol.registerSchemesAsPrivileged([
  {
    scheme: 'cool-body',
    privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true }
  }
])

function registerNetworkBodyProtocol(): void {
  protocol.handle('cool-body', (request) => {
    const url = new URL(request.url)
    const chunks =
      url.pathname === '/raw'
        ? streamNetworkSessionRaw(url.hostname)
        : streamNetworkBody(url.hostname, url.pathname.slice(1))
    const body = new ReadableStream<Uint8Array>({
      async pull(controller) {
        try {
          const next = await chunks.next()
          if (next.done) controller.close()
          else controller.enqueue(next.value)
        } catch (error) {
          controller.error(error)
        }
      },
      async cancel() {
        await chunks.return(undefined)
      }
    })
    return new Response(body, {
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Security-Policy': "default-src 'none'; sandbox",
        'X-Content-Type-Options': 'nosniff'
      }
    })
  })
}

function openNetworkBodyWindow(sessionId: string, bodyAttachmentId: string): void {
  const bodyWindow = new BrowserWindow({
    width: 900,
    height: 700,
    minWidth: 600,
    minHeight: 400,
    autoHideMenuBar: true,
    title: '網路本文',
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true }
  })
  void bodyWindow
    .loadURL(`cool-body://${encodeURIComponent(sessionId)}/${encodeURIComponent(bodyAttachmentId)}`)
    .catch((error: unknown) => {
      console.error('無法開啟網路回應本文：', error)
      if (!bodyWindow.isDestroyed()) bodyWindow.close()
    })
}

async function readCliColorsContents(): Promise<string> {
  if (!cliColorsPath) return ''
  try {
    return await readFile(cliColorsPath, 'utf8')
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return ''
    throw error
  }
}

async function syncCliColors(): Promise<void> {
  try {
    const contents = await readCliColorsContents()
    if (contents === cliColorsSnapshot) return
    const cliColors = await readCliColors(getCliDataDirectory())
    cliColorsSnapshot = contents
    if (!Object.keys(cliColors).length) return
    const currentSettings = await getSettings()
    const nextSettings = { ...currentSettings, ...cliColors }
    const changed = cliColorMappings.some(
      ([, key]) => key in cliColors && currentSettings[key] !== nextSettings[key]
    )
    if (!changed) return
    await saveSettings(nextSettings)
    for (const window of BrowserWindow.getAllWindows()) {
      if (!window.isDestroyed()) window.webContents.send('settings:cli-colors', cliColors)
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    console.error('Unable to sync CLI colors:', message)
    for (const window of BrowserWindow.getAllWindows()) {
      if (!window.isDestroyed()) window.webContents.send('settings:cli-colors-error', message)
    }
  }
}

async function watchCliColors(): Promise<void> {
  cliColorsPath = join(getCliDataDirectory(), 'colors.json')
  cliColorsSnapshot = await readCliColorsContents()
  watchFile(cliColorsPath, { interval: 500, persistent: false }, (current, previous) => {
    if (
      current.mtimeMs === previous.mtimeMs &&
      current.ctimeMs === previous.ctimeMs &&
      current.size === previous.size
    ) {
      return
    }
    if (cliColorsTimer) clearTimeout(cliColorsTimer)
    cliColorsTimer = setTimeout(() => {
      cliColorsTimer = undefined
      void syncCliColors()
    }, 180)
  })
}

function executablePath(name: string): string | undefined {
  try {
    return execFileSync(process.platform === 'win32' ? 'where.exe' : 'which', [name], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore']
    })
      .split(/\r?\n/)[0]
      .trim()
  } catch {
    return undefined
  }
}

function getProjectRoot(): string {
  const candidates = [
    process.cwd(),
    resolve(process.cwd(), '..'),
    resolve(app.getAppPath(), '..'),
    resolve(app.getAppPath(), '..', '..'),
    app.getAppPath(),
    join(process.resourcesPath, 'cool-cli'),
    process.resourcesPath,
    dirname(process.execPath)
  ].filter((candidate): candidate is string => !!candidate)
  const projectRoot = candidates.find((candidate) => existsSync(join(candidate, 'cool.py')))
  return resolve(projectRoot ?? process.cwd())
}

function getCliDataDirectory(): string {
  const projectRoot = getProjectRoot()
  try {
    accessSync(projectRoot, fsConstants.W_OK)
    return projectRoot
  } catch {
    return join(homedir(), '.config', 'cool')
  }
}

async function syncTerminalAccounts(showStartupError = false): Promise<void> {
  if (cliAccountsSyncRunning) {
    cliAccountsSyncAgain = true
    return
  }
  cliAccountsSyncRunning = true
  try {
    do {
      cliAccountsSyncAgain = false
      try {
        const emails = await syncCliAccounts(getCliDataDirectory())
        await syncDesktopAccountsToCli(getCliDataDirectory())
        if (cliAccountsPath) {
          try {
            cliAccountsSnapshot = await readFile(cliAccountsPath, 'utf8')
          } catch (error) {
            if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
            cliAccountsSnapshot = undefined
          }
        }
        if (emails.length) {
          for (const window of BrowserWindow.getAllWindows()) {
            if (!window.isDestroyed()) window.webContents.send('accounts:cli-sync', emails)
          }
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)
        console.error('Unable to sync terminal CLI accounts:', message)
        const windows = BrowserWindow.getAllWindows()
        if (showStartupError && windows.length === 0) {
          dialog.showErrorBox('終端帳號同步失敗', message)
        }
        for (const window of windows) {
          if (!window.isDestroyed()) window.webContents.send('accounts:cli-sync-error', message)
        }
      }
    } while (cliAccountsSyncAgain)
  } finally {
    cliAccountsSyncRunning = false
  }
}

async function syncDesktopAccountsToTerminal(): Promise<void> {
  try {
    await syncDesktopAccountsToCli(getCliDataDirectory())
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    console.error('Unable to sync desktop accounts to terminal CLI:', message)
    for (const window of BrowserWindow.getAllWindows()) {
      if (!window.isDestroyed()) window.webContents.send('accounts:cli-sync-error', message)
    }
  }
}

async function watchTerminalAccounts(): Promise<void> {
  cliAccountsPath = join(getCliDataDirectory(), 'accounts.json')
  try {
    cliAccountsSnapshot = await readFile(cliAccountsPath, 'utf8')
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
    cliAccountsSnapshot = undefined
  }
  watchFile(cliAccountsPath, { interval: 1000, persistent: false }, (current, previous) => {
    if (
      current.mtimeMs === previous.mtimeMs &&
      current.ctimeMs === previous.ctimeMs &&
      current.size === previous.size
    ) {
      return
    }
    if (cliAccountsSyncTimer) clearTimeout(cliAccountsSyncTimer)
    cliAccountsSyncTimer = setTimeout(() => {
      cliAccountsSyncTimer = undefined
      void readFile(cliAccountsPath as string, 'utf8')
        .then((contents) => {
          if (contents !== cliAccountsSnapshot) void syncTerminalAccounts()
        })
        .catch((error: unknown) => {
          if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
            console.error('Unable to read changed terminal accounts:', error)
            void syncTerminalAccounts()
          }
        })
    }, 300)
  })
}

async function writeDesktopCourseUrls(): Promise<void> {
  const cliDataDirectory = getCliDataDirectory()
  const urlsPath = join(cliDataDirectory, 'urls.txt')
  const diskBeforeWrite = await readFile(urlsPath, 'utf8')
  if (cliCourseUrlsSnapshot !== undefined && diskBeforeWrite !== cliCourseUrlsSnapshot) {
    await syncCliCourseUrls(cliDataDirectory, cliCourseUrlsSnapshot)
    cliCourseUrlsSnapshot = diskBeforeWrite
  }
  const writtenContents = await writeCliCourseUrls(cliDataDirectory)
  cliCourseUrlsSnapshot = writtenContents
  const diskContents = await readFile(urlsPath, 'utf8')
  if (diskContents !== writtenContents) {
    cliCourseUrlsSyncAgain = true
    void syncTerminalCourseUrls()
  }
}

async function syncTerminalCourseUrls(): Promise<void> {
  if (cliCourseUrlsSyncRunning) {
    cliCourseUrlsSyncAgain = true
    return
  }
  cliCourseUrlsSyncRunning = true
  try {
    do {
      cliCourseUrlsSyncAgain = false
      try {
        if (!cliCourseUrlsPath) return
        const contents = await readFile(cliCourseUrlsPath, 'utf8')
        if (contents === cliCourseUrlsSnapshot) continue
        const previousContents = cliCourseUrlsSnapshot ?? ''
        const courses = await syncCliCourseUrls(getCliDataDirectory(), previousContents)
        cliCourseUrlsSnapshot = contents
        for (const window of BrowserWindow.getAllWindows()) {
          if (!window.isDestroyed()) window.webContents.send('courses:cli-sync', courses)
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)
        console.error('Unable to sync terminal course URLs:', message)
        for (const window of BrowserWindow.getAllWindows()) {
          if (!window.isDestroyed()) window.webContents.send('courses:cli-sync-error', message)
        }
      }
    } while (cliCourseUrlsSyncAgain)
  } finally {
    cliCourseUrlsSyncRunning = false
  }
}

async function watchTerminalCourseUrls(): Promise<void> {
  cliCourseUrlsPath = join(getCliDataDirectory(), 'urls.txt')
  cliCourseUrlsSnapshot = await readFile(cliCourseUrlsPath, 'utf8')
  watchFile(cliCourseUrlsPath, { interval: 250, persistent: false }, (current, previous) => {
    if (
      current.mtimeMs === previous.mtimeMs &&
      current.ctimeMs === previous.ctimeMs &&
      current.size === previous.size
    ) {
      return
    }
    if (cliCourseUrlsSyncTimer) clearTimeout(cliCourseUrlsSyncTimer)
    cliCourseUrlsSyncTimer = setTimeout(() => {
      cliCourseUrlsSyncTimer = undefined
      cliCourseUrlsSyncAgain = true
      void syncTerminalCourseUrls()
    }, 120)
  })
}

function publishCourseProgress(window: BrowserWindow, update: CourseProgressUpdate): void {
  if (!window.isDestroyed()) window.webContents.send('courses:progress', update)
}

function getTerminalProfiles(): TerminalProfile[] {
  const profiles: TerminalProfile[] = []
  const projectRoot = getProjectRoot()
  if (process.platform !== 'win32') {
    for (const [id, label, command] of [
      ['zsh', 'zsh', 'zsh'],
      ['bash', 'Bash', 'bash'],
      ['sh', 'Shell', 'sh']
    ]) {
      const path = executablePath(command)
      const args =
        id === 'zsh' ? ['-f', '-i'] : id === 'bash' ? ['--noprofile', '--norc', '-i'] : ['-i']
      if (path) profiles.push({ id, label, command: path, args, cwd: projectRoot })
    }
    return profiles
  }
  const root = process.env.SystemRoot ?? 'C:\\Windows'
  profiles.push(
    {
      id: 'windows-powershell',
      label: 'Windows PowerShell',
      command: join(root, 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe'),
      args: ['-NoLogo', '-NoProfile'],
      cwd: projectRoot
    },
    {
      id: 'command-prompt',
      label: '命令提示字元',
      command: join(root, 'System32', 'cmd.exe'),
      args: ['/K'],
      cwd: projectRoot
    }
  )
  const pwsh = executablePath('pwsh.exe')
  if (pwsh)
    profiles.push({
      id: 'powershell',
      label: 'PowerShell',
      command: pwsh,
      args: ['-NoLogo'],
      cwd: projectRoot
    })

  const vswhere = join(
    process.env['ProgramFiles(x86)'] ?? 'C:\\Program Files (x86)',
    'Microsoft Visual Studio',
    'Installer',
    'vswhere.exe'
  )
  try {
    const installPath = execFileSync(
      vswhere,
      ['-latest', '-products', '*', '-property', 'installationPath'],
      { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }
    ).trim()
    if (installPath) {
      const tools = join(installPath, 'Common7', 'Tools')
      const commandPrompt = join(tools, 'VsDevCmd.bat')
      const developerShell = join(tools, 'Launch-VsDevShell.ps1')
      profiles.push({
        id: 'vs-developer-command',
        label: 'Developer Command Prompt for VS',
        command: join(root, 'System32', 'cmd.exe'),
        args: ['/K', `call "${commandPrompt}"`],
        cwd: projectRoot
      })
      profiles.push({
        id: 'vs-developer-powershell',
        label: 'Developer PowerShell for VS',
        command: profiles.find((profile) => profile.id === 'windows-powershell')!.command,
        args: [
          '-NoLogo',
          '-NoExit',
          '-Command',
          `& '${developerShell.replace(/'/g, "''")}' -SkipAutomaticLocation`
        ],
        cwd: projectRoot
      })
    }
  } catch {
    // Visual Studio command-line tools are optional.
  }
  return profiles
}

function createTerminal(
  window: BrowserWindow,
  profileId: string
): { id: string; profileId: string; label: string } {
  const profile = getTerminalProfiles().find((item) => item.id === profileId)
  if (!profile) throw new Error('所選終端設定不存在或尚未安裝。')
  const cwd = profile.cwd ?? getProjectRoot()
  let python: { command: string; prefixArgs: string[] } | undefined
  if (process.platform === 'win32') {
    const interpreter = executablePath('python.exe')
    const launcher = interpreter ? undefined : executablePath('py.exe')
    if (interpreter) python = { command: interpreter, prefixArgs: [] }
    else if (launcher) python = { command: launcher, prefixArgs: ['-3'] }
  } else {
    const interpreter = executablePath('python3')
    if (interpreter) python = { command: interpreter, prefixArgs: [] }
  }
  if (!python) throw new Error('找不到 Python。請確認 Python 已加入 PATH。')
  const scriptPath = join(getProjectRoot(), 'cool.py')
  if (!existsSync(scriptPath)) throw new Error(`找不到 Cool 專案腳本：${scriptPath}`)
  const args = projectStartupArgs(
    profile,
    cwd,
    scriptPath,
    python.command,
    python.prefixArgs,
    process.platform
  )
  let startupInput = projectStartupInput(profile, scriptPath, python.command, python.prefixArgs)
  const environment = {
    ...process.env,
    TERM: 'xterm-256color',
    COLORTERM: 'truecolor',
    PYTHONUTF8: '1',
    PYTHONIOENCODING: 'utf-8'
  }

  const terminalId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  const terminal = spawn(profile.command, args, {
    name: 'xterm-256color',
    cols: 100,
    rows: 28,
    cwd,
    env: environment,
    useConpty: process.platform === 'win32',
    useConptyDll: process.platform === 'win32'
  })
  const windowTerminals = terminals.get(window.id) ?? new Map<string, TerminalSession>()
  const terminalSession: TerminalSession = {
    pty: terminal,
    lineBuffer: '',
    output: new TerminalOutputGate((data) => {
      if (!window.isDestroyed()) window.webContents.send('terminal:data', terminalId, data)
    })
  }
  windowTerminals.set(terminalId, terminalSession)
  terminals.set(window.id, windowTerminals)
  terminal.onData((data) => {
    if (startupInput) {
      terminal.write(`${startupInput}\r`)
      startupInput = undefined
    }
    terminalSession.output.write(data)
  })
  terminal.onExit(({ exitCode }) => {
    const current = terminals.get(window.id)
    current?.delete(terminalId)
    if (current?.size === 0) terminals.delete(window.id)
    if (!window.isDestroyed()) window.webContents.send('terminal:exit', terminalId, exitCode)
    void syncTerminalAccounts()
  })
  return { id: terminalId, profileId, label: profile.label }
}

function registerIpc(): void {
  ipcMain.handle('terminal:profiles', () => getTerminalProfiles())
  ipcMain.handle('terminal:start', (event, profileId: unknown) => {
    const window = BrowserWindow.fromWebContents(event.sender)
    if (!window) throw new Error('找不到應用程式視窗。')
    if (typeof profileId !== 'string') throw new Error('終端設定不合法。')
    return createTerminal(window, profileId)
  })
  ipcMain.on('terminal:ready', (event, terminalId: unknown) => {
    const window = BrowserWindow.fromWebContents(event.sender)
    const session =
      window && typeof terminalId === 'string'
        ? terminals.get(window.id)?.get(terminalId)
        : undefined
    if (!window || !session) return
    session.output.markReady()
  })
  ipcMain.on('terminal:stop', (event, terminalId: unknown) => {
    const window = BrowserWindow.fromWebContents(event.sender)
    if (window && typeof terminalId === 'string') {
      terminals.get(window.id)?.get(terminalId)?.pty.kill()
    }
  })
  ipcMain.on('terminal:write', (event, terminalId: unknown, data: unknown) => {
    const window = BrowserWindow.fromWebContents(event.sender)
    const session =
      window && typeof terminalId === 'string'
        ? terminals.get(window.id)?.get(terminalId)
        : undefined
    if (!session || typeof data !== 'string') return
    let write = ''
    for (const char of data) {
      if (char === '\r' || char === '\n') {
        if (session.lineBuffer === '/exit') {
          window?.close()
          return
        }
        session.lineBuffer = ''
        write += char
      } else if (char === '\x03') {
        session.lineBuffer = ''
        write += char
      } else if (char === '\x7f' || char === '\b') {
        session.lineBuffer = session.lineBuffer.slice(0, -1)
        write += char
      } else if (char === '\x1b') {
        session.lineBuffer = ''
        write += char
      } else {
        if (char >= ' ' && char <= '~' && session.lineBuffer.length < 256) {
          session.lineBuffer += char
        } else if (char.charCodeAt(0) > 127 && session.lineBuffer.length < 256) {
          session.lineBuffer += char
        }
        write += char
      }
    }
    if (write) session.pty.write(write)
  })
  ipcMain.on('terminal:resize', (event, terminalId: unknown, columns: unknown, rows: unknown) => {
    const window = BrowserWindow.fromWebContents(event.sender)
    const session =
      window && typeof terminalId === 'string'
        ? terminals.get(window.id)?.get(terminalId)
        : undefined
    if (
      session &&
      Number.isInteger(columns) &&
      Number.isInteger(rows) &&
      (columns as number) > 0 &&
      (rows as number) > 0
    ) {
      session.pty.resize(columns as number, rows as number)
    }
  })

  ipcMain.handle('accounts:list', () => getAccounts())
  ipcMain.handle('accounts:rename', async (_event, email: string, name: string) => {
    const accounts = await renameAccount(email, name)
    await syncDesktopAccountsToTerminal()
    return accounts
  })
  ipcMain.handle('accounts:remove', async (_event, email: string) => {
    const accounts = await removeAccount(email)
    try {
      await removeCliAccount(email, getCliDataDirectory())
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      console.error('Unable to remove terminal CLI account:', message)
      for (const window of BrowserWindow.getAllWindows()) {
        if (!window.isDestroyed()) window.webContents.send('accounts:cli-sync-error', message)
      }
    }
    return accounts
  })
  ipcMain.handle(
    'accounts:login',
    (event, email: string, password: string, name: string, mode: 'headed' | 'headless') => {
      const window = BrowserWindow.fromWebContents(event.sender)
      if (!window) throw new Error('找不到應用程式視窗。')
      return beginLogin(window, email, password, name, mode).then(async (accounts) => {
        await syncDesktopAccountsToTerminal()
        return accounts
      })
    }
  )
  ipcMain.handle(
    'accounts:login-saved',
    async (event, email: string, mode: 'headed' | 'headless') => {
      const window = BrowserWindow.fromWebContents(event.sender)
      if (!window) throw new Error('找不到應用程式視窗。')
      if (!['headed', 'headless'].includes(mode)) throw new Error('登入模式不合法。')
      const account = (await getAccounts()).find(
        (item) => item.email.toLowerCase() === email.toLowerCase()
      )
      if (!account) throw new Error('找不到指定帳號。')
      const password = await getCredential(account.email)
      if (!password) throw new Error('此帳號沒有已儲存的密碼，請使用上方帳號密碼表單重新連結。')
      return beginLogin(window, account.email, password, account.name, mode).then(
        async (accounts) => {
          await syncDesktopAccountsToTerminal()
          return accounts
        }
      )
    }
  )
  ipcMain.handle('accounts:cookie:check', (event, email: string) => {
    const window = BrowserWindow.fromWebContents(event.sender)
    if (!window) throw new Error('找不到應用程式視窗。')
    return checkCookie(window, email)
  })

  ipcMain.handle('courses:list', () => getCourses())
  ipcMain.handle('courses:add', async (_event, urls: string[], category: string, alias: string) => {
    const cliDataDirectory = getCliDataDirectory()
    await importCliCourseUrls(cliDataDirectory)
    await addCourses(urls, category, alias)
    await writeDesktopCourseUrls()
    return getCourses()
  })
  ipcMain.handle('courses:setCategory', async (_event, url: string, category: string) => {
    const cliDataDirectory = getCliDataDirectory()
    await importCliCourseUrls(cliDataDirectory)
    await setCourseCategory(url, category)
    await writeDesktopCourseUrls()
    return getCourses()
  })
  ipcMain.handle('courses:remove', async (_event, url: string) => {
    const cliDataDirectory = getCliDataDirectory()
    await importCliCourseUrls(cliDataDirectory)
    await removeCourse(url)
    await writeDesktopCourseUrls()
    return getCourses()
  })
  ipcMain.handle(
    'courses:open',
    async (
      event,
      urls: string[],
      accountEmail: string,
      mode: 'headed' | 'headless',
      label: string
    ) => {
      const window = BrowserWindow.fromWebContents(event.sender)
      if (!window) throw new Error('找不到應用程式視窗。')
      return openCourses(window, urls, accountEmail, mode, label, (update) =>
        publishCourseProgress(window, update)
      )
    }
  )
  ipcMain.handle('reports:fetch', async (event, accountEmail: string, thresholdMinutes: number) => {
    const window = BrowserWindow.fromWebContents(event.sender)
    if (!window) throw new Error('找不到應用程式視窗。')
    return fetchReport(window, accountEmail, thresholdMinutes)
  })
  ipcMain.handle('events:list', () => listNetworkSessions())
  ipcMain.handle('events:open-body', (_event, sessionId: unknown, bodyAttachmentId: unknown) => {
    if (
      typeof sessionId !== 'string' ||
      typeof bodyAttachmentId !== 'string' ||
      !sessionId ||
      !bodyAttachmentId
    ) {
      throw new Error('網路本文附件參數不合法。')
    }
    openNetworkBodyWindow(sessionId, bodyAttachmentId)
  })
  ipcMain.handle('events:export', async (event, sessionId: unknown) => {
    const window = BrowserWindow.fromWebContents(event.sender)
    if (!window) throw new Error('找不到應用程式視窗。')
    if (typeof sessionId !== 'string' || !sessionId) {
      throw new Error('網路工作階段 ID 不合法。')
    }
    const sessions = await listNetworkSessions()
    const session = sessions.find((item) => item.id === sessionId)
    if (!session) throw new Error('此網路紀錄已不存在，請重新整理清單後再試。')
    if (session.status === 'active') throw new Error('進行中的工作階段不可匯出為歷史紀錄。')
    const safeLabel = Array.from(session.label, (character) =>
      /[<>:"/\\|?*]/.test(character) || character.charCodeAt(0) < 32 ? '_' : character
    )
      .join('')
      .trim()
    const timestamp = session.startedAt.replace(/[:.]/g, '-')
    const result = await dialog.showSaveDialog(window, {
      title: '匯出網路紀錄',
      defaultPath: join(
        app.getPath('downloads'),
        `${safeLabel || 'network-session'}-${session.mode}-${timestamp}.json`
      ),
      filters: [{ name: 'JSON', extensions: ['json'] }]
    })
    if (result.canceled || !result.filePath) return { canceled: true }
    await writeFile(result.filePath, streamNetworkSessionExport(sessionId), {
      encoding: 'utf8',
      mode: 0o600
    })
    return { canceled: false, filePath: result.filePath }
  })
  ipcMain.handle('events:stop', (_event, sessionId: unknown) => {
    if (typeof sessionId !== 'string' || !sessionId) {
      throw new Error('網路工作階段 ID 不合法。')
    }
    return stopNetworkSessionWork(sessionId)
  })
  ipcMain.handle('events:remove', (_event, sessionIds: unknown) => {
    if (!Array.isArray(sessionIds) || sessionIds.some((id) => typeof id !== 'string')) {
      throw new Error('網路紀錄選取資料不合法。')
    }
    return removeNetworkSessions(sessionIds)
  })
  ipcMain.handle('settings:get', () => getSettings(getCliDataDirectory()))
  ipcMain.handle('settings:save', async (_event, settings) => {
    const saved = await saveSettings(settings, getCliDataDirectory())
    await configureNetworkHistory(saved)
    cliColorsSnapshot = await readCliColorsContents()
    return saved
  })
  ipcMain.handle('clipboard:read', () => clipboard.readText())
  ipcMain.on('clipboard:write', (_event, text: unknown) => {
    if (typeof text === 'string') clipboard.writeText(text)
  })
  ipcMain.on('app:openExternal', (_event, rawUrl: unknown) => {
    if (typeof rawUrl !== 'string') return
    try {
      const url = new URL(rawUrl)
      if (url.protocol === 'https:' || url.protocol === 'http:')
        void shell.openExternal(url.toString())
    } catch {
      // Ignore invalid external URLs from the renderer.
    }
  })
  ipcMain.on('window:minimize', (event) => {
    BrowserWindow.fromWebContents(event.sender)?.minimize()
  })
  ipcMain.on('window:toggleMaximize', (event) => {
    const window = BrowserWindow.fromWebContents(event.sender)
    if (!window) return
    if (window.isMaximized()) window.unmaximize()
    else window.maximize()
  })
  ipcMain.on('window:close', (event) => {
    BrowserWindow.fromWebContents(event.sender)?.close()
  })
}

function createWindow(): BrowserWindow {
  const mainWindow = new BrowserWindow({
    width: 1360,
    height: 900,
    minWidth: 1000,
    minHeight: 680,
    show: false,
    autoHideMenuBar: true,
    backgroundColor: '#0b0d10',
    title: 'cool — 學習工作台',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  })

  mainWindow.once('ready-to-show', () => mainWindow.show())
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    try {
      const parsed = new URL(url)
      if (parsed.protocol === 'https:' || parsed.protocol === 'http:') {
        void shell.openExternal(parsed.toString())
      }
    } catch {
      // Ignore malformed window-open requests.
    }
    return { action: 'deny' }
  })
  mainWindow.on('closed', () => {
    for (const session of terminals.get(mainWindow.id)?.values() ?? []) session.pty.kill()
    terminals.delete(mainWindow.id)
  })

  if (is.dev && process.env.ELECTRON_RENDERER_URL) {
    void mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    void mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
  return mainWindow
}

app.whenReady().then(async () => {
  electronApp.setAppUserModelId('com.coolenglish.desktop')
  app.on('browser-window-created', (_event, window) => optimizer.watchWindowShortcuts(window))
  registerNetworkBodyProtocol()
  registerIpc()
  try {
    await initializeStorage()
    await initializeCliCourseUrls(getCliDataDirectory())
    const settings = await getSettings(getCliDataDirectory())
    await watchCliColors()
    await watchTerminalCourseUrls()
    await initializeNetworkHistory()
    await configureNetworkHistory(settings)
    await watchTerminalAccounts()
    await syncTerminalAccounts(true)
  } catch (error) {
    dialog.showErrorBox(
      'Cool Desktop 無法啟動',
      error instanceof Error ? error.message : String(error)
    )
    app.quit()
    return
  }
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('before-quit', () => {
  if (cliAccountsPath) unwatchFile(cliAccountsPath)
  if (cliCourseUrlsPath) unwatchFile(cliCourseUrlsPath)
  if (cliColorsPath) unwatchFile(cliColorsPath)
  if (cliAccountsSyncTimer) clearTimeout(cliAccountsSyncTimer)
  if (cliCourseUrlsSyncTimer) clearTimeout(cliCourseUrlsSyncTimer)
  if (cliColorsTimer) clearTimeout(cliColorsTimer)
  for (const windowTerminals of terminals.values()) {
    for (const session of windowTerminals.values()) session.pty.kill()
  }
  terminals.clear()
  void closeBrowsers()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

export { app }
