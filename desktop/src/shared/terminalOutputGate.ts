export class TerminalOutputGate {
  private isReady = false
  private pending: string[] = []
  private readonly send: (data: string) => void

  constructor(send: (data: string) => void) {
    this.send = send
  }

  write(data: string): void {
    if (this.isReady) {
      this.send(data)
      return
    }
    this.pending.push(data)
  }

  markReady(): void {
    if (this.isReady) return
    this.isReady = true
    for (const data of this.pending) this.send(data)
    this.pending = []
  }
}
