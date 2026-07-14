import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, Coffee, Sparkles } from 'lucide-react';
import { MarkdownBody } from '../components/MarkdownBody';
import { ThinkingIndicator } from '../components/ThinkingIndicator';
import { useFilters } from '../components/FilterContext';
import ChatVizPanel from '../components/ChatVizPanel';
import { ChatVisualization, Message } from '../types';

const STARTER_PROMPTS = [
  'Why did revenue dip last week?',
  'Summarize top-performing products',
  'What-if: raise prices 5%?',
  'Explain conversion trends',
];

export default function WorkspacePage() {
  const { selectedProduct, startDate, endDate } = useFilters();
  const [chatInput, setChatInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'assistant',
      text: "Welcome back — grab a metaphorical coffee and ask me anything about your business. I can explain dips, run simulations, scan anomalies, or look up product performance.",
    },
  ]);

  const [isStreaming, setIsStreaming] = useState(false);
  const [currentLogs, setCurrentLogs] = useState<string[]>([]);

  const chatMessagesRef = useRef<HTMLDivElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const isAutoScrolling = useRef(true);

  const handleScroll = () => {
    const el = chatMessagesRef.current;
    if (!el) return;
    const isAtBottom = el.scrollHeight - el.scrollTop <= el.clientHeight + 80;
    if (isAtBottom) {
      isAutoScrolling.current = true;
      setShowScrollBtn(false);
    } else {
      isAutoScrolling.current = false;
      setShowScrollBtn(true);
    }
  };

  const handleScrollToBottom = () => {
    isAutoScrolling.current = true;
    setShowScrollBtn(false);
    const el = chatMessagesRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  };

  useEffect(() => {
    if (isAutoScrolling.current && chatMessagesRef.current) {
      const el = chatMessagesRef.current;
      el.scrollTop = el.scrollHeight;
    }
  }, [messages, isStreaming, currentLogs]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isStreaming) return;

    setMessages((prev) => [...prev, { sender: 'user', text }]);
    setChatInput('');
    setCurrentLogs([]);
    setIsStreaming(true);
    setMessages((prev) => [...prev, { sender: 'assistant', text: '' }]);

    try {
      const response = await fetch('/api/v1/agent/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: text,
          context: {
            product_id: selectedProduct || null,
            start_date: startDate || null,
            end_date: endDate || null,
          },
        }),
      });

      if (!response.ok) throw new Error('Network error');

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        let currentText = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6).trim();
              if (dataStr === '[DONE]' || !dataStr) continue;

              try {
                const data = JSON.parse(dataStr);
                if (data.type === 'status' || data.type === 'viz_planning') {
                  setCurrentLogs((prev) => [...prev, data.content]);
                } else if (data.type === 'metadata') {
                  setMessages((prev) => {
                    const newMsgs = [...prev];
                    newMsgs[newMsgs.length - 1] = {
                      ...newMsgs[newMsgs.length - 1],
                      meta: { route: data.route_called },
                    };
                    return newMsgs;
                  });
                } else if (data.type === 'viz_plan') {
                  const placeholders: ChatVisualization[] = (data.visualizations || []).map(
                    (v: ChatVisualization) => ({ ...v, status: 'loading' })
                  );
                  setMessages((prev) => {
                    const newMsgs = [...prev];
                    newMsgs[newMsgs.length - 1] = {
                      ...newMsgs[newMsgs.length - 1],
                      visualizations: placeholders,
                    };
                    return newMsgs;
                  });
                } else if (data.type === 'viz_ready') {
                  const chart = data.chart;
                  setMessages((prev) => {
                    const newMsgs = [...prev];
                    const last = newMsgs[newMsgs.length - 1];
                    const vizs = (last.visualizations || []).map((v) =>
                      v.id === data.id
                        ? {
                            id: chart.id,
                            title: chart.title,
                            subtitle: chart.subtitle,
                            chart_type: chart.chart_type,
                            index_axis: chart.index_axis,
                            status: 'ready' as const,
                            data: chart.data,
                          }
                        : v
                    );
                    newMsgs[newMsgs.length - 1] = { ...last, visualizations: vizs };
                    return newMsgs;
                  });
                } else if (data.type === 'viz_error') {
                  setMessages((prev) => {
                    const newMsgs = [...prev];
                    const last = newMsgs[newMsgs.length - 1];
                    const vizs = (last.visualizations || []).map((v) =>
                      v.id === data.id ? { ...v, status: 'error' as const } : v
                    );
                    newMsgs[newMsgs.length - 1] = { ...last, visualizations: vizs };
                    return newMsgs;
                  });
                } else if (data.type === 'text') {
                  currentText += data.content;
                  setMessages((prev) => {
                    const newMsgs = [...prev];
                    newMsgs[newMsgs.length - 1] = {
                      ...newMsgs[newMsgs.length - 1],
                      text: currentText,
                    };
                    return newMsgs;
                  });
                }
              } catch {
                // incomplete stream chunk
              }
            }
          }
        }
      }
    } catch {
      setMessages((prev) => {
        const newMsgs = [...prev];
        newMsgs[newMsgs.length - 1] = {
          sender: 'assistant',
          text: 'Could not reach the analytics assistant. Check your connection and try again.',
        };
        return newMsgs;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(chatInput);
  };

  return (
    <div className="workspace-lounge">
      <header className="pin-hero animate-fade-in" style={{ position: 'relative' }}>
        <div>
          <div className="pin-hero-eyebrow">
            <Coffee size={14} />
            AI lounge
          </div>
          <h1>Ask anything — stay awhile</h1>
          <p className="pin-hero-desc">
            Your analyst is here for forecasts, anomaly scans, what-if runs, and plain-language summaries. No jargon required.
          </p>
        </div>
        <div className="pin-hero-badge">
          <span>Ready</span>
          <strong>
            <Sparkles size={22} style={{ color: 'var(--cozy-rose)' }} />
          </strong>
        </div>
      </header>

      <div className="workspace-suggestions animate-fade-in">
        {STARTER_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            className="workspace-chip"
            onClick={() => sendMessage(prompt)}
            disabled={isStreaming}
          >
            {prompt}
          </button>
        ))}
      </div>

      <div className="chat-container chat-container--cozy animate-fade-in" style={{ position: 'relative' }}>
        <div className="chat-messages" ref={chatMessagesRef} onScroll={handleScroll}>
          {messages.map((msg, index) => {
            const hasText = msg.text && msg.text.trim().length > 0;
            const hasViz = (msg.visualizations?.length ?? 0) > 0;
            if (!hasText && !hasViz && msg.sender === 'assistant' && isStreaming && index === messages.length - 1) {
              return null;
            }

            return (
              <div key={index} className={`chat-bubble ${msg.sender}`}>
                {msg.sender === 'assistant' ? (
                  <MarkdownBody content={msg.text} />
                ) : (
                  msg.text
                )}
                {msg.visualizations && msg.visualizations.length > 0 && (
                  <ChatVizPanel visualizations={msg.visualizations} />
                )}
                {msg.meta && (
                  <div
                    style={{
                      marginTop: '8px',
                      fontSize: '11px',
                      color: 'var(--text-muted)',
                      borderTop: '1px solid var(--border-subtle)',
                      paddingTop: '6px',
                    }}
                  >
                    Routed to: <code>{msg.meta.route}</code>
                  </div>
                )}
              </div>
            );
          })}

          {isStreaming && (
            <div className="chat-bubble assistant">
              <ThinkingIndicator logs={currentLogs} />
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {showScrollBtn && (
          <button
            type="button"
            className="scroll-bottom-btn animate-fade-in"
            onClick={handleScrollToBottom}
            aria-label="Scroll to bottom"
          >
            <ChevronDown size={18} />
          </button>
        )}

        <form className="chat-input-container" onSubmit={handleSendMessage}>
          <input
            type="text"
            className="chat-input"
            placeholder="Ask about revenue, experiments, or run a simulation…"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            disabled={isStreaming}
          />
          <button type="submit" className="chat-send-btn" disabled={isStreaming || !chatInput.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
