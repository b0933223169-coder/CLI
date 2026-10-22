import test from 'node:test'
import assert from 'node:assert/strict'
import { canTransitionNetworkSession } from './networkSessionState.ts'

test('an active network session can end as completed, failed, or stopped', () => {
  assert.equal(canTransitionNetworkSession('active', 'completed'), true)
  assert.equal(canTransitionNetworkSession('active', 'failed'), true)
  assert.equal(canTransitionNetworkSession('active', 'stopped'), true)
})

test('a stopped or completed session cannot be overwritten by later work', () => {
  assert.equal(canTransitionNetworkSession('stopped', 'failed'), false)
  assert.equal(canTransitionNetworkSession('stopped', 'completed'), false)
  assert.equal(canTransitionNetworkSession('completed', 'failed'), false)
  assert.equal(canTransitionNetworkSession('failed', 'stopped'), false)
})
