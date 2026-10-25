import assert from 'node:assert/strict'
import test from 'node:test'
import { colorThemePresets, getColorThemePreset, isColorThemePresetId } from './colorThemes.ts'

test('provides 24 uniquely identified built-in color themes', () => {
  assert.equal(colorThemePresets.length, 24)
  assert.equal(new Set(colorThemePresets.map((preset) => preset.id)).size, 24)
  assert.equal(isColorThemePresetId('ember'), true)
  assert.equal(isColorThemePresetId('not-a-preset'), false)
  assert.equal(getColorThemePreset('neon')?.name, '霓虹街景')
})

test('all built-in theme interface text colors remain readable', () => {
  for (const preset of colorThemePresets) {
    for (const background of [preset.interfaceBackgroundColor, preset.interfaceSurfaceColor]) {
      const luminances = [preset.textColor, background].map((color) => {
        const channels = color.match(/[0-9a-f]{2}/gi) ?? []
        return channels.reduce((total, channel, index) => {
          const value = parseInt(channel, 16) / 255
          const linear = value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
          return total + linear * [0.2126, 0.7152, 0.0722][index]
        }, 0)
      })
      const [textLuminance, backgroundLuminance] = luminances
      const ratio =
        (Math.max(textLuminance, backgroundLuminance) + 0.05) /
        (Math.min(textLuminance, backgroundLuminance) + 0.05)
      assert.ok(
        ratio >= 4.5,
        `${preset.name} interface text does not meet 4.5:1 contrast on ${background}`
      )
    }
  }
})

test('built-in themes have distinct colored interface backgrounds and surfaces', () => {
  assert.equal(new Set(colorThemePresets.map((preset) => preset.interfaceBackgroundColor)).size, 24)
  assert.equal(new Set(colorThemePresets.map((preset) => preset.interfaceSurfaceColor)).size, 24)
  assert.ok(
    new Set(
      colorThemePresets
        .filter((preset) => preset.theme === 'light')
        .map((preset) => preset.interfaceBackgroundColor)
    ).size > 1,
    'light themes should use distinct colored backgrounds rather than white variants'
  )
})

test('dark themes clearly separate the app background from its panels', () => {
  for (const preset of colorThemePresets.filter((theme) => theme.theme === 'dark')) {
    const background = preset.interfaceBackgroundColor.match(/[0-9a-f]{2}/gi) ?? []
    const surface = preset.interfaceSurfaceColor.match(/[0-9a-f]{2}/gi) ?? []
    const distance = Math.sqrt(
      background.reduce((total, channel, index) => {
        const difference = parseInt(channel, 16) - parseInt(surface[index], 16)
        return total + difference ** 2
      }, 0)
    )
    assert.ok(distance >= 40, `${preset.name} dark theme panels are not distinct enough`)
  }
})

test('built-in palettes use distinct accents and readable terminal text', () => {
  assert.equal(new Set(colorThemePresets.map((preset) => preset.accentColor)).size, 24)

  for (const preset of colorThemePresets) {
    const luminances = [preset.terminalTextColor, preset.terminalBackgroundColor].map((color) => {
      const channels = color.match(/[0-9a-f]{2}/gi) ?? []
      return channels.reduce((total, channel, index) => {
        const value = parseInt(channel, 16) / 255
        const linear = value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
        return total + linear * [0.2126, 0.7152, 0.0722][index]
      }, 0)
    })
    const [textLuminance, backgroundLuminance] = luminances
    const ratio =
      (Math.max(textLuminance, backgroundLuminance) + 0.05) /
      (Math.min(textLuminance, backgroundLuminance) + 0.05)
    assert.ok(ratio >= 4.5, `${preset.name} terminal text does not meet 4.5:1 contrast`)
  }
})
