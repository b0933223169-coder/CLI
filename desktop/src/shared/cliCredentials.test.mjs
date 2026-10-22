import assert from 'node:assert/strict'
import test from 'node:test'
import { decryptCliPassword } from './cliCredentials.ts'

test('decrypts the existing terminal password format for desktop re-encryption', () => {
  assert.equal(decryptCliPassword('xkJXGNjt82fNFeGqla3Y', 11, ['COOL-TEST-1234']), 'Passw0rd-測試')
})

test('rejects a wrong machine id, password length, and malformed ciphertext', () => {
  assert.throws(
    () => decryptCliPassword('xkJXGNjt82fNFeGqla3Y', 11, ['wrong-machine']),
    /無法解密終端帳號密碼/
  )
  assert.throws(
    () => decryptCliPassword('xkJXGNjt82fNFeGqla3Y', 10, ['COOL-TEST-1234']),
    /無法解密終端帳號密碼/
  )
  assert.throws(() => decryptCliPassword('not-base64!', 11, ['COOL-TEST-1234']), /格式不正確/)
})
