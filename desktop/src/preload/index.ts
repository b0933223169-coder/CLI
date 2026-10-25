import { contextBridge, ipcRenderer } from 'electron'
import type { CoolApi, CourseProgressUpdate, CourseReportRow, NetworkEvent } from '../shared/types'

const api: CoolApi = {
  terminal: {
    profiles: () => ipcRenderer.invoke('terminal:profiles'),
    start: (profileId) => ipcRenderer.invoke('terminal:start', profileId),
    ready: (terminalId) => ipcRenderer.send('terminal:ready', terminalId),
    stop: (terminalId) => ipcRenderer.send('terminal:stop', terminalId),
    write: (terminalId, data) => ipcRenderer.send('terminal:write', terminalId, data),
    resize: (terminalId, columns, rows) =>
      ipcRenderer.send('terminal:resize', terminalId, columns, rows),
    onData: (callback) => {
      const listener = (
        _event: Electron.IpcRendererEvent,
        terminalId: string,
        data: string
      ): void => callback(terminalId, data)
      ipcRenderer.on('terminal:data', listener)
      return () => ipcRenderer.removeListener('terminal:data', listener)
    },
    onExit: (callback) => {
      const listener = (
        _event: Electron.IpcRendererEvent,
        terminalId: string,
        code: number
      ): void => callback(terminalId, code)
      ipcRenderer.on('terminal:exit', listener)
      return () => ipcRenderer.removeListener('terminal:exit', listener)
    }
  },
  accounts: {
    list: () => ipcRenderer.invoke('accounts:list'),
    onLoginSuccess: (callback) => {
      const listener = (_event: Electron.IpcRendererEvent, email: string): void => callback(email)
      ipcRenderer.on('accounts:login-success', listener)
      return () => ipcRenderer.removeListener('accounts:login-success', listener)
    },
    onLoginInteractionRequired: (callback) => {
      const listener = (_event: Electron.IpcRendererEvent, message: string): void =>
        callback(message)
      ipcRenderer.on('accounts:login-interaction-required', listener)
      return () => ipcRenderer.removeListener('accounts:login-interaction-required', listener)
    },
    onLoginStatus: (callback) => {
      const listener = (_event: Electron.IpcRendererEvent, message: string): void =>
        callback(message)
      ipcRenderer.on('accounts:login-status', listener)
      return () => ipcRenderer.removeListener('accounts:login-status', listener)
    },
    onCliSync: (callback) => {
      const listener = (_event: Electron.IpcRendererEvent, emails: string[]): void =>
        callback(emails)
      ipcRenderer.on('accounts:cli-sync', listener)
      return () => ipcRenderer.removeListener('accounts:cli-sync', listener)
    },
    onCliSyncError: (callback) => {
      const listener = (_event: Electron.IpcRendererEvent, message: string): void =>
        callback(message)
      ipcRenderer.on('accounts:cli-sync-error', listener)
      return () => ipcRenderer.removeListener('accounts:cli-sync-error', listener)
    },
    rename: (email, name) => ipcRenderer.invoke('accounts:rename', email, name),
    remove: (email) => ipcRenderer.invoke('accounts:remove', email),
    login: (email, password, name, mode) =>
      ipcRenderer.invoke('accounts:login', email, password, name, mode),
    loginSaved: (email, mode) => ipcRenderer.invoke('accounts:login-saved', email, mode),
    checkCookie: (email) => ipcRenderer.invoke('accounts:cookie:check', email)
  },
  courses: {
    list: () => ipcRenderer.invoke('courses:list'),
    onCliSync: (callback) => {
      const listener = (
        _event: Electron.IpcRendererEvent,
        courses: Parameters<typeof callback>[0]
      ): void => callback(courses)
      ipcRenderer.on('courses:cli-sync', listener)
      return () => ipcRenderer.removeListener('courses:cli-sync', listener)
    },
    onCliSyncError: (callback) => {
      const listener = (_event: Electron.IpcRendererEvent, message: string): void =>
        callback(message)
      ipcRenderer.on('courses:cli-sync-error', listener)
      return () => ipcRenderer.removeListener('courses:cli-sync-error', listener)
    },
    add: (urls, category, alias) => ipcRenderer.invoke('courses:add', urls, category, alias),
    setCategory: (url, category) => ipcRenderer.invoke('courses:setCategory', url, category),
    remove: (url) => ipcRenderer.invoke('courses:remove', url),
    open: (urls, accountEmail, mode, label) =>
      ipcRenderer.invoke('courses:open', urls, accountEmail, mode, label)
  },
  reports: {
    fetch: (accountEmail, thresholdMinutes): Promise<CourseReportRow[]> =>
      ipcRenderer.invoke('reports:fetch', accountEmail, thresholdMinutes)
  },
  events: {
    onNetwork: (callback) => {
      const listener = (_event: Electron.IpcRendererEvent, data: NetworkEvent): void =>
        callback(data)
      ipcRenderer.on('network:event', listener)
      return () => ipcRenderer.removeListener('network:event', listener)
    },
    onSession: (callback) => {
      const listener = (
        _event: Electron.IpcRendererEvent,
        session: Parameters<Parameters<CoolApi['events']['onSession']>[0]>[0]
      ): void => callback(session)
      ipcRenderer.on('network:session', listener)
      return () => ipcRenderer.removeListener('network:session', listener)
    },
    onHistoryChanged: (callback) => {
      const listener = (): void => callback()
      ipcRenderer.on('network:history-changed', listener)
      return () => ipcRenderer.removeListener('network:history-changed', listener)
    },
    onCourseProgress: (callback) => {
      const listener = (_event: Electron.IpcRendererEvent, update: CourseProgressUpdate): void =>
        callback(update)
      ipcRenderer.on('courses:progress', listener)
      return () => ipcRenderer.removeListener('courses:progress', listener)
    },
    list: () => ipcRenderer.invoke('events:list'),
    remove: (sessionIds) => ipcRenderer.invoke('events:remove', sessionIds),
    export: (sessionId) => ipcRenderer.invoke('events:export', sessionId),
    openBody: (sessionId, bodyAttachmentId) =>
      ipcRenderer.invoke('events:open-body', sessionId, bodyAttachmentId),
    stop: (sessionId) => ipcRenderer.invoke('events:stop', sessionId)
  },
  settings: {
    get: () => ipcRenderer.invoke('settings:get'),
    save: (settings) => ipcRenderer.invoke('settings:save', settings),
    onCliColors: (callback) => {
      const listener = (
        _event: Electron.IpcRendererEvent,
        settings: Parameters<typeof callback>[0]
      ): void => callback(settings)
      ipcRenderer.on('settings:cli-colors', listener)
      return () => ipcRenderer.removeListener('settings:cli-colors', listener)
    },
    onCliColorsError: (callback) => {
      const listener = (_event: Electron.IpcRendererEvent, message: string): void =>
        callback(message)
      ipcRenderer.on('settings:cli-colors-error', listener)
      return () => ipcRenderer.removeListener('settings:cli-colors-error', listener)
    }
  },
  clipboard: {
    read: () => ipcRenderer.invoke('clipboard:read'),
    write: (text) => ipcRenderer.send('clipboard:write', text)
  },
  app: {
    version: process.env.npm_package_version ?? '0.1.0',
    openExternal: (url) => ipcRenderer.send('app:openExternal', url),
    minimize: () => ipcRenderer.send('window:minimize'),
    toggleMaximize: () => ipcRenderer.send('window:toggleMaximize'),
    close: () => ipcRenderer.send('window:close')
  }
}

contextBridge.exposeInMainWorld('cool', api)
