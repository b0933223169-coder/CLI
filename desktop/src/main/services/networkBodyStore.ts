import { randomUUID } from 'crypto'
import { createReadStream } from 'fs'
import { open, mkdir, rm } from 'fs/promises'
import { dirname, join } from 'path'

const BODY_CHUNK_BYTES = 32 * 1024

export interface NetworkBodyCapture {
  id: string
  appendBase64(data: string): Promise<void>
  finish(): Promise<number>
  discard(): Promise<void>
}

async function writeAll(handle: Awaited<ReturnType<typeof open>>, buffer: Buffer): Promise<void> {
  let offset = 0
  while (offset < buffer.length) {
    const { bytesWritten } = await handle.write(buffer, offset, buffer.length - offset)
    offset += bytesWritten
  }
}

export async function createNetworkBodyCapture(
  root: string,
  sessionId: string,
  encoding: 'text' | 'hex',
  storage: 'encrypted' | 'raw',
  encrypt?: (value: string) => Buffer
): Promise<NetworkBodyCapture> {
  if (storage === 'encrypted' && !encrypt) {
    throw new Error('加密網路本文儲存需要加密函式。')
  }
  const encryptChunk = encrypt
  const id = randomUUID()
  const filePath = join(root, sessionId, `${id}.body`)
  await mkdir(dirname(filePath), { recursive: true, mode: 0o700 })
  const handle = await open(filePath, 'wx', 0o600)
  let bytesWritten = 0
  let finished = false
  let pending = Promise.resolve()

  const append = (data: string): Promise<void> => {
    pending = pending.then(async () => {
      if (finished) throw new Error('網路本文串流已結束。')
      const decoded = Buffer.from(data, 'base64')
      for (let offset = 0; offset < decoded.length; offset += BODY_CHUNK_BYTES) {
        const chunk = decoded.subarray(offset, offset + BODY_CHUNK_BYTES)
        if (storage === 'raw') {
          await writeAll(handle, chunk)
        } else {
          const serialized = encoding === 'text' ? chunk : Buffer.from(chunk.toString('hex'))
          if (!encryptChunk) throw new Error('網路本文加密函式不存在。')
          const ciphertext = encryptChunk(serialized.toString('base64'))
          const header = Buffer.allocUnsafe(4)
          header.writeUInt32BE(ciphertext.length)
          await writeAll(handle, header)
          await writeAll(handle, ciphertext)
        }
        bytesWritten += chunk.length
      }
    })
    return pending
  }

  return {
    id,
    appendBase64: append,
    async finish() {
      await pending
      if (!finished) {
        finished = true
        await handle.close()
      }
      return bytesWritten
    },
    async discard() {
      await pending.catch(() => undefined)
      if (!finished) {
        finished = true
        await handle.close()
      }
      await rm(filePath, { force: true })
    }
  }
}

export async function* readRawNetworkBody(filePath: string): AsyncGenerator<Buffer> {
  for await (const chunk of createReadStream(filePath)) {
    yield Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)
  }
}

export async function* readEncryptedNetworkBody(
  filePath: string,
  decrypt: (value: Buffer) => string
): AsyncGenerator<Buffer> {
  const handle = await open(filePath, 'r')
  try {
    const header = Buffer.allocUnsafe(4)
    while (true) {
      let read = 0
      while (read < header.length) {
        const result = await handle.read(header, read, header.length - read, null)
        if (!result.bytesRead) {
          if (!read) return
          throw new Error('網路本文附件格式不完整。')
        }
        read += result.bytesRead
      }
      const ciphertextLength = header.readUInt32BE()
      if (!ciphertextLength || ciphertextLength > BODY_CHUNK_BYTES * 4) {
        throw new Error('網路本文附件區塊大小不合法。')
      }
      const ciphertext = Buffer.allocUnsafe(ciphertextLength)
      read = 0
      while (read < ciphertext.length) {
        const result = await handle.read(ciphertext, read, ciphertext.length - read, null)
        if (!result.bytesRead) throw new Error('網路本文附件資料不完整。')
        read += result.bytesRead
      }
      yield Buffer.from(decrypt(ciphertext), 'base64')
    }
  } finally {
    await handle.close()
  }
}
