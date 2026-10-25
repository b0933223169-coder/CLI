import assert from 'node:assert/strict'
import test from 'node:test'
import {
  getRemovedTerminalCourseUrls,
  mergeTerminalCourseMetadata,
  normalizeCourseAlias,
  reconcileTerminalCourses
} from './terminalCourseUrls.ts'

test('moves the default uncategorized alias to the actual category', () => {
  assert.equal(normalizeCourseAlias('tests', '未分類'), 'tests')
  assert.equal(normalizeCourseAlias('未分類', '未分類'), '未分類')
  assert.equal(normalizeCourseAlias('tests', 'chapter one'), 'chapter one')
})

test('does not let a legacy uncategorized CLI entry erase existing desktop metadata', () => {
  assert.deepEqual(
    mergeTerminalCourseMetadata(
      { category: '英語課程', alias: '第 1 組' },
      { name: '未分類', urls: ['https://example.com/course'] }
    ),
    { category: '英語課程', alias: '第 1 組' }
  )
})

test('imports category and link name from the current CLI group format', () => {
  assert.deepEqual(
    mergeTerminalCourseMetadata(
      { category: '舊分類', alias: '舊名稱' },
      { name: '課程組', category: '英文', urls: ['https://example.com/course'] }
    ),
    { category: '英文', alias: '課程組' }
  )
})

test('imports named legacy groups while preserving a known desktop category', () => {
  assert.deepEqual(
    mergeTerminalCourseMetadata(
      { category: '英文', alias: '原名稱' },
      { name: '終端命名', urls: ['https://example.com/course'] }
    ),
    { category: '英文', alias: '終端命名' }
  )
})

test('identifies removed links so CLI deletions can be reflected in desktop state', () => {
  assert.deepEqual(
    getRemovedTerminalCourseUrls(
      ['https://example.com/a', 'https://example.com/b', 'https://example.com/a'],
      ['https://example.com/b']
    ),
    ['https://example.com/a']
  )
})

test('reconciles external CLI additions, metadata edits, and deletions without dropping unrelated app data', () => {
  const previous = [
    '# group: old\n# category: English\nhttps://example.com/keep\nhttps://example.com/remove'
  ].join('\n')
  const current = [
    '# group: renamed\n# category: Advanced English\nhttps://example.com/keep',
    '# group: Video\n# category: Movies\nhttps://example.com/new'
  ].join('\n')
  assert.deepEqual(
    reconcileTerminalCourses(
      [
        { url: 'https://example.com/keep', category: 'English', alias: 'old' },
        { url: 'https://example.com/remove', category: 'English', alias: 'old' },
        { url: 'https://example.com/desktop-only', category: 'Local', alias: 'local' }
      ],
      previous,
      current
    ),
    [
      { url: 'https://example.com/keep', category: 'Advanced English', alias: 'renamed' },
      { url: 'https://example.com/desktop-only', category: 'Local', alias: 'local' },
      { url: 'https://example.com/new', category: 'Movies', alias: 'Video' }
    ]
  )
})
