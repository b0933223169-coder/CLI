function displayWidth(value: string): number {
  return Array.from(value).reduce((width, character) => {
    const codePoint = character.codePointAt(0) ?? 0
    return width + (codePoint >= 0x1100 ? 2 : 1)
  }, 0)
}

export function formatTerminalCourseStatusLine(
  index: number,
  label: string,
  status: 'OK' | 'WARN'
): string {
  const statusLabel = status === 'OK' ? ' OK ' : 'WARN'
  const lineLabel = `[${index}] ${label}`
  const dots = '.'.repeat(Math.max(2, 52 - displayWidth(lineLabel)))
  return `${lineLabel} ${dots} [ ${statusLabel} ]\r\n`
}
