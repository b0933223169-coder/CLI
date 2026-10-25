import assert from 'node:assert/strict'
import test from 'node:test'
import {
  cliColorMappings,
  cliColorPreview,
  cliColorSwatch,
  cliIndexedBackgroundColors,
  cliIndexedForegroundColors,
  cliReportColorFields,
  defaultCliReportColors,
  isCliColorValue,
  normalizeCliColor
} from './cliReportColors.ts'

test('defines the seven CLI report colors and their shared settings mappings', () => {
  assert.deepEqual(
    cliReportColorFields.map(({ key }) => key),
    ['title', 'title_text', 'header', 'cur', 'low', 'url', 'sep']
  )
  assert.deepEqual(
    Object.fromEntries(cliReportColorFields.map(({ key, setting }) => [key, setting])),
    Object.fromEntries(cliColorMappings.slice(3))
  )
  assert.deepEqual(defaultCliReportColors, {
    cliReportTitleColor: 'MAGENTA',
    cliReportTitleTextColor: 'WHITE',
    cliReportHeaderColor: 'CYAN',
    cliReportCurrentColor: 'REVERSE',
    cliReportBelowColor: 'RED_BG_WHITE',
    cliReportUrlColor: 'DIM',
    cliReportSeparatorColor: 'DIM'
  })
})

test('accepts CLI named, indexed, and custom hex colors and normalizes hex values', () => {
  assert.equal(cliIndexedForegroundColors.length, 256)
  assert.equal(cliIndexedBackgroundColors.length, 256)
  assert.equal(cliIndexedForegroundColors[255], 'COLOR_255')
  assert.equal(cliIndexedBackgroundColors[0], 'BG_000')
  assert.equal(isCliColorValue('REVERSE'), true)
  assert.equal(isCliColorValue('RED_BG_WHITE'), true)
  assert.equal(isCliColorValue('COLOR_255'), true)
  assert.equal(isCliColorValue('BG_000'), true)
  assert.equal(isCliColorValue('#aBc'), true)
  assert.equal(isCliColorValue('COLOR_256'), false)
  assert.equal(isCliColorValue('not-a-color'), false)
  assert.equal(normalizeCliColor(' #aBc '), '#aabbcc')
})

test('previews special report styles and the full xterm 256-color range', () => {
  assert.deepEqual(cliColorPreview('REVERSE'), {
    color: '#101f20',
    backgroundColor: '#d8fff4'
  })
  assert.deepEqual(cliColorPreview('REVERSE', '#f0f0f0', '#101010'), {
    color: '#101010',
    backgroundColor: '#f0f0f0'
  })
  assert.deepEqual(cliColorPreview('RED_BG_WHITE'), {
    color: '#ffffff',
    backgroundColor: '#800000'
  })
  assert.equal(cliColorPreview('COLOR_016').color, '#000000')
  assert.equal(cliColorPreview('BG_255').backgroundColor, '#eeeeee')
  assert.equal(cliColorPreview('#ABCDEF').color, '#ABCDEF')
})

test('shows each setting as a full-row color swatch with readable contrasting text', () => {
  assert.deepEqual(cliColorSwatch('COLOR_211'), {
    color: '#ffffff',
    backgroundColor: '#ff87af'
  })
  assert.deepEqual(cliColorSwatch('MAGENTA'), {
    color: '#ffffff',
    backgroundColor: '#ff00ff'
  })
  assert.deepEqual(cliColorSwatch('RED_BG_WHITE'), {
    color: '#ffffff',
    backgroundColor: '#800000'
  })
  assert.deepEqual(cliColorSwatch('REVERSE'), {
    color: '#101f20',
    backgroundColor: '#d8fff4'
  })
  assert.deepEqual(cliColorSwatch('#eeeeee'), {
    color: '#15181e',
    backgroundColor: '#eeeeee'
  })
})
