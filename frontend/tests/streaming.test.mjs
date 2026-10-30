import { test } from "node:test";
import assert from "node:assert/strict";
import { readEvents } from "../src/streaming.ts";

function body(text, width = 1) {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream({
    start(controller) {
      for (let i = 0; i < bytes.length; i += width)
        controller.enqueue(bytes.slice(i, i + width));
      controller.close();
    },
  });
}

test("SSE handles split Unicode, CRLF, heartbeats, multiline data and completion", async () => {
  const events = [];
  await readEvents(
    body(
      ": heartbeat\r\n\r\nevent: update\r\ndata: नमस्ते 🌍\r\ndata: second line\r\n\r\nevent: done\ndata: {}\n\n",
    ),
    (event, data) => events.push([event, data]),
  );
  assert.deepEqual(events, [
    ["update", "नमस्ते 🌍\nsecond line"],
    ["done", "{}"],
  ]);
});

test("SSE refuses truncated completion and oversized frames", async () => {
  await assert.rejects(
    readEvents(body("event: update\ndata: partial\n\n", 20), () => {}),
    /before completion/,
  );
  await assert.rejects(
    readEvents(body("data: " + "x".repeat(4_500_001), 64_000), () => {}),
    /too large/,
  );
});

test("SSE cancels the reader when processing fails", async () => {
  let cancelled = false;
  const stream = new ReadableStream({
    start(c) {
      c.enqueue(new TextEncoder().encode("data: invalid\n\n"));
    },
    cancel() {
      cancelled = true;
    },
  });
  await assert.rejects(
    readEvents(stream, () => {
      throw new Error("invalid data");
    }),
    /invalid data/,
  );
  assert.equal(cancelled, true);
});
