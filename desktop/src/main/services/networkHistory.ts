import { app, BrowserWindow, safeStorage } from 'electron'
import { mkdir, readFile, rename, rm, writeFile } from 'fs/promises'
import { dirname, join } from 'path'
import { randomUUID } from 'crypto'
import type {
  AppSettings,
  NetworkEvent,
  NetworkMode,
  NetworkSession,
  NetworkSessionSummary
} from '../../shared/types'
import { canTransitionNetworkSession, type NetworkSessionStatus } from './networkSessionState'
import { isNetworkSessionExpired } from './networkHistoryRetention'
import {
  serializeNetworkSessionExport,
  serializeNetworkSessionRaw
} from '../../shared/networkSessionExport'
import {
  createNetworkBodyCapture,
  readEncryptedNetworkBody,
  readRawNetworkBody,
  type NetworkBodyCapture
} from './networkBodyStore'

const historyPath = (): string => join(app.getPath('userData'), 'data', 'network-sessions.json')
const bodyRootPath = (): string => join(app.getPath('userData'), 'data', 'network-bodies')
const sessions: NetworkSession[] = []
let persistTimer: NodeJS.Timeout | undefined
let persistDirty = false
let persistRunning: Promise<void> | undefined
let historyMode: AppSettings['networkHistoryMode'] = 'keep'
let historyRetentionMinutes = 1440
let captureRawBodies = false
let retentionTimer: NodeJS.Timeout | undefined

function summarize(session: NetworkSession): NetworkSessionSummary {
  return {
    id: session.id,
    label: session.label,
    mode: session.mode,
    startedAt: session.startedAt,
    ...(session.endedAt ? { endedAt: session.endedAt } : {}),
    status: session.status,
    eventCount: session.events.length
  }
}

function publish(session: NetworkSession): void {
  const summary = summarize(session)
  for (const window of BrowserWindow.getAllWindows()) {
    if (!window.isDestroyed()) window.webContents.send('network:session', summary)
  }
}

async function* serializeSessions(): AsyncGenerator<string> {
  yield '['
  for (let sessionIndex = 0; sessionIndex < sessions.length; sessionIndex += 1) {
    const { events, ...metadata } = sessions[sessionIndex]
    const serializedMetadata = JSON.stringify(metadata)
    yield `${sessionIndex ? ',' : ''}${serializedMetadata.slice(0, -1)},"events":[`
    for (let eventIndex = 0; eventIndex < events.length; eventIndex += 1) {
      yield `${eventIndex ? ',' : ''}${JSON.stringify(events[eventIndex])}`
    }
    yield ']}'
  }
  yield ']'
}

async function writeSessionSnapshot(): Promise<void> {
  const file = historyPath()
  const temp = `${file}.${process.pid}.tmp`
  await mkdir(dirname(file), { recursive: true })
  try {
    await writeFile(temp, serializeSessions(), { encoding: 'utf8', mode: 0o600 })
    await rename(temp, file)
  } finally {
    await rm(temp, { force: true })
  }
}

function schedulePersist(): void {
  persistDirty = true
  if (persistTimer) return
  persistTimer = setTimeout(() => {
    persistTimer = undefined
    void flushPersist().catch((error: unknown) =>
      console.error('無法保存 Playwright 歷史紀錄：', error)
    )
  }, 1_000)
}

async function flushPersist(): Promise<void> {
  if (persistTimer) {
    clearTimeout(persistTimer)
    persistTimer = undefined
  }
  if (persistRunning) {
    await persistRunning
    if (persistDirty) await flushPersist()
    return
  }

  persistRunning = (async () => {
    try {
      do {
        persistDirty = false
        await writeSessionSnapshot()
      } while (persistDirty)
    } catch (error) {
      persistDirty = true
      throw error
    }
  })()
  try {
    await persistRunning
  } finally {
    persistRunning = undefined
  }
}

async function persist(): Promise<void> {
  persistDirty = true
  await flushPersist()
}

async function expireOldSessions(): Promise<void> {
  if (historyMode !== 'expire') return
  let writeIndex = 0
  const expiredSessionIds: string[] = []
  for (const session of sessions) {
    if (!isNetworkSessionExpired(session, historyRetentionMinutes)) {
      sessions[writeIndex] = session
      writeIndex += 1
    } else {
      expiredSessionIds.push(session.id)
    }
  }
  if (writeIndex === sessions.length) return
  sessions.splice(writeIndex)
  await persist()
  await Promise.all(expiredSessionIds.map(deleteNetworkBodies))
  for (const window of BrowserWindow.getAllWindows()) {
    if (!window.isDestroyed()) window.webContents.send('network:history-changed')
  }
}

