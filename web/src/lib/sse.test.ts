// @vitest-environment node
import { describe, expect, it } from "vitest";

import { parseEventStream, readTurnEvents } from "@/lib/sse";

/** A byte stream that delivers `text` in chunks of `size` bytes (splitting characters too). */
function streamOf(text: string, size: number): ReadableStream<Uint8Array> {
  const bytes = new TextEncoder().encode(text);
  let offset = 0;
  return new ReadableStream({
    pull(controller) {
      if (offset >= bytes.length) {
        controller.close();
        return;
      }
      controller.enqueue(bytes.slice(offset, offset + size));
      offset += size;
    },
  });
}

async function collect<T>(iterator: AsyncIterable<T>): Promise<T[]> {
  const items: T[] = [];
  for await (const item of iterator) items.push(item);
  return items;
}

const BODY = [
  'event: route\ndata: {"type":"route","route":"tutor","reason":"asks","new_problem":false}\n\n',
  ": ping\n\n",
  'event: token\ndata: {"type":"token","text":"Câu hỏi hay đấy! "}\n\n',
  'event: done\ndata: {"type":"done","session_id":"s1","route":"tutor","reply":"Câu hỏi hay đấy!","hint_level":1,"grade":null}\n\n',
].join("");

describe("parseEventStream", () => {
  it.each([1, 2, 3, 7, 64, 4096])("handles %i-byte chunks, including split characters", async (size) => {
    const events = await collect(parseEventStream(streamOf(BODY, size)));
    expect(events.map((e) => e.event)).toEqual(["route", "token", "done"]);
    expect(JSON.parse(events[1].data)).toEqual({ type: "token", text: "Câu hỏi hay đấy! " });
  });

  it("supports CRLF line endings, multi-line data and a final event without a blank line", async () => {
    const body = "event: note\r\ndata: first\r\ndata: second\r\n\r\ndata: tail";
    for (const size of [1, 5, 100]) {
      const events = await collect(parseEventStream(streamOf(body, size)));
      expect(events).toEqual([
        { event: "note", data: "first\nsecond" },
        { event: "message", data: "tail" },
      ]);
    }
  });
});

describe("readTurnEvents", () => {
  it("yields typed tutor events", async () => {
    const events = await collect(readTurnEvents(streamOf(BODY, 9)));
    expect(events.map((e) => e.type)).toEqual(["route", "token", "done"]);
    const done = events[2];
    expect(done.type === "done" && done.hint_level).toBe(1);
  });

  it("skips events whose name and payload type disagree", async () => {
    const body = 'event: token\ndata: {"type":"done"}\n\nevent: reset\ndata: {"type":"reset","reason":"answer_leak"}\n\n';
    const events = await collect(readTurnEvents(streamOf(body, 4)));
    expect(events).toEqual([{ type: "reset", reason: "answer_leak" }]);
  });
});
