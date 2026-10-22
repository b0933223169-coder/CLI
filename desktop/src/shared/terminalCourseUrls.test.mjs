import assert from 'node:assert/strict'
import test from 'node:test'
import {
  parseTerminalCourseGroups,
  parseTerminalCourseUrls,
  serializeTerminalCourseGroups
} from './terminalCourseUrls.ts'

test('parses and deduplicates valid HTTP course URLs from CLI url files', () => {
  assert.deepEqual(
    parseTerminalCourseUrls(
      [
        '# Cool English 課程網址清單',
        'https://www.coolenglish.edu.tw/course/view.php?id=1',
        'not a url',
        'https://www.coolenglish.edu.tw/course/view.php?id=1',
        'ftp://example.com/course',
        'http://example.com/course'
      ].join('\n')
    ),
    ['https://www.coolenglish.edu.tw/course/view.php?id=1', 'http://example.com/course']
  )
})

test('round-trips named groups and writes unique URLs in the CLI urls.txt format', () => {
  assert.equal(
    serializeTerminalCourseGroups(
      [
        {
          name: '影片組',
          category: '電影',
          urls: ['https://example.com/course', 'https://example.com/course']
        },
        { name: '學習', urls: ['https://example.com/course'] }
      ],
      new Date('2026-10-20T08:00:00.000Z')
    ),
    [
      '# Cool English 課程網址清單',
      '# 最後更新時間: 2026-10-20 08:00:00',
      '# 每行一個網址，支援 cool -u 快速選取或依序瀏覽',
      '',
      '# group: %E5%BD%B1%E7%89%87%E7%B5%84',
      '# category: %E9%9B%BB%E5%BD%B1',
      'https://example.com/course',
      ''
    ].join('\n')
  )
  assert.deepEqual(
    parseTerminalCourseGroups(
      [
        '# group: %E5%BD%B1%E7%89%87%E7%B5%84',
        '# category: %E9%9B%BB%E5%BD%B1',
        'https://example.com/video',
        '# group: %E5%AD%B8%E7%BF%92',
        '# category: %E8%8B%B1%E6%96%87',
        'https://example.com/course'
      ].join('\n')
    ),
    [
      { name: '影片組', category: '電影', urls: ['https://example.com/video'] },
      { name: '學習', category: '英文', urls: ['https://example.com/course'] }
    ]
  )
})

test('legacy CLI group markers retain an undefined category for app-side migration', () => {
  assert.deepEqual(
    parseTerminalCourseGroups('# group: %E5%AD%B8%E7%BF%92\nhttps://example.com/course'),
    [{ name: '學習', urls: ['https://example.com/course'] }]
  )
})