function scheduleRetentionCleanup(): void {
  if (retentionTimer) clearInterval(retentionTimer)
  retentionTimer = undefined
  if (historyMode !== 'expire') return
  retentionTimer = setInterval(() => {
    void expireOldSessions().catch((error: unknown) =>
      console.error('無法清理到期網路紀錄：', error)
    )
  }, 10_000)
  retentionTimer.unref()
}

export async function configureNetworkHistory(
  settings: Pick<
    AppSettings,
    'networkHistoryMode' | 'networkHistoryRetentionMinutes' | 'networkCaptureRawBodies'
  >
): Promise<void> {
  historyMode = settings.networkHistoryMode
  historyRetentionMinutes = settings.networkHistoryRetentionMinutes
  captureRawBodies = settings.networkCaptureRawBodies
  scheduleRetentionCleanup()
  await expireOldSessions()
}

export function isNetworkHistoryEnabled(): boolean {
  return historyMode !== 'disabled'
}

export async function initializeNetworkHistory(): Promise<void> {
  let recoveredActiveSession = false
  try {
    const parsed: unknown = JSON.parse(await readFile(historyPath(), 'utf8'))
    if (!Array.isArray(parsed)) throw new Error('Playwright 紀錄檔格式錯誤。')
    for (const item of parsed) {
      if (
        item &&
        typeof item === 'object' &&
        typeof item.id === 'string' &&
        Array.isArray(item.events)
      ) {
        const session = item as NetworkSession
        if (session.status === 'active') {
          session.status = 'failed'
          session.endedAt = new Date().toISOString()
          recoveredActiveSession = true
        }
        sessions.push(session)
      }
    }
    if (recoveredActiveSession) await persist()
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error
  }
  await expireOldSessions()
  scheduleRetentionCleanup()
}

export async function listNetworkSessions(): Promise<NetworkSession[]> {
  return [...sessions].reverse()
}

export function getNetworkSessionForExport(sessionId: string): NetworkSession {
  const session = sessions.find((item) => item.id === sessionId)
  if (!session) throw new Error('此網路紀錄已不存在，請重新整理清單後再試。')
  if (session.status === 'active') throw new Error('進行中的工作階段不可匯出為歷史紀錄。')
  return {
    ...session,
    events: session.events.map((event) => ({
      ...event,
      ...(event.headers ? { headers: { ...event.headers } } : {})
    }))
  }
}

export function isNetworkSessionActive(sessionId: string): boolean {
  return sessions.some((session) => session.id === sessionId && session.status === 'active')
}

export function canCaptureNetworkBody(sessionId: string): boolean {
  const session = sessions.find((item) => item.id === sessionId)
  return captureRawBodies && historyMode !== 'disabled' && !!session && session.status === 'active'
}

export function shouldCaptureRawNetworkBodies(): boolean {
  return captureRawBodies
}

export async function beginNetworkBodyCapture(
  sessionId: string,
  encoding: 'text' | 'hex',
  raw = false
): Promise<NetworkBodyCapture> {
  if (!canCaptureNetworkBody(sessionId)) {
    throw new Error('此網路工作階段目前不可擷取本文。')
  }
  if (!raw && !safeStorage.isEncryptionAvailable()) {
    throw new Error('系統安全儲存目前不可用，無法安全保存網路回應本文。')
  }
  return createNetworkBodyCapture(
    bodyRootPath(),
    sessionId,
    encoding,
    raw ? 'raw' : 'encrypted',
    raw ? undefined : (value) => safeStorage.encryptString(value)
  )
}

export function getNetworkBodyPath(sessionId: string, bodyAttachmentId: string): string {
  if (!/^[0-9a-f-]{36}$/i.test(bodyAttachmentId)) {
    throw new Error('網路本文附件 ID 不合法。')
  }
  const session = sessions.find((item) => item.id === sessionId)
  if (!session || !session.events.some((event) => event.bodyAttachmentId === bodyAttachmentId)) {
    throw new Error('找不到此網路本文附件。')
  }
  return join(bodyRootPath(), sessionId, `${bodyAttachmentId}.body`)
}

