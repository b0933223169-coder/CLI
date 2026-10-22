import assert from 'node:assert/strict'
import test from 'node:test'
import { completeCoolEnglishLogin } from './coolLoginCompletion.ts'
import { coolEnglishCookies, hasUsableMoodleSession } from './coolSession.ts'

const validCookie = {
  name: 'MoodleSession',
  value: 'session-value',
  domain: '.coolenglish.edu.tw',
  expires: -1,
  path: '/',
  secure: true,
  httpOnly: true
}

test('persists a verified target-site session before closing its browser', async () => {
  const calls = []
  const result = await completeCoolEnglishLogin({
    cookies: [
      validCookie,
      { ...validCookie, name: 'foreign', domain: '.attacker.coolenglish.edu.tw' }
    ],
    filterCookies: coolEnglishCookies,
    hasUsableSession: hasUsableMoodleSession,
    validate: async () => {
      calls.push('validate')
      return true
    },
    persist: async (cookies) => {
      calls.push('persist')
      assert.deepEqual(
        cookies.map(({ name }) => name),
        ['MoodleSession']
      )
    },
    markCompleted: async () => calls.push('complete'),
    closeBrowser: async () => calls.push('close')
  })

  assert.deepEqual(
    result.map(({ name }) => name),
    ['MoodleSession']
  )
  assert.deepEqual(calls, ['validate', 'persist', 'complete', 'close'])
})

test('does not persist or close when the cookie is absent or unverified', async () => {
  for (const [cookies, validate, expectedError] of [
    [[], async () => true, /MoodleSession/],
    [[{ ...validCookie, value: '' }], async () => true, /MoodleSession/],
    [[validCookie], async () => false, /尚未確認/]
  ]) {
    const calls = []
    await assert.rejects(
      completeCoolEnglishLogin({
        cookies,
        filterCookies: coolEnglishCookies,
        hasUsableSession: hasUsableMoodleSession,
        validate,
        persist: async () => calls.push('persist'),
        markCompleted: async () => calls.push('complete'),
        closeBrowser: async () => calls.push('close')
      }),
      expectedError
    )
    assert.deepEqual(calls, [])
  }
})

test('does not mark success or close if encrypted persistence fails', async () => {
  const calls = []
  await assert.rejects(
    completeCoolEnglishLogin({
      cookies: [validCookie],
      filterCookies: coolEnglishCookies,
      hasUsableSession: hasUsableMoodleSession,
      validate: async () => true,
      persist: async () => {
        calls.push('persist')
        throw new Error('disk failure')
      },
      markCompleted: async () => calls.push('complete'),
      closeBrowser: async () => calls.push('close')
    }),
    /disk failure/
  )
  assert.deepEqual(calls, ['persist'])
})
