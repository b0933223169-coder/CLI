import assert from 'node:assert/strict'
import test from 'node:test'
import {
  isGoogleAccountsUrl,
  isGoogleOAuthProviderHref,
  isGoogleRecaptchaUrl
} from './googleLogin.ts'

test('recognizes only the configured Google OAuth provider used by the CLI', () => {
  assert.equal(isGoogleOAuthProviderHref('/auth/oauth2/login.php?id=2'), true)
  assert.equal(isGoogleOAuthProviderHref('/auth/oauth2/login.php?sesskey=x&id=2'), true)
  assert.equal(isGoogleOAuthProviderHref('/auth/oauth2/login.php?id=1'), false)
  assert.equal(isGoogleOAuthProviderHref('/auth/oauth2/login.php'), false)
  assert.equal(isGoogleOAuthProviderHref('https://facebook.com/login'), false)
  assert.equal(
    isGoogleOAuthProviderHref('https://attacker.example/auth/oauth2/login.php?id=2'),
    false
  )
})

test('recognizes Google reCAPTCHA frames without treating unrelated Google URLs as challenges', () => {
  assert.equal(
    isGoogleRecaptchaUrl('https://www.google.com/recaptcha/api2/anchor?size=invisible&sa=submit'),
    true
  )
  assert.equal(isGoogleRecaptchaUrl('https://www.recaptcha.net/recaptcha/api2/anchor'), true)
  assert.equal(isGoogleRecaptchaUrl('https://accounts.google.com/'), false)
  assert.equal(isGoogleRecaptchaUrl('https://google.com.attacker.example/recaptcha/'), false)
  assert.equal(isGoogleRecaptchaUrl('not a url'), false)
})

test('recognizes regional Google account hosts during OAuth redirects', () => {
  assert.equal(isGoogleAccountsUrl('https://accounts.google.com/signin'), true)
  assert.equal(isGoogleAccountsUrl('https://accounts.google.com.tw/accounts/SetSID'), true)
  assert.equal(isGoogleAccountsUrl('https://mail.google.com/'), false)
  assert.equal(isGoogleAccountsUrl('https://accounts.google.com.attacker.example/'), false)
})
