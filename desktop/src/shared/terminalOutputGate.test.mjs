import assert from 'node:assert/strict'
import test from 'node:test'
import { TerminalOutputGate } from './terminalOutputGate.ts'

test('buffers initial PTY output until the renderer terminal is ready', () => {
  const received = []
  const gate = new TerminalOutputGate((data) => received.push(data))

  gate.write('shell banner')
  gate.write('cool> ')
  assert.deepEqual(received, [])

  gate.markReady()
  gate.write('next prompt')
  gate.markReady()

  assert.deepEqual(received, ['shell banner', 'cool> ', 'next prompt'])
})
