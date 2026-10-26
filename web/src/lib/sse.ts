import type { TurnEvent } from "@/lib/types";

export interface ServerSentEvent {
  event: string;
  data: string;
}

/**
 * Parse a `text/event-stream` body into events.
 *
 * `EventSource` only supports GET, and the chat endpoint is a POST, so the stream is read
 * with `fetch`. Chunks can split an event, a line or even a multi-byte character anywhere:
 * the decoder runs in streaming mode and only complete events (ending in a blank line) are
 * emitted. Comment lines (keep-alive pings) are ignored.
 */
export async function* parseEventStream(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<ServerSentEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      // Normalise line endings, keeping a trailing "\r" whose "\n" may be in the next chunk.
      const pendingCR = !done && buffer.endsWith("\r");
      buffer = (pendingCR ? buffer.slice(0, -1) : buffer).replace(/\r\n?/g, "\n");
      if (pendingCR) buffer += "\r";
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const parsed = parseBlock(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 2);
        if (parsed) yield parsed;
        boundary = buffer.indexOf("\n\n");
      }
      if (done) break;
    }
    const tail = parseBlock(buffer);
    if (tail) yield tail;
  } finally {
    reader.releaseLock();
  }
}

function parseBlock(block: string): ServerSentEvent | null {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (!line || line.startsWith(":")) continue;
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") event = value;
    else if (field === "data") data.push(value);
  }
  return data.length ? { event, data: data.join("\n") } : null;
}

/** Turn raw server-sent events into typed tutor events (unknown events are skipped). */
export async function* readTurnEvents(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<TurnEvent> {
  for await (const { event, data } of parseEventStream(body)) {
    const payload = JSON.parse(data) as TurnEvent;
    if (payload.type === event) yield payload;
  }
}
