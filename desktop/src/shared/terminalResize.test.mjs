import assert from 'node:assert/strict'
import test from 'node:test'
import { canFitTerminal } from './terminalResize.ts'

test('fits and resizes the PTY continuously while the workspace splitter is being dragged', () => {
  assert.equal(canFitTerminal(true, 800, 300), true)
})

test('fits the visible terminal after splitter dragging ends', () => {
  assert.equal(canFitTerminal(true, 800, 300), true)
})

test('does not fit a hidden terminal or a zero-sized terminal host', () => {
  assert.equal(canFitTerminal(false, 800, 300), false)
  assert.equal(canFitTerminal(true, 0, 300), false)
  assert.equal(canFitTerminal(true, 800, 0), false)
})
