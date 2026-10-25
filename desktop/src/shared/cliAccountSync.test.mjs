import assert from 'node:assert/strict'
import test from 'node:test'
import { isCliAccountLoginNewer } from './cliAccountSync.ts'

test('syncs only accounts whose own login timestamp is newer than the saved account', () => {
  const previouslySavedLogin = '2026-10-21T10:00:00'

  assert.equal(
    isCliAccountLoginNewer('2026-10-22T08:00:00', Date.parse(previouslySavedLogin)),
    true
  )
  assert.equal(
    isCliAccountLoginNewer(previouslySavedLogin, Date.parse(previouslySavedLogin)),
    false
  )
  assert.equal(isCliAccountLoginNewer(undefined, Date.parse(previouslySavedLogin)), false)
  assert.equal(isCliAccountLoginNewer('not-a-date', Date.parse(previouslySavedLogin)), false)
})
