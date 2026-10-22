import assert from 'node:assert/strict'
import test from 'node:test'
import { parseTimeReportRows } from './timeReportParser.ts'

test('parses the Cool English time table and applies the requested threshold', () => {
  const html = `
    <table id="sort-table"><tbody>
      <tr><td>2026/10</td><td>7 小時 30 分</td><td>3 小時</td><td>2 小時</td></tr>
      <tr><td>2026/09</td><td>12 小時</td><td>6 小時</td><td>4 小時</td></tr>
    </tbody></table>`

  assert.deepEqual(parseTimeReportRows(html, 720), [
    {
      month: '2026/10',
      platformTime: '7 小時 30 分',
      videoTime: '3 小時',
      practiceTime: '2 小時',
      isBelowThreshold: true
    },
    {
      month: '2026/09',
      platformTime: '12 小時',
      videoTime: '6 小時',
      practiceTime: '4 小時',
      isBelowThreshold: false
    }
  ])
})

test('decodes HTML entities and returns no rows when the time table is absent', () => {
  assert.equal(
    parseTimeReportRows(
      '<table id="sort-table"><tr><td>2026/10</td><td>1&nbsp;小時</td><td>A &amp; B</td><td>0</td></tr></table>',
      120
    )[0].videoTime,
    'A & B'
  )
  assert.deepEqual(parseTimeReportRows('<html></html>', 720), [])
})
