import { streamSSE } from '../api/client';
import { ChatResponse } from '../types';

export interface ChatPayload {
  query: string;
  context: {
    product_id: string | null;
    start_date: string | null;
    end_date: string | null;
  };
}

/**
 * Sends a workspace query to the streaming /agent/query endpoint and
 * aggregates the SSE events (status updates, metadata, text chunks) into
 * the final ChatResponse shape the rest of the app expects.
 *
 * NOTE: this still waits for the full stream to finish before resolving --
 * it fixes the broken .json() parse on a streaming body, but does not add
 * progressive/token-by-token rendering in the UI. That's a separate,
 * frontend-side enhancement (onEvent callback below is there to support it
 * later without another rewrite of this function).
 */
export const sendWorkspaceQuery = async (
  payload: ChatPayload,
  onEvent?: (event: { type: string;[key: string]: unknown }) => void
): Promise<ChatResponse> => {
  let responseText = '';
  let routedTo = '';

  for await (const event of streamSSE('/agent/query', {
    method: 'POST',
    body: JSON.stringify(payload),
  })) {
    onEvent?.(event);

    if (event.type === 'text' && typeof event.content === 'string') {
      responseText += event.content;
    } else if (event.type === 'metadata' && typeof event.route_called === 'string') {
      routedTo = event.route_called;
    }
  }

  return { response: responseText, routed_to: routedTo };
};