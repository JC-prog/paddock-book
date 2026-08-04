import { ReadableStream } from 'node:stream/web';

import { ChatApiService } from './chat-api.service';

function encode(chunk: string): Uint8Array {
  return new TextEncoder().encode(chunk);
}

function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
  let i = 0;
  return new ReadableStream<Uint8Array>({
    pull(controller) {
      if (i < chunks.length) {
        controller.enqueue(encode(chunks[i]));
        i++;
      } else {
        controller.close();
      }
    }
  });
}

function makeErroringStream(chunks: string[]): ReadableStream<Uint8Array> {
  let i = 0;
  return new ReadableStream<Uint8Array>({
    pull(controller) {
      if (i < chunks.length) {
        controller.enqueue(encode(chunks[i]));
        i++;
      } else {
        controller.error(new Error('simulated dropped connection'));
      }
    }
  });
}

function makeHungStream(): ReadableStream<Uint8Array> {
  return new ReadableStream<Uint8Array>({
    pull() {
      // Never enqueues, closes, or errors — simulates a connected-but-silent backend.
    }
  });
}

describe('ChatApiService', () => {
  let service: ChatApiService;

  beforeEach(() => {
    service = new ChatApiService();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('emits each word and then completes on a clean stream end', async () => {
    const stream = makeStream(['data: Hello,\n\n', 'data: this\n\ndata: is\n\n']);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(stream, { status: 200 })));

    const emitted: string[] = [];
    let completed = false;

    await new Promise<void>((resolve, reject) => {
      service.streamReply('hi').subscribe({
        next: (word) => emitted.push(word),
        complete: () => {
          completed = true;
          resolve();
        },
        error: reject
      });
    });

    expect(emitted).toEqual(['Hello,', 'this', 'is']);
    expect(completed).toBe(true);
  });

  it('correctly parses a data line split across a chunk boundary', async () => {
    const stream = makeStream(['data: Hel', 'lo,\n\n']);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(stream, { status: 200 })));

    const emitted: string[] = [];

    await new Promise<void>((resolve, reject) => {
      service.streamReply('hi').subscribe({
        next: (word) => emitted.push(word),
        complete: resolve,
        error: reject
      });
    });

    expect(emitted).toEqual(['Hello,']);
  });

  it('errors when the connection drops mid-stream, without losing words already received', async () => {
    const stream = makeErroringStream(['data: Hello,\n\n']);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(stream, { status: 200 })));

    const emitted: string[] = [];
    let errored = false;

    await new Promise<void>((resolve) => {
      service.streamReply('hi').subscribe({
        next: (word) => emitted.push(word),
        complete: () => resolve(),
        error: () => {
          errored = true;
          resolve();
        }
      });
    });

    expect(emitted).toEqual(['Hello,']);
    expect(errored).toBe(true);
  });

  it('errors after 10 seconds of silence with no part of a reply received', async () => {
    vi.useFakeTimers();
    const stream = makeHungStream();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(stream, { status: 200 })));

    let errored = false;
    service.streamReply('hi').subscribe({
      error: () => {
        errored = true;
      }
    });

    await vi.advanceTimersByTimeAsync(10_000);

    expect(errored).toBe(true);
  });
});
