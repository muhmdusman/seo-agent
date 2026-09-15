export interface AnalysisEvent {
  type: 'status' | 'result' | 'completed' | 'error';
  message?: string;
  report_id?: string;
}

export async function* analysisEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<AnalysisEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      let boundary;
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const data = frame.split('\n').filter(line => line.startsWith('data:'))
          .map(line => line.slice(5).trimStart()).join('\n');
        if (data) yield JSON.parse(data) as AnalysisEvent;
      }
      if (done) break;
    }
    if (buffer.trim()) throw new Error('The analysis stream ended before its final message.');
  } finally {
    await reader.cancel();
    reader.releaseLock();
  }
}