export async function* streamNetworkBody(
  sessionId: string,
  bodyAttachmentId: string
): AsyncGenerator<Buffer> {
  const filePath = getNetworkBodyPath(sessionId, bodyAttachmentId)
  const event = sessions
    .find((session) => session.id === sessionId)
    ?.events.find((item) => item.bodyAttachmentId === bodyAttachmentId)
  if (event?.bodyStorage === 'raw') {
    yield* readRawNetworkBody(filePath)
    return
  }
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error('系統安全儲存目前不可用，無法解密網路回應本文。')
  }
  yield* readEncryptedNetworkBody(filePath, (value) => safeStorage.decryptString(value))
}

export async function* streamNetworkSessionRaw(sessionId: string): AsyncGenerator<Buffer> {
  const session = sessions.find((item) => item.id === sessionId)
  if (!session) throw new Error('此網路紀錄已不存在，請重新整理清單後再試。')
  for await (const chunk of serializeNetworkSessionRaw(session, (id) =>
    streamNetworkBody(sessionId, id)
  )) {
    yield Buffer.from(chunk, 'utf8')
  }
}

export async function* streamNetworkSessionExport(sessionId: string): AsyncGenerator<string> {
  const session = getNetworkSessionForExport(sessionId)
  for await (const chunk of serializeNetworkSessionExport(session, (id) =>
    streamNetworkBody(sessionId, id)
  )) {
    yield chunk
  }
}

async function deleteNetworkBodies(sessionId: string): Promise<void> {
  await rm(join(bodyRootPath(), sessionId), { recursive: true, force: true })
}

export async function removeNetworkSessions(sessionIds: string[]): Promise<NetworkSession[]> {
  const uniqueIds = [...new Set(sessionIds)]
  if (!uniqueIds.length || uniqueIds.some((id) => !id)) {
    throw new Error('請選擇至少一筆網路紀錄。')
  }
  const selected = uniqueIds.map((id) => sessions.find((session) => session.id === id))
  if (selected.some((session) => !session)) {
    throw new Error('部分網路紀錄已不存在，請重新整理清單後再試。')
  }
  if (selected.some((session) => session?.status === 'active')) {
    throw new Error('進行中的工作階段不可刪除，請等它結束後再從歷史紀錄清除。')
  }
  const selectedSet = new Set(uniqueIds)
  for (let index = sessions.length - 1; index >= 0; index -= 1) {
    if (selectedSet.has(sessions[index].id)) sessions.splice(index, 1)
  }
  await persist()
  await Promise.all(uniqueIds.map(deleteNetworkBodies))
  return listNetworkSessions()
}

export async function beginNetworkSession(mode: NetworkMode, label: string): Promise<string> {
  if (historyMode === 'disabled') return randomUUID()
  const session: NetworkSession = {
    id: randomUUID(),
    label,
    mode,
    startedAt: new Date().toISOString(),
    status: 'active',
    events: []
  }
  sessions.push(session)
  await persist()
  publish(session)
  return session.id
}

export async function updateNetworkSessionMode(
  sessionId: string,
  mode: 'headed' | 'headless'
): Promise<void> {
  if (historyMode === 'disabled') return
  const session = sessions.find((item) => item.id === sessionId)
  if (!session || session.status !== 'active') {
    throw new Error('無法更新已結束或不存在的網路工作階段。')
  }
  if (session.mode === mode) return
  session.mode = mode
  publish(session)
  await persist()
}

export async function recordNetworkEvent(
  window: BrowserWindow,
  sessionId: string,
  event: Omit<NetworkEvent, 'sessionId' | 'sessionLabel' | 'mode'>
): Promise<void> {
  if (historyMode === 'disabled') return
  const session = sessions.find((item) => item.id === sessionId)
  if (!session) throw new Error(`找不到 Playwright 工作階段：${sessionId}`)
  if (session.status !== 'active') return
  const fullEvent: NetworkEvent = {
    ...event,
    sessionId,
    sessionLabel: session.label,
    mode: session.mode
  }
  session.events.push(fullEvent)
  if (!window.isDestroyed()) window.webContents.send('network:event', fullEvent)
  schedulePersist()
  publish(session)
}

export async function endNetworkSession(
  sessionId: string,
  status: Exclude<NetworkSessionStatus, 'active'>
): Promise<void> {
  const session = sessions.find((item) => item.id === sessionId)
  if (!session || !canTransitionNetworkSession(session.status, status)) return
  session.status = status
  session.endedAt = new Date().toISOString()
  publish(session)
  await persist()
}
