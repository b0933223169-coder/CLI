import assert from 'node:assert/strict'
import test from 'node:test'
import {
  createNetworkSessionExport,
  serializeNetworkSessionExport,
  serializeNetworkSessionRaw
} from './networkSessionExport.ts'

/* eslint-disable @typescript-eslint/explicit-function-return-type */
test('exports only the selected session and retains its event data', () => {
  const session = {
    id: 'session-1',
    label: 'Login',
    mode: 'headless',
    startedAt: '2026-10-21T10:00:00.000Z',
    endedAt: '2026-10-21T10:01:00.000Z',
    status: 'failed',
    events: [
      {
        sessionId: 'session-1',
        sessionLabel: 'Login',
        mode: 'headless',
        kind: 'response',
        status: 403,
        url: 'https://example.test/',
        headers: { 'content-type': 'text/html' },
        bodyPreview: 'Challenge page',
        time: '2026-10-21T10:00:01.000Z'
      }
    ]
  }

  const exported = createNetworkSessionExport(session, '2026-10-21T10:02:00.000Z')

  assert.equal(exported.format, 'cool-network-session')
  assert.equal(exported.version, 1)
  assert.equal(exported.exportedAt, '2026-10-21T10:02:00.000Z')
  assert.deepEqual(exported.session, session)
  assert.notEqual(exported.session, session)
  assert.notEqual(exported.session.events[0], session.events[0])
  assert.notEqual(exported.session.events[0].headers, session.events[0].headers)
})

test('streams complete response attachments into raw and exported JSON without buffering them', async () => {
  const body = Buffer.from('response-'.repeat(250_000), 'utf8')
  const session = {
    id: 'session-2',
    label: 'Course',
    mode: 'headed',
    startedAt: '2026-10-21T10:00:00.000Z',
    status: 'completed',
    events: [
      {
        sessionId: 'session-2',
        sessionLabel: 'Course',
        mode: 'headed',
        kind: 'response',
        url: 'https://example.test/data',
        bodyAttachmentId: 'body-1',
        bodyEncoding: 'text',
        bodyBytes: body.length,
        time: '2026-10-21T10:00:01.000Z'
      }
    ]
  }
  /** @type {(id: string) => AsyncGenerator<Buffer>} */
  const readBody = async function* (id) {
    assert.equal(id, 'body-1')
    for (let offset = 0; offset < body.length; offset += 8192) {
      yield body.subarray(offset, offset + 8192)
    }
  }

  let exportedText = ''
  for await (const chunk of serializeNetworkSessionExport(
    session,
    readBody,
    '2026-10-21T10:02:00.000Z'
  )) {
    exportedText += chunk
  }
  const exported = JSON.parse(exportedText)
  assert.deepEqual(Buffer.from(exported.session.events[0].bodyDataBase64, 'base64'), body)

  const rawLines = []
  for await (const chunk of serializeNetworkSessionRaw(session, readBody)) rawLines.push(chunk)
  const rawRecords = rawLines.map((line) => JSON.parse(line))
  assert.equal(rawRecords[0].recordType, 'event')
  assert.equal(
    rawRecords
      .filter((record) => record.recordType === 'body-chunk')
      .map((record) => record.data)
      .join(''),
    body.toString('utf8')
  )
})

test('exports raw body chunks as lossless base64 data', async () => {
  const body = Buffer.from([0, 1, 2, 10, 13, 127, 128, 255])
  const session = {
    id: 'session-raw',
    label: 'Raw',
    mode: 'headed',
    startedAt: '2026-10-21T10:00:00.000Z',
    status: 'completed',
    events: [
      {
        sessionId: 'session-raw',
        sessionLabel: 'Raw',
        mode: 'headed',
        kind: 'request',
        url: 'https://example.test/upload',
        bodyAttachmentId: 'body-raw',
        bodySource: 'request',
        bodyStorage: 'raw',
        bodyEncoding: 'hex',
        bodyBytes: body.length,
        time: '2026-10-21T10:00:01.000Z'
      }
    ]
  }
  /** @type {(id: string) => AsyncGenerator<Buffer>} */
  const readBody = async function* (id) {
    assert.equal(id, 'body-raw')
    yield body.subarray(0, 3)
    yield body.subarray(3)
  }

  const records = []
  for await (const chunk of serializeNetworkSessionRaw(session, readBody)) {
    records.push(JSON.parse(chunk))
  }
  const bodyRecords = records.filter((record) => record.recordType === 'body-chunk')
  assert.deepEqual(
    bodyRecords.map((record) => record.encoding),
    ['base64', 'base64']
  )
  assert.deepEqual(
    Buffer.concat(bodyRecords.map((record) => Buffer.from(record.data, 'base64'))),
    body
  )

  let exportedText = ''
  for await (const chunk of serializeNetworkSessionExport(session, readBody)) {
    exportedText += chunk
  }
  const exported = JSON.parse(exportedText)
  assert.deepEqual(Buffer.from(exported.session.events[0].bodyDataBase64, 'base64'), body)
})
