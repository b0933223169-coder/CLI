import assert from 'node:assert/strict'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'
import {
  createNetworkBodyCapture,
  readEncryptedNetworkBody,
  readRawNetworkBody
} from './networkBodyStore.ts'

/* eslint-disable @typescript-eslint/explicit-function-return-type */
test('streams arbitrarily many response chunks to encrypted storage and reads them back', async () => {
  const root = await mkdtemp(join(tmpdir(), 'cool-network-body-'))
  const sessionId = 'session-id'
  const encryptionKey = Buffer.from('test-encryption-key')
  /** @type {(value: string) => Buffer} */
  const encrypt = (value) => Buffer.concat([encryptionKey, Buffer.from(value, 'utf8')])
  /** @type {(value: Buffer) => string} */
  const decrypt = (value) => value.subarray(encryptionKey.length).toString('utf8')
  const source = Buffer.alloc(2_000_000)
  for (let index = 0; index < source.length; index += 1) source[index] = index % 251
  const capture = await createNetworkBodyCapture(root, sessionId, 'text', 'encrypted', encrypt)

  for (let offset = 0; offset < source.length; offset += 8192) {
    await capture.appendBase64(source.subarray(offset, offset + 8192).toString('base64'))
  }
  assert.equal(await capture.finish(), source.length)

  const storedPath = join(root, sessionId, `${capture.id}.body`)
  const stored = await readFile(storedPath)
  assert.equal(stored.includes(source.subarray(0, 64)), false)
  const chunks = []
  for await (const chunk of readEncryptedNetworkBody(storedPath, decrypt)) chunks.push(chunk)
  assert.deepEqual(Buffer.concat(chunks), source)

  await rm(root, { recursive: true, force: true })
})

test('stores raw body bytes unchanged and unencrypted', async () => {
  const root = await mkdtemp(join(tmpdir(), 'cool-network-body-raw-'))
  const sessionId = 'session-id'
  const source = Buffer.from([0, 1, 2, 10, 13, 127, 128, 255])
  const capture = await createNetworkBodyCapture(root, sessionId, 'hex', 'raw')

  await capture.appendBase64(source.subarray(0, 3).toString('base64'))
  await capture.appendBase64(source.subarray(3).toString('base64'))
  assert.equal(await capture.finish(), source.length)

  const storedPath = join(root, sessionId, `${capture.id}.body`)
  assert.deepEqual(await readFile(storedPath), source)
  const chunks = []
  for await (const chunk of readRawNetworkBody(storedPath)) chunks.push(chunk)
  assert.deepEqual(Buffer.concat(chunks), source)

  await rm(root, { recursive: true, force: true })
})
