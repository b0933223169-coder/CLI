import type { NetworkEvent, NetworkSession } from './types'

export interface NetworkSessionExport {
  format: 'cool-network-session'
  version: 1
  exportedAt: string
  session: NetworkSession
}

export function createNetworkSessionExport(
  session: NetworkSession,
  exportedAt = new Date().toISOString()
): NetworkSessionExport {
  return {
    format: 'cool-network-session',
    version: 1,
    exportedAt,
    session: {
      ...session,
      events: session.events.map((event) => ({
        ...event,
        ...(event.headers ? { headers: { ...event.headers } } : {})
      }))
    }
  }
}

async function* serializeEvent(
  event: NetworkEvent,
  readBody: (attachmentId: string) => AsyncIterable<Buffer>
): AsyncGenerator<string> {
  if (!event.bodyAttachmentId) {
    yield JSON.stringify(event)
    return
  }
  yield JSON.stringify({ ...event, bodyDataBase64: '' }).slice(0, -2)
  let remainder = Buffer.alloc(0)
  for await (const chunk of readBody(event.bodyAttachmentId)) {
    const data = remainder.length ? Buffer.concat([remainder, chunk]) : chunk
    const completeLength = data.length - (data.length % 3)
    if (completeLength) yield data.subarray(0, completeLength).toString('base64')
    remainder = Buffer.from(data.subarray(completeLength))
  }
  if (remainder.length) yield remainder.toString('base64')
  yield '"}'
}

export async function* serializeNetworkSessionRaw(
  session: NetworkSession,
  readBody: (attachmentId: string) => AsyncIterable<Buffer>
): AsyncGenerator<string> {
  for (let index = session.events.length - 1; index >= 0; index -= 1) {
    const event = session.events[index]
    yield `${JSON.stringify({ recordType: 'event', ...event })}\n`
    if (!event.bodyAttachmentId) continue
    const decoder = event.bodyEncoding === 'text' ? new TextDecoder('utf-8') : undefined
    let chunkIndex = 0
    for await (const chunk of readBody(event.bodyAttachmentId)) {
      const data =
        event.bodyStorage === 'raw'
          ? chunk.toString('base64')
          : decoder
            ? decoder.decode(chunk, { stream: true })
            : chunk.toString('hex')
      if (data) {
        yield `${JSON.stringify({
          recordType: 'body-chunk',
          bodyAttachmentId: event.bodyAttachmentId,
          encoding: event.bodyStorage === 'raw' ? 'base64' : (event.bodyEncoding ?? 'hex'),
          chunk: chunkIndex,
          data
        })}\n`
        chunkIndex += 1
      }
    }
    const finalText = event.bodyStorage === 'raw' ? undefined : decoder?.decode()
    if (finalText) {
      yield `${JSON.stringify({
        recordType: 'body-chunk',
        bodyAttachmentId: event.bodyAttachmentId,
        encoding: 'text',
        chunk: chunkIndex,
        data: finalText
      })}\n`
    }
  }
}

export async function* serializeNetworkSessionExport(
  session: NetworkSession,
  readBody: (attachmentId: string) => AsyncIterable<Buffer>,
  exportedAt = new Date().toISOString()
): AsyncGenerator<string> {
  const { events, ...metadata } = session
  const serializedMetadata = JSON.stringify(metadata)
  yield `{"format":"cool-network-session","version":1,"exportedAt":${JSON.stringify(exportedAt)},"session":${serializedMetadata.slice(0, -1)},"events":[`
  for (let index = 0; index < events.length; index += 1) {
    yield `${index ? ',' : ''}`
    yield* serializeEvent(events[index], readBody)
  }
  yield ']}}\n'
}
