export interface TerminalCourseGroup {
  name: string
  category?: string
  urls: string[]
}

export interface CourseMetadata {
  category: string
  alias?: string
}

export interface CourseLinkRecord extends CourseMetadata {
  url: string
}

export function normalizeCourseAlias(category: string, alias?: string): string {
  const normalizedAlias = alias?.trim()
  if (!normalizedAlias || (normalizedAlias === '未分類' && category !== '未分類')) {
    return category
  }
  return normalizedAlias
}

export function mergeTerminalCourseMetadata(
  current: CourseMetadata | undefined,
  group: TerminalCourseGroup
): CourseMetadata {
  const name = group.name.trim() || '未分類'
  const category = group.category?.trim()
  if (!current) return { category: category || name, alias: name }
  if (category) return { category, alias: name }
  if (name === '未分類') return current
  return { category: current.category, alias: name }
}

export function getRemovedTerminalCourseUrls(
  previousUrls: string[],
  currentUrls: string[]
): string[] {
  const current = new Set(currentUrls)
  return [...new Set(previousUrls)].filter((url) => !current.has(url))
}

export function reconcileTerminalCourses(
  existingCourses: CourseLinkRecord[],
  previousContents: string,
  currentContents: string
): CourseLinkRecord[] {
  const previousUrls = parseTerminalCourseGroups(previousContents).flatMap((group) => group.urls)
  const groups = parseTerminalCourseGroups(currentContents)
  const currentUrls = groups.flatMap((group) => group.urls)
  const removedUrls = new Set(getRemovedTerminalCourseUrls(previousUrls, currentUrls))
  const byUrl = new Map(
    existingCourses
      .filter((course) => !removedUrls.has(course.url))
      .map((course) => [course.url, course])
  )
  for (const group of groups) {
    for (const url of group.urls) {
      const metadata = mergeTerminalCourseMetadata(byUrl.get(url), group)
      byUrl.set(url, { url, ...metadata })
    }
  }
  return [...byUrl.values()]
}

export function parseTerminalCourseGroups(contents: string): TerminalCourseGroup[] {
  const groups = new Map<string, Set<string>>()
  let currentGroup = '未分類'
  let currentCategory: string | undefined
  for (const line of contents.split(/\r?\n/)) {
    const trimmed = line.trim()
    const groupMatch = trimmed.match(/^#\s*group:\s*(.*)$/i)
    if (groupMatch) {
      try {
        currentGroup = decodeURIComponent(groupMatch[1]) || '未分類'
      } catch {
        currentGroup = groupMatch[1] || '未分類'
      }
      currentCategory = undefined
      continue
    }
    const categoryMatch = trimmed.match(/^#\s*category:\s*(.*)$/i)
    if (categoryMatch) {
      try {
        currentCategory = decodeURIComponent(categoryMatch[1]) || '未分類'
      } catch {
        currentCategory = categoryMatch[1] || '未分類'
      }
      continue
    }
    const url = trimmed
    if (!/^https?:\/\//i.test(url)) continue
    try {
      const parsed = new URL(url)
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') continue
      const key = JSON.stringify([currentGroup, currentCategory])
      const entries = groups.get(key) ?? new Set<string>()
      entries.add(url)
      groups.set(key, entries)
    } catch {
      // Ignore malformed legacy lines while preserving the rest of the list.
    }
  }
  return [...groups].map(([key, urls]) => {
    const [name, category] = JSON.parse(key) as [string, string | undefined]
    return { name, ...(category ? { category } : {}), urls: [...urls] }
  })
}

export function parseTerminalCourseUrls(contents: string): string[] {
  return [...new Set(parseTerminalCourseGroups(contents).flatMap((group) => group.urls))]
}

export function serializeTerminalCourseGroups(
  groups: TerminalCourseGroup[],
  updatedAt = new Date()
): string {
  const timestamp = updatedAt.toISOString().replace('T', ' ').slice(0, 19)
  const lines: string[] = []
  const seen = new Set<string>()
  for (const group of groups) {
    const groupUrls = new Set<string>()
    const urls = group.urls.filter((url) => {
      if (seen.has(url) || groupUrls.has(url)) return false
      groupUrls.add(url)
      return true
    })
    if (!urls.length) continue
    lines.push(`# group: ${encodeURIComponent(group.name)}`)
    if (group.category) lines.push(`# category: ${encodeURIComponent(group.category)}`)
    for (const url of urls) {
      lines.push(url)
      seen.add(url)
    }
    lines.push('')
  }
  return [
    '# Cool English 課程網址清單',
    `# 最後更新時間: ${timestamp}`,
    '# 每行一個網址，支援 cool -u 快速選取或依序瀏覽',
    '',
    ...lines
  ].join('\n')
}

export function serializeTerminalCourseUrls(urls: string[], updatedAt = new Date()): string {
  return serializeTerminalCourseGroups([{ name: '未分類', urls }], updatedAt)
}
