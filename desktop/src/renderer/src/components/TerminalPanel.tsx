import { FitAddon } from '@xterm/addon-fit'
import { Terminal } from '@xterm/xterm'
import { Plus, TerminalSquare, X } from 'lucide-react'
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { terminalFontFamilyStack } from '../../../shared/fontSettings'
import {
  canFitTerminal,
  TERMINAL_LAYOUT_RESIZE_END_EVENT,
  TERMINAL_LAYOUT_RESIZE_START_EVENT
} from '../../../shared/terminalResize'
import type { FontFamily, TerminalProfile, TerminalSessionInfo } from '../../../shared/types'
import '@xterm/xterm/css/xterm.css'

interface TerminalInstance extends TerminalSessionInfo {
  terminal: Terminal
  fit: FitAddon
  element: HTMLDivElement
  ptyColumns: number
  ptyRows: number
}

interface TerminalPanelProps {
  terminalFontSize: number
  fontFamily: FontFamily
  terminalCursorColor: string
  terminalTextColor: string
  terminalBackgroundColor: string
  isVisible: boolean
}

export function TerminalPanel({
  terminalFontSize,
  fontFamily,
  terminalCursorColor,
  terminalTextColor,
  terminalBackgroundColor,
  isVisible
}: TerminalPanelProps): React.JSX.Element {
  const host = useRef<HTMLDivElement>(null)
  const instances = useRef(new Map<string, TerminalInstance>())
  const [profiles, setProfiles] = useState<TerminalProfile[]>([])
  const [profilesLoading, setProfilesLoading] = useState(true)
  const [tabs, setTabs] = useState<TerminalSessionInfo[]>([])
  const [activeId, setActiveId] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const [contextMenu, setContextMenu] = useState<{
    x: number
    y: number
    terminalId: string
  } | null>(null)
  const [error, setError] = useState('')
  const settings = useRef({
    terminalFontSize,
    fontFamily,
    terminalCursorColor,
    terminalTextColor,
    terminalBackgroundColor,
    isVisible
  })
  const activeIdRef = useRef(activeId)
  const fitFrame = useRef<number | null>(null)
  const resizeEndFrame = useRef<number | null>(null)
  const layoutResizing = useRef(false)
  const pendingInput = useRef(new Map<string, string[]>())

  useLayoutEffect(() => {
    settings.current = {
      terminalFontSize,
      fontFamily,
      terminalCursorColor,
      terminalTextColor,
      terminalBackgroundColor,
      isVisible
    }
    activeIdRef.current = activeId
  }, [
    terminalFontSize,
    fontFamily,
    terminalCursorColor,
    terminalTextColor,
    terminalBackgroundColor,
    isVisible,
    activeId
  ])

  const fitActive = useCallback(() => {
    const current = instances.current.get(activeIdRef.current)
    const bounds = host.current?.getBoundingClientRect()
    if (
      !current ||
      !bounds ||
      !canFitTerminal(settings.current.isVisible, bounds.width, bounds.height)
    ) {
      return
    }
    current.fit.fit()
    if (
      current.terminal.cols > 0 &&
      current.terminal.rows > 0 &&
      (current.ptyColumns !== current.terminal.cols || current.ptyRows !== current.terminal.rows)
    ) {
      current.ptyColumns = current.terminal.cols
      current.ptyRows = current.terminal.rows
      window.cool.terminal.resize(current.id, current.ptyColumns, current.ptyRows)
    }
  }, [])

  const scheduleFitActive = useCallback(() => {
    if (fitFrame.current !== null) cancelAnimationFrame(fitFrame.current)
    fitFrame.current = requestAnimationFrame(() => {
      fitFrame.current = null
      fitActive()
    })
  }, [fitActive])

  const createTerminal = useCallback(
    async (profile: TerminalProfile): Promise<void> => {
      if (!host.current) return
      setError('')
      try {
        const session = await window.cool.terminal.start(profile.id)
        const element = document.createElement('div')
        element.className = 'terminal-instance'
        element.style.display = 'none'
        host.current.append(element)

        const terminal = new Terminal({
          allowProposedApi: false,
          convertEol: false,
          cursorBlink: true,
          fontFamily: terminalFontFamilyStack(settings.current.fontFamily),
          letterSpacing: 0,
          fontSize: settings.current.terminalFontSize,
          lineHeight: 1.35,
          scrollback: 10_000,
          rightClickSelectsWord: true,
          theme: {
            background: settings.current.terminalBackgroundColor,
            foreground: settings.current.terminalTextColor,
            cursor: settings.current.terminalCursorColor,
            cursorAccent: settings.current.terminalBackgroundColor,
            selectionBackground: '#29445d',
            black: settings.current.terminalBackgroundColor,
            red: '#ef6b73',
            green: '#63d297',
            yellow: '#e7c873',
            blue: '#77a8f7',
            magenta: '#c792ea',
            cyan: '#66d9c3',
            white: settings.current.terminalTextColor,
            brightBlack: '#626c7b',
            brightRed: '#ff7a83',
            brightGreen: '#7ce2aa',
            brightYellow: '#f0d58b',
            brightBlue: '#8bb7ff',
            brightMagenta: '#d9a7ff',
            brightCyan: '#82e8d5',
            brightWhite: settings.current.terminalTextColor
          }
        })
        const fit = new FitAddon()
        terminal.loadAddon(fit)
        terminal.open(element)
        const instance: TerminalInstance = {
          ...session,
          terminal,
          fit,
          element,
          ptyColumns: 100,
          ptyRows: 28
        }
        instances.current.set(session.id, instance)
        terminal.onData((data) => {
          if (layoutResizing.current) {
            const queued = pendingInput.current.get(session.id) ?? []
            queued.push(data)
            pendingInput.current.set(session.id, queued)
          } else {
            window.cool.terminal.write(session.id, data)
          }
        })
        window.cool.terminal.ready(session.id)
        terminal.attachCustomKeyEventHandler((event) => {
          if (!(event.ctrlKey || event.metaKey)) return true
          const key = event.key.toLowerCase()
          if (key === 'c' && (event.shiftKey || terminal.hasSelection())) {
            const selection = terminal.getSelection()
            if (selection) window.cool.clipboard.write(selection)
            event.preventDefault()
            return false
          }
          if (key === 'v' && (event.shiftKey || !event.altKey)) {
            event.preventDefault()
            void window.cool.clipboard.read().then((text) => terminal.paste(text))
            return false
          }
          return true
        })
        setTabs((items) => [...items, session])
        setActiveId(session.id)
        scheduleFitActive()
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : String(caught))
      }
    },
    [scheduleFitActive]
  )

  useEffect(() => {
    let active = true
    const currentInstances = instances.current
    const stopData = window.cool.terminal.onData((terminalId, data) => {
      const instance = instances.current.get(terminalId)
      if (instance) instance.terminal.write(data)
    })
    const stopExit = window.cool.terminal.onExit((terminalId, code) => {
      instances.current.get(terminalId)?.terminal.writeln(`\r\n[終端已結束：${code}]`)
    })
    const resizeObserver = new ResizeObserver(scheduleFitActive)
    if (host.current) resizeObserver.observe(host.current)
    const startLayoutResize = (): void => {
      if (resizeEndFrame.current !== null) {
        cancelAnimationFrame(resizeEndFrame.current)
        resizeEndFrame.current = null
      }
      layoutResizing.current = true
    }
    const endLayoutResize = (): void => {
      if (resizeEndFrame.current !== null) cancelAnimationFrame(resizeEndFrame.current)
      resizeEndFrame.current = requestAnimationFrame(() => {
        resizeEndFrame.current = null
        layoutResizing.current = false
        fitActive()
        for (const [terminalId, chunks] of pendingInput.current) {
          for (const data of chunks) window.cool.terminal.write(terminalId, data)
        }
        pendingInput.current.clear()
        scheduleFitActive()
      })
    }
    window.addEventListener(TERMINAL_LAYOUT_RESIZE_START_EVENT, startLayoutResize)
    window.addEventListener(TERMINAL_LAYOUT_RESIZE_END_EVENT, endLayoutResize)
    window.addEventListener('focus', scheduleFitActive)
    document.addEventListener('visibilitychange', scheduleFitActive)

    void window.cool.terminal
      .profiles()
      .then((available) => {
        if (!active) return
        setProfiles(available)
        if (!available.length)
          setError('找不到可用的系統終端。請確認 PowerShell、命令提示字元或 shell 已安裝。')
        setProfilesLoading(false)
      })
      .catch((caught: unknown) => {
        if (!active) return
        setError(caught instanceof Error ? caught.message : String(caught))
        setProfilesLoading(false)
      })

    return () => {
      active = false
      resizeObserver.disconnect()
      window.removeEventListener(TERMINAL_LAYOUT_RESIZE_START_EVENT, startLayoutResize)
      window.removeEventListener(TERMINAL_LAYOUT_RESIZE_END_EVENT, endLayoutResize)
      window.removeEventListener('focus', scheduleFitActive)
      document.removeEventListener('visibilitychange', scheduleFitActive)
      if (fitFrame.current !== null) cancelAnimationFrame(fitFrame.current)
      if (resizeEndFrame.current !== null) cancelAnimationFrame(resizeEndFrame.current)
      stopData()
      stopExit()
      for (const instance of currentInstances.values()) {
        window.cool.terminal.stop(instance.id)
        instance.terminal.dispose()
        instance.element.remove()
      }
      currentInstances.clear()
    }
  }, [createTerminal, fitActive, scheduleFitActive])

  useEffect(() => {
    for (const instance of instances.current.values()) {
      instance.terminal.options.fontSize = terminalFontSize
      instance.terminal.options.fontFamily = terminalFontFamilyStack(fontFamily)
      instance.terminal.options.letterSpacing = 0
      instance.terminal.options.theme = {
        ...instance.terminal.options.theme,
        background: terminalBackgroundColor,
        foreground: terminalTextColor,
        cursor: terminalCursorColor,
        cursorAccent: terminalBackgroundColor,
        black: terminalBackgroundColor,
        white: terminalTextColor,
        brightWhite: terminalTextColor
      }
    }
    scheduleFitActive()
  }, [
    terminalFontSize,
    fontFamily,
    terminalCursorColor,
    terminalTextColor,
    terminalBackgroundColor,
    scheduleFitActive
  ])

  useEffect(() => {
    for (const instance of instances.current.values()) {
      instance.element.style.display = instance.id === activeId ? 'block' : 'none'
    }
    scheduleFitActive()
  }, [activeId, scheduleFitActive])

  useEffect(() => {
    if (isVisible) scheduleFitActive()
  }, [isVisible, scheduleFitActive])

  const closeTab = (session: TerminalSessionInfo): void => {
    window.cool.terminal.stop(session.id)
    instances.current.get(session.id)?.terminal.dispose()
    instances.current.get(session.id)?.element.remove()
    instances.current.delete(session.id)
    setTabs((items) => items.filter((item) => item.id !== session.id))
    if (activeId === session.id) {
      const remaining = tabs.filter((item) => item.id !== session.id)
      setActiveId(remaining.at(-1)?.id ?? '')
    }
  }

  const onContextMenu = (event: React.MouseEvent<HTMLDivElement>): void => {
    event.preventDefault()
    if (!activeId || !host.current) return
    const bounds = host.current.getBoundingClientRect()
    setContextMenu({
      x: Math.min(event.clientX - bounds.left, Math.max(0, bounds.width - 180)),
      y: Math.min(event.clientY - bounds.top, Math.max(0, bounds.height - 120)),
      terminalId: activeId
    })
  }

  const copy = (): void => {
    const selected = instances.current
      .get(contextMenu?.terminalId ?? activeId)
      ?.terminal.getSelection()
    if (selected) window.cool.clipboard.write(selected)
    setContextMenu(null)
  }

  const paste = (): void => {
    const target = instances.current.get(contextMenu?.terminalId ?? activeId)?.terminal
    void window.cool.clipboard.read().then((text) => target?.paste(text))
    setContextMenu(null)
  }

  const selectAll = (): void => {
    instances.current.get(contextMenu?.terminalId ?? activeId)?.terminal.selectAll()
    setContextMenu(null)
  }

  return (
    <div className="terminal-panel">
      <div className="terminal-toolbar">
        <div className="terminal-tabs">
          {tabs.map((tab) => (
            <div
              className={`terminal-tab ${activeId === tab.id ? 'active' : ''}`}
              key={tab.id}
              role="button"
              tabIndex={0}
              onClick={() => setActiveId(tab.id)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') setActiveId(tab.id)
              }}
              title={tab.label}
            >
              <TerminalSquare size={13} />
              {tab.label}
              <button
                className="terminal-tab-close"
                title="關閉終端"
                onClick={(event) => {
                  event.stopPropagation()
                  closeTab(tab)
                }}
              >
                <X size={12} />
              </button>
            </div>
          ))}
          <div className="terminal-new-wrapper">
            <button
              className="mini-icon-button"
              title="新增終端（啟動 cool.py）"
              aria-label="新增終端"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((open) => !open)}
            >
              <Plus size={15} />
            </button>
            {menuOpen && (
              <div className="terminal-profile-menu">
                <span className="terminal-profile-menu-label">選擇系統終端 · 啟動 cool.py</span>
                {profilesLoading ? (
                  <span className="terminal-profile-menu-empty">正在載入可用終端…</span>
                ) : (
                  profiles.map((profile) => (
                    <button
                      key={profile.id}
                      onClick={() => {
                        setMenuOpen(false)
                        void createTerminal(profile)
                      }}
                    >
                      <TerminalSquare size={14} />
                      {profile.label}
                    </button>
                  ))
                )}
                {!profilesLoading && !profiles.length && (
                  <span className="terminal-profile-menu-empty">沒有可用的系統終端</span>
                )}
              </div>
            )}
          </div>
          {tabs.length > 0 && (
            <span className="terminal-tab-label">
              輸入 /exit 關閉工作臺 · Ctrl+Shift+C/V 複製/貼上
            </span>
          )}
        </div>
        <div className="terminal-toolbar-actions">
          {error && <span className="terminal-error">{error}</span>}
        </div>
      </div>
      <div className="terminal-screen" ref={host} onContextMenu={onContextMenu}>
        {contextMenu && (
          <div
            className="terminal-context-menu"
            style={{ left: contextMenu.x, top: contextMenu.y }}
            onMouseLeave={() => setContextMenu(null)}
          >
            <button onClick={copy}>複製選取內容</button>
            <button onClick={paste}>貼上</button>
            <button onClick={selectAll}>全選</button>
          </div>
        )}
      </div>
    </div>
  )
}
