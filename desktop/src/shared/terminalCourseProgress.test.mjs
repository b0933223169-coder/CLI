import assert from 'node:assert/strict'
import test from 'node:test'
import { formatTerminalCourseStatusLine } from './terminalCourseProgress.ts'

test('formats course progress in the familiar CLI status-line layout', () => {
  const output = formatTerminalCourseStatusLine(
    1,
    '歡樂電影城: 特務 327：理髮店行動 Agent 327: Operation',
    'OK'
  )

  assert.match(
    output,
    /^\[1\] 歡樂電影城: 特務 327：理髮店行動 Agent 327: Operation \.+ \[ {2}OK {2}\]\r\n$/
  )
})

test('marks a course that failed to open as a warning', () => {
  assert.match(formatTerminalCourseStatusLine(2, '第二個課程', 'WARN'), /\[ WARN \]/)
})
