import assert from 'node:assert/strict'
import test from 'node:test'
import { normalizeSettingsCategoryOrder, settingsCategoryIds } from './settingsCategories.ts'

test('keeps a valid category order and appends categories missing from older settings', () => {
  const result = normalizeSettingsCategoryOrder(['privacy', 'appearance'])
  assert.deepEqual(result.slice(0, 2), ['privacy', 'appearance'])
  assert.equal(result.length, settingsCategoryIds.length)
  assert.equal(new Set(result).size, settingsCategoryIds.length)
})

test('drops invalid and duplicate category ids without losing default categories', () => {
  const result = normalizeSettingsCategoryOrder(['terminal', 'terminal', 'unknown'])
  assert.equal(result[0], 'terminal')
  assert.equal(result.length, settingsCategoryIds.length)
  assert.equal(new Set(result).size, settingsCategoryIds.length)
})
