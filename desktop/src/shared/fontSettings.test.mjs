import assert from 'node:assert/strict'
import test from 'node:test'
import { fontFamilyStack, normalizeFontFamily, terminalFontFamilyStack } from './fontSettings.ts'

test('normalizes legacy and invalid saved font families to the system default', () => {
  assert.equal(normalizeFontFamily(undefined), 'system')
  assert.equal(normalizeFontFamily('unknown'), 'system')
})

test('preserves each supported font choice and returns a matching stack', () => {
  assert.equal(fontFamilyStack(normalizeFontFamily('system')).startsWith('Inter,'), true)
  assert.equal(fontFamilyStack(normalizeFontFamily('segoe')).startsWith('"Segoe UI"'), true)
  assert.equal(fontFamilyStack(normalizeFontFamily('arial')).startsWith('Arial,'), true)
  assert.equal(fontFamilyStack(normalizeFontFamily('consolas')).startsWith('Consolas,'), true)
})

test('terminal font stacks always use fixed-width fonts', () => {
  assert.match(terminalFontFamilyStack('system'), /Cascadia Mono/)
  assert.match(terminalFontFamilyStack('segoe'), /Cascadia Mono/)
  assert.match(terminalFontFamilyStack('arial'), /Cascadia Mono/)
  assert.match(terminalFontFamilyStack('consolas'), /^Consolas,/)
  for (const font of ['system', 'segoe', 'arial', 'consolas']) {
    assert.match(terminalFontFamilyStack(font), /monospace/)
    assert.doesNotMatch(terminalFontFamilyStack(font), /Segoe UI|Arial|Inter/)
  }
})
