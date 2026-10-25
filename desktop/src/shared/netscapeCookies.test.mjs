import assert from 'node:assert/strict'
import test from 'node:test'
import { parseNetscapeCookies } from './netscapeCookies.ts'

test('parses Netscape cookies, including HttpOnly and tab-separated values', () => {
  const cookies = parseNetscapeCookies(
    [
      '# Netscape HTTP Cookie File',
      '.coolenglish.edu.tw\tTRUE\t/\tTRUE\t0\tMoodleSession\tsecret\ttail',
      '#HttpOnly_.coolenglish.edu.tw\tTRUE\t/\tTRUE\t1790000000\tSecureSession\tprivate',
      ''
    ].join('\n')
  )

  assert.deepEqual(cookies, [
    {
      name: 'MoodleSession',
      value: 'secret\ttail',
      domain: '.coolenglish.edu.tw',
      path: '/',
      secure: true,
      httpOnly: false,
      expires: 0
    },
    {
      name: 'SecureSession',
      value: 'private',
      domain: '.coolenglish.edu.tw',
      path: '/',
      secure: true,
      httpOnly: true,
      expires: 1790000000
    }
  ])
})

test('ignores comments and malformed Netscape cookie entries', () => {
  assert.deepEqual(
    parseNetscapeCookies('# comment\n.invalid\nhost\tTRUE\t/\tTRUE\tbad\tname\tvalue\n'),
    []
  )
})
