import type { CoolApi } from '../shared/types'

declare global {
  interface Window {
    cool: CoolApi
  }
}
