import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { v4 as uuidv4 } from 'uuid';
import { chatApi, documentApi } from './services/api';

const MODES = [
  { id: 'chat', label: '💬 Chat', desc: 'Conversational AI with memory' },
  { id: 'rag', label: '📄 RAG', desc: 'Ask questions about uploaded docs' },
  { id: 'agent', label: '🤖 Agent', desc: 'AI with tools: search, calc, weather' },
  { id: 'summarize', label: '📝 Summarize', desc: 'Summarize docs or conversation' },
];

const EXAMPLE_PROMPTS = {
  chat: ["Explain quantum computing simply", "Write a Python fibonacci function", "What are microservices?"],
  rag: ["What are the key findings in the document?", "Summarize the main points", "What does the document say about..."],
  agent: ["What's the weather in New York?", "Calculate compound interest: $10000 at 7% for 10 years", "Search for recent AI developments"],
  summarize: ["Summarize the uploaded document", "Give me the key points", "Summarize our conversation so far"],
};

function MarkdownContent({ content }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ node, inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          return !inline && match ? (
            <SyntaxHighlighter style={oneDark} language={match[1]} PreTag="div" {...props}>
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          ) : (
            <code style={{ background: '#1e293b', padding: '2px 6px', borderRadius: 4, fontSize: '0.9em', fontFamily: 'monospace' }} {...props}>
              {children}
            </code>
          );
        },
        p: ({ children }) => <p style={{ margin: '0 0 8px', lineHeight: 1.6 }}>{children}</p>,
        ul: ({ children }) => <ul style={{ margin: '4px 0', paddingLeft: 20 }}>{children}</ul>,
        ol: ({ children }) => <ol style={{ margin: '4px 0', paddingLeft: 20 }}>{children}</ol>,
        li: ({ children }) => <li style={{ marginBottom: 2 }}>{children}</li>,
        h1: ({ children }) => <h1 style={{ fontSize: 18, fontWeight: 700, margin: '8px 0 4px', color: '#f1f5f9' }}>{children}</h1>,
        h2: ({ children }) => <h2 style={{ fontSize: 16, fontWeight: 600, margin: '8px 0 4px', color: '#f1f5f9' }}>{children}</h2>,
        h3: ({ children }) => <h3 style={{ fontSize: 14, fontWeight: 600, margin: '6px 0 2px', color: '#cbd5e1' }}>{children}</h3>,
        blockquote: ({ children }) => <blockquote style={{ borderLeft: '3px solid #3b82f6', paddingLeft: 12, margin: '8px 0', color: '#94a3b8' }}>{children}</blockquote>,
        table: ({ children }) => <div style={{ overflowX: 'auto', margin: '8px 0' }}><table style={{ borderCollapse: 'collapse', width: '100%' }}>{children}</table></div>,
        th: ({ children }) => <th style={{ padding: '6px 10px', background: '#1e293b', border: '1px solid #334155', textAlign: 'left', fontSize: 12 }}>{children}</th>,
        td: ({ children }) => <td style={{ padding: '6px 10px', border: '1px solid #334155', fontSize: 13 }}>{children}</td>,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

