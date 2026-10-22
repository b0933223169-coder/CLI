export interface CoolLoginCompletion<TCookie> {
  cookies: TCookie[]
  filterCookies: (cookies: TCookie[]) => TCookie[]
  hasUsableSession: (cookies: TCookie[]) => boolean
  validate: () => Promise<boolean>
  persist: (cookies: TCookie[]) => Promise<void>
  markCompleted: () => Promise<void>
  closeBrowser: () => Promise<void>
}

export async function completeCoolEnglishLogin<TCookie>(
  completion: CoolLoginCompletion<TCookie>
): Promise<TCookie[]> {
  const cookies = completion.filterCookies(completion.cookies)
  if (!completion.hasUsableSession(cookies)) {
    throw new Error('未取得有效的 Cool English MoodleSession cookie。')
  }
  if (!(await completion.validate())) {
    throw new Error('Cool English 尚未確認此 MoodleSession 已登入。')
  }

  await completion.persist(cookies)
  await completion.markCompleted()
  await completion.closeBrowser()
  return cookies
}
