// SSE frames can span network reads, including inside a UTF-8 character.
export async function readEvents(
  body: ReadableStream<Uint8Array>,
  receive: (event: string, data: string) => void,
  activity: () => void = () => {},
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  let event = "message";
  let data: string[] = [];
  let frameSize = 0;
  try {
    for (;;) {
      const chunk = await reader.read();
      if (chunk.done)
        throw new Error("The response connection ended before completion.");
      activity();
      pending += decoder.decode(chunk.value, { stream: true });
      let end: number;
      while ((end = pending.indexOf("\n")) >= 0) {
        const line = pending.slice(0, end).replace(/\r$/, "");
        pending = pending.slice(end + 1);
        frameSize += line.length;
        if (frameSize > 4_500_000)
          throw new Error("The response update is too large.");
        if (!line) {
          if (data.length) {
            receive(event, data.join("\n"));
            if (event === "done") return;
          }
          event = "message";
          data = [];
          frameSize = 0;
        } else if (line.startsWith("event:")) {
          event = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          data.push(line.slice(5).replace(/^ /, ""));
        }
      }
      if (pending.length > 4_500_000)
        throw new Error("The response update is too large.");
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