function AgentSteps({ steps }) {
  const [open, setOpen] = useState(false);
  if (!steps || steps.length === 0) return null;
  return (
    <div style={{ marginTop: 8, borderTop: '1px solid #1e293b', paddingTop: 8 }}>
      <button onClick={() => setOpen(o => !o)}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
        {open ? '▾' : '▸'} {steps.length} agent step{steps.length > 1 ? 's' : ''}
      </button>
      {open && (
        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {steps.map((step, i) => (
            <div key={i} style={{ background: '#0f172a', borderRadius: 6, padding: '8px 12px', fontSize: 12, fontFamily: 'monospace' }}>
              <div style={{ color: step.type === 'tool_call' ? '#f59e0b' : '#10b981', marginBottom: 4 }}>
                {step.type === 'tool_call' ? `🔧 ${step.tool}` : `✓ ${step.tool}`}
              </div>
              {step.input && <div style={{ color: '#64748b' }}>{JSON.stringify(step.input)}</div>}
              {step.output && <div style={{ color: '#94a3b8', marginTop: 2 }}>{step.output}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Sources({ sources }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>SOURCES</div>
      {sources.map((src, i) => (
        <div key={i} style={{ background: '#0f172a', borderRadius: 6, padding: '6px 10px', fontSize: 12 }}>
          <div style={{ color: '#3b82f6', fontWeight: 600 }}>{src.filename} {src.page !== 'N/A' && `· p.${src.page}`}</div>
          <div style={{ color: '#64748b', marginTop: 2, lineHeight: 1.4 }}>{src.excerpt}</div>
        </div>
      ))}
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <div style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', marginBottom: 16, gap: 10, alignItems: 'flex-start' }}>
      {!isUser && (
        <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, flexShrink: 0 }}>
          🤖
        </div>
      )}
      <div style={{ maxWidth: '75%', minWidth: 60 }}>
        <div style={{
          background: isUser ? 'linear-gradient(135deg, #3b82f6, #2563eb)' : '#1e293b',
          color: '#e2e8f0', borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
          padding: '12px 16px', fontSize: 14, lineHeight: 1.5
        }}>
          {isUser ? msg.content : <MarkdownContent content={msg.content} />}
        </div>
        {msg.agent_steps && <AgentSteps steps={msg.agent_steps} />}
        {msg.sources && <Sources sources={msg.sources} />}
        <div style={{ fontSize: 11, color: '#475569', marginTop: 4, textAlign: isUser ? 'right' : 'left' }}>
          {msg.latency_ms ? `${msg.latency_ms}ms` : ''}
          {msg.timestamp && ` · ${new Date(msg.timestamp).toLocaleTimeString()}`}
        </div>
      </div>
      {isUser && (
        <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#334155', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, flexShrink: 0 }}>
          👤
        </div>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 16 }}>
      <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>🤖</div>
      <div style={{ background: '#1e293b', borderRadius: '18px 18px 18px 4px', padding: '14px 18px', display: 'flex', gap: 6, alignItems: 'center' }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{ width: 8, height: 8, borderRadius: '50%', background: '#3b82f6', animation: `pulse 1.2s ${i * 0.2}s infinite` }} />
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [mode, setMode] = useState('chat');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [docsLoaded, setDocsLoaded] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [uploadStatus, setUploadStatus] = useState(null);
  const bottomRef = useRef(null);
  const fileRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    initSession();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const initSession = async () => {
    try {
      const { session_id } = await chatApi.newSession();
      setSessionId(session_id);
    } catch {
      setSessionId(uuidv4());
    }
  };

  const send = async () => {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput('');

    const userMsg = { role: 'user', content: text, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await chatApi.sendMessage({
        session_id: sessionId,
        message: text,
        mode,
        stream: false
      });

      const aiMsg = {
        role: 'assistant',
        content: response.message.content,
        timestamp: response.message.timestamp,
        sources: response.sources,
        agent_steps: response.agent_steps,
        latency_ms: response.latency_ms
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `❌ Error: ${err.response?.data?.detail || err.message}`,
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const uploadFile = async (file) => {
    if (!file || !sessionId) return;
    setUploading(true);
    setUploadStatus(null);
    try {
      const result = await documentApi.upload(sessionId, file);
      setDocsLoaded(d => d + 1);
      setUploadStatus({ success: true, msg: `✓ ${result.filename} — ${result.chunks_created} chunks indexed` });
      if (mode === 'chat') setMode('rag');
    } catch (err) {
      setUploadStatus({ success: false, msg: `✗ Upload failed: ${err.response?.data?.detail || err.message}` });
    } finally {
      setUploading(false);
      setTimeout(() => setUploadStatus(null), 4000);
    }
  };

  const clearAll = async () => {
    if (!sessionId) return;
    await chatApi.clearSession(sessionId);
    setMessages([]);
    setDocsLoaded(0);
    setUploadStatus(null);
  };

  const newSession = async () => {
    setMessages([]);
    setDocsLoaded(0);
    setUploadStatus(null);
    await initSession();
  };

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#0f172a', color: '#e2e8f0', fontFamily: 'system-ui, -apple-system, sans-serif', overflow: 'hidden' }}>
      <style>{`
        @keyframes pulse { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; } 40% { transform: scale(1); opacity: 1; } }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-track { background: transparent; } ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
        textarea { resize: none; }
      `}</style>

      {/* Sidebar */}
      {sidebarOpen && (
        <div style={{ width: 260, background: '#0a0f1e', borderRight: '1px solid #1e293b', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
          {/* Logo */}
          <div style={{ padding: '20px 16px', borderBottom: '1px solid #1e293b' }}>
            <div style={{ fontSize: 18, fontWeight: 700, background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              ✦ GenAI Chat
            </div>
            <div style={{ fontSize: 11, color: '#475569', marginTop: 2 }}>LangChain · LangGraph · RAG</div>
          </div>

          {/* Mode selector */}
          <div style={{ padding: '16px 12px', borderBottom: '1px solid #1e293b' }}>
            <div style={{ fontSize: 10, color: '#475569', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>MODE</div>
            {MODES.map(m => (
              <button key={m.id} onClick={() => setMode(m.id)}
                style={{
                  width: '100%', textAlign: 'left', padding: '8px 10px', borderRadius: 8, border: 'none', cursor: 'pointer', marginBottom: 4,
                  background: mode === m.id ? '#1e293b' : 'transparent',
                  color: mode === m.id ? '#e2e8f0' : '#64748b',
                  borderLeft: mode === m.id ? '3px solid #3b82f6' : '3px solid transparent'
                }}>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{m.label}</div>
                <div style={{ fontSize: 11, color: '#475569', marginTop: 1 }}>{m.desc}</div>
              </button>
            ))}
          </div>

          {/* Upload */}
          <div style={{ padding: '16px 12px', borderBottom: '1px solid #1e293b' }}>
            <div style={{ fontSize: 10, color: '#475569', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>DOCUMENTS</div>
            <button onClick={() => fileRef.current?.click()}
              disabled={uploading}
              style={{ width: '100%', padding: '8px 12px', background: '#1e293b', border: '1px dashed #334155', borderRadius: 8, color: '#94a3b8', cursor: 'pointer', fontSize: 13 }}>
              {uploading ? '⏳ Uploading...' : '📎 Upload File'}
            </button>
            <input ref={fileRef} type="file" style={{ display: 'none' }} accept=".pdf,.txt,.md,.docx"
              onChange={e => e.target.files[0] && uploadFile(e.target.files[0])} />
            {docsLoaded > 0 && (
              <div style={{ marginTop: 6, fontSize: 12, color: '#10b981' }}>✓ {docsLoaded} document{docsLoaded > 1 ? 's' : ''} indexed</div>
            )}
            {uploadStatus && (
              <div style={{ marginTop: 6, fontSize: 11, color: uploadStatus.success ? '#10b981' : '#ef4444', lineHeight: 1.3 }}>{uploadStatus.msg}</div>
            )}
          </div>

          {/* Actions */}
          <div style={{ padding: '12px', marginTop: 'auto', borderTop: '1px solid #1e293b' }}>
            <button onClick={newSession} style={{ width: '100%', padding: '7px', background: '#1e293b', border: 'none', borderRadius: 6, color: '#94a3b8', cursor: 'pointer', fontSize: 13, marginBottom: 6 }}>
              + New Session
            </button>
            <button onClick={clearAll} style={{ width: '100%', padding: '7px', background: 'transparent', border: '1px solid #334155', borderRadius: 6, color: '#64748b', cursor: 'pointer', fontSize: 13 }}>
              🗑 Clear Chat
            </button>
            {sessionId && (
              <div style={{ marginTop: 8, fontSize: 10, color: '#334155', wordBreak: 'break-all' }}>
                Session: {sessionId.substring(0, 20)}...
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main chat area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Header */}
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #1e293b', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
          <button onClick={() => setSidebarOpen(o => !o)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', fontSize: 18 }}>☰</button>
          <div>
            <div style={{ fontWeight: 600, fontSize: 15 }}>
              {MODES.find(m => m.id === mode)?.label}
            </div>
            <div style={{ fontSize: 12, color: '#475569' }}>{MODES.find(m => m.id === mode)?.desc}</div>
          </div>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 20px' }}>
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', marginTop: 60 }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>✦</div>
              <div style={{ fontSize: 22, fontWeight: 700, background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', marginBottom: 8 }}>
                GenAI Chat
              </div>
              <div style={{ color: '#475569', fontSize: 14, marginBottom: 32 }}>LangChain · LangGraph · RAG · Redis Memory</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center', maxWidth: 520, margin: '0 auto' }}>
                {EXAMPLE_PROMPTS[mode]?.map((p, i) => (
                  <button key={i} onClick={() => { setInput(p); textareaRef.current?.focus(); }}
                    style={{ padding: '8px 14px', background: '#1e293b', border: '1px solid #334155', borderRadius: 20, color: '#94a3b8', cursor: 'pointer', fontSize: 13 }}>
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg, i) => <Message key={i} msg={msg} />)}
          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div style={{ padding: '16px 20px', borderTop: '1px solid #1e293b', flexShrink: 0 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end', background: '#1e293b', borderRadius: 14, padding: '10px 14px', border: '1px solid #334155' }}>
            <textarea ref={textareaRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown}
              placeholder={`Message in ${mode} mode... (Enter to send, Shift+Enter for newline)`}
              rows={1}
              style={{
                flex: 1, background: 'none', border: 'none', outline: 'none', color: '#e2e8f0',
                fontSize: 14, lineHeight: 1.5, maxHeight: 120, overflowY: 'auto',
                fontFamily: 'inherit'
              }}
              onInput={e => {
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
              }}
            />
            <button onClick={send} disabled={loading || !input.trim()}
              style={{
                width: 36, height: 36, borderRadius: 10, border: 'none', cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                background: loading || !input.trim() ? '#334155' : 'linear-gradient(135deg, #3b82f6, #2563eb)',
                color: '#fff', fontSize: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
              }}>
              {loading ? '⏳' : '↑'}
            </button>
          </div>
          <div style={{ textAlign: 'center', fontSize: 11, color: '#334155', marginTop: 8 }}>
            Powered by GPT-4o · LangChain · LangGraph · FAISS · Redis
          </div>
        </div>
      </div>
    </div>
  );
}
