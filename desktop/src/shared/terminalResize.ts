export const TERMINAL_LAYOUT_RESIZE_START_EVENT = 'cool:terminal-layout-resize-start'
export const TERMINAL_LAYOUT_RESIZE_END_EVENT = 'cool:terminal-layout-resize-end'

export function canFitTerminal(isVisible: boolean, width: number, height: number): boolean {
  return isVisible && width > 0 && height > 0
}
