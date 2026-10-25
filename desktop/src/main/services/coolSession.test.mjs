import assert from 'node:assert/strict'
import test from 'node:test'
import {
  classifyCoolEnglishTimeReport,
  coolEnglishCookies,
  hasUsableMoodleSession,
  isAuthenticatedCoolEnglishDashboard,
  isCoolEnglishPageUrl
} from './coolSession.ts'

const now = Date.parse('2026-10-11T10:00:00Z')

test('recognizes both Cool English hostnames and rejects unrelated or insecure URLs', () => {
  assert.equal(isCoolEnglishPageUrl('https://www.coolenglish.edu.tw/login/index.php'), true)
  assert.equal(isCoolEnglishPageUrl('https://coolenglish.edu.tw/my/'), true)
  assert.equal(isCoolEnglishPageUrl('http://www.coolenglish.edu.tw/'), false)
  assert.equal(isCoolEnglishPageUrl('https://attacker.coolenglish.edu.tw/'), false)
  assert.equal(isCoolEnglishPageUrl('https://coolenglish.edu.tw.attacker.example/'), false)
})

test('accepts an unexpired Cool English MoodleSession cookie', () => {
  assert.equal(
    hasUsableMoodleSession(
      [
        {
          name: 'MoodleSession',
          value: 'opaque-session-value',
          domain: '.coolenglish.edu.tw',
          expires: now / 1000 + 60
        }
      ],
      now
    ),
    true
  )
})

test('rejects absent, empty, expired, and unrelated-domain MoodleSession cookies', () => {
  const invalidCookies = [
    [],
    [{ name: 'MoodleSession', value: '', domain: 'www.coolenglish.edu.tw', expires: -1 }],
    [
      {
        name: 'MoodleSession',
        value: 'opaque-session-value',
        domain: 'www.coolenglish.edu.tw',
        expires: now / 1000
      }
    ],
    [
      {
        name: 'MoodleSession',
        value: 'opaque-session-value',
        domain: '.edu.tw',
        expires: -1
      }
    ]
  ]

  for (const cookies of invalidCookies) {
    assert.equal(hasUsableMoodleSession(cookies, now), false)
  }
})

test('accepts a Cool English dashboard response with a real Moodle user id', () => {
  assert.equal(
    isAuthenticatedCoolEnglishDashboard(
      'https://www.coolenglish.edu.tw/my/',
      200,
      '<script>M.cfg = {"userId":42}</script>'
    ),
    true
  )
  assert.equal(
    isAuthenticatedCoolEnglishDashboard(
      'https://coolenglish.edu.tw/my/',
      200,
      '<script>M.cfg = {"userId":42}</script>'
    ),
    true
  )
})

test('accepts an authenticated Cool English home redirect using CLI login markers', () => {
  assert.equal(
    isAuthenticatedCoolEnglishDashboard(
      'https://www.coolenglish.edu.tw/',
      200,
      '<a href="/login/logout.php">登出</a>'
    ),
    true
  )
  assert.equal(
    isAuthenticatedCoolEnglishDashboard(
      'https://www.coolenglish.edu.tw/user/profile.php',
      200,
      '<h1>個人檔案</h1>'
    ),
    true
  )
  assert.equal(
    isAuthenticatedCoolEnglishDashboard(
      'https://www.coolenglish.edu.tw/',
      200,
      '<a href="/login/logout.php">登出</a><form id="login"><input type="password"></form>'
    ),
    true
  )
})

test('rejects an incomplete profile-verification form after OAuth redirect', () => {
  assert.equal(
    isAuthenticatedCoolEnglishDashboard(
      'https://www.coolenglish.edu.tw/user/profile.php',
      200,
      '<h1>個人檔案</h1><form><input name="firstname"><input name="lastname"></form>'
    ),
    false
  )
})

test('extracts only exact Cool English cookie domains, including Moodle session cookies', () => {
  const cookies = coolEnglishCookies([
    { name: 'MoodleSession', value: 'session', domain: '.coolenglish.edu.tw', expires: -1 },
    { name: 'other', value: 'v', domain: 'www.coolenglish.edu.tw', expires: -1 },
    {
      name: 'MoodleSession',
      value: 'attacker',
      domain: '.attacker.coolenglish.edu.tw',
      expires: -1
    }
  ])
  assert.deepEqual(
    cookies.map(({ name, domain }) => [name, domain]),
    [
      ['MoodleSession', '.coolenglish.edu.tw'],
      ['other', 'www.coolenglish.edu.tw']
    ]
  )
  assert.equal(hasUsableMoodleSession(cookies, now), true)
})

test('rejects login redirects, guest pages, and login forms as authenticated sessions', () => {
  assert.equal(
    isAuthenticatedCoolEnglishDashboard(
      'https://www.coolenglish.edu.tw/login/index.php',
      200,
      '<script>M.cfg = {"userId":0}</script>'
    ),
    false
  )
  assert.equal(
    isAuthenticatedCoolEnglishDashboard(
      'https://www.coolenglish.edu.tw/my/',
      200,
      '<script>M.cfg = {"userId":1}</script>'
    ),
    false
  )
  assert.equal(
    isAuthenticatedCoolEnglishDashboard(
      'https://www.coolenglish.edu.tw/user/edit.php',
      200,
      '<script>M.cfg = {"userId":42}</script>'
    ),
    false
  )
  assert.equal(
    isAuthenticatedCoolEnglishDashboard(
      'https://www.coolenglish.edu.tw/my/',
      200,
      '<script>M.cfg = {"userId":42}</script><input type="password">'
    ),
    false
  )
  assert.equal(
    isAuthenticatedCoolEnglishDashboard(
      'https://attacker.example/my/',
      200,
      '<script>M.cfg = {"userId":42}</script>'
    ),
    false
  )
})

test('classifies cookie validity from the real learning-time report response', () => {
  const report = `
    <table id="sort-table"><tbody><tr>
      <td>2026/10</td><td>2 小時</td><td>1 小時</td><td>1 小時</td>
    </tr></tbody></table>
  `
  assert.equal(
    classifyCoolEnglishTimeReport(
      'https://www.coolenglish.edu.tw/time/time_view_detail_by_people.php?id=42',
      200,
      report
    ),
    'valid'
  )
  assert.equal(
    classifyCoolEnglishTimeReport(
      'https://www.coolenglish.edu.tw/login/index.php',
      200,
      '<form id="login"><input name="username"></form>'
    ),
    'expired'
  )
  assert.equal(
    classifyCoolEnglishTimeReport(
      'https://www.coolenglish.edu.tw/time/time_view_detail_by_people.php?id=42',
      200,
      '<h1>Temporary service message</h1>'
    ),
    'unknown'
  )
  assert.equal(
    classifyCoolEnglishTimeReport(
      'https://www.coolenglish.edu.tw/time/time_view_detail_by_people.php?id=42',
      503,
      '<h1>Service unavailable</h1>'
    ),
    'unknown'
  )
})
