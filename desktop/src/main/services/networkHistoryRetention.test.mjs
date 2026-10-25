import assert from 'node:assert/strict'
import test from 'node:test'
import { isNetworkSessionExpired } from './networkHistoryRetention.ts'

test('expires finished sessions relative to their end time', () => {
  const now = Date.parse('2026-10-21T12:00:00.000Z')
  const session = {
    status: 'completed',
    startedAt: '2026-10-21T10:00:00.000Z',
    endedAt: '2026-10-21T11:00:00.000Z'
  }

  assert.equal(isNetworkSessionExpired(session, 59, now), true)
  assert.equal(isNetworkSessionExpired(session, 60, now), true)
  assert.equal(isNetworkSessionExpired(session, 61, now), false)
})

test('does not expire active sessions or sessions with invalid timestamps', () => {
  assert.equal(
    isNetworkSessionExpired(
      { status: 'active', startedAt: '2020-01-01T00:00:00.000Z' },
      1,
      Date.now()
    ),
    false
  )
  assert.equal(
    isNetworkSessionExpired({ status: 'failed', startedAt: 'invalid' }, 1, Date.now()),
    false
  )
})
