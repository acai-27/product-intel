export const apiClient = async <T>(endpoint: string, options?: RequestInit): Promise<T> => {
  const baseUrl = '/api/v1'; // Assuming a proxy is set in vite.config.ts
  const url = endpoint.startsWith('http') ? endpoint : `${baseUrl}${endpoint}`;

  const headers = {
    'Content-Type': 'application/json',
    ...(options?.headers || {}),
  };

  const config: RequestInit = {
    ...options,
    headers,
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    let detail = errorData?.message || `API Error: ${response.status} ${response.statusText}`;
    if (errorData?.detail) {
      detail = Array.isArray(errorData.detail)
        ? errorData.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ')
        : String(errorData.detail);
    }
    throw new Error(detail);
  }

  return response.json();
};

export default apiClient;

/**
 * SSE event shape yielded by streaming endpoints like /agent/query.
 * Mirrors the `type` field the backend sends: 'status' | 'metadata' | 'text' | 'visualization'.
 */
export interface SSEEvent {
  type: string;
  [key: string]: unknown;
}

/**
 * Reads a `text/event-stream` response body and yields each parsed SSE event
 * as it arrives, in order. Stops when the backend sends the literal
 * "[DONE]" sentinel or the stream closes.
 *
 * This exists because `apiClient`'s plain `response.json()` cannot parse a
 * streaming response -- SSE bodies are a sequence of `data: {...}\n\n`
 * blocks, not a single JSON value, so calling `.json()` on one throws.
 */
export async function* streamSSE(
  endpoint: string,
  options?: RequestInit
): AsyncGenerator<SSEEvent, void, unknown> {
  const baseUrl = '/api/v1';
  const url = endpoint.startsWith('http') ? endpoint : `${baseUrl}${endpoint}`;

  const headers = {
    'Content-Type': 'application/json',
    ...(options?.headers || {}),
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok || !response.body) {
    const errorData = await response.json().catch(() => null);
    const detail = errorData?.detail || errorData?.message || `API Error: ${response.status} ${response.statusText}`;
    throw new Error(String(detail));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by a blank line ("\n\n")
    const events = buffer.split('\n\n');
    buffer = events.pop() ?? ''; // keep the last, possibly-incomplete chunk in the buffer

    for (const rawEvent of events) {
      const line = rawEvent.trim();
      if (!line.startsWith('data:')) continue;

      const payload = line.slice('data:'.length).trim();
      if (payload === '[DONE]') return;

      try {
        yield JSON.parse(payload) as SSEEvent;
      } catch {
        // Skip any malformed/partial event rather than crashing the whole stream
        continue;
      }
    }
  }
}