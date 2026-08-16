import { useState, useRef, useEffect } from "react";

// ── Design tokens ──────────────────────────────────────────────────────────
// Navy blue dominant, teal accent, red for Nepal flag nod
// Monospace for numbers/data — feels utility-grade, appropriate for a power authority

const API = "http://localhost:8000";

const SUGGESTED = [
  "Who is the current MD of NEA?",
  "What are the tariff rates for 0-20 units?",
  "No light number for Baneshwor?",
  "How to apply for new electricity connection?",
  "How to pay NEA bill online?",
  "What is NEA's total generation capacity?",
  "How to file a complaint?",
  "What is the tariff for commercial consumers?",
];

function BoltIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 5, alignItems: "center", padding: "6px 2px" }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: 7, height: 7, borderRadius: "50%",
          background: "#00B4D8",
          animation: "pulse 1.2s ease-in-out infinite",
          animationDelay: `${i * 0.18}s`,
        }} />
      ))}
    </div>
  );
}

// ── Lightweight markdown-ish formatter ──────────────────────────────────
// The chat model replies with **bold**, blank-line paragraphs, and
// "- "/"1. " list items. This turns that into real left-aligned HTML
// (headings, <p>, <ul>/<ol>) instead of one flat string of <br/> tags.
function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function formatInline(line) {
  return escapeHtml(line)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(?<!\*)\*(?!\*)(.+?)\*(?!\*)/g, "<em>$1</em>");
}

function lineKind(line) {
  if (/^[-•*]\s+/.test(line)) return "bullet";
  if (/^\d+[.)]\s+/.test(line)) return "numbered";
  return "plain";
}

function formatMessage(text) {
  const blocks = text.trim().split(/\n\s*\n/); // split into paragraphs/lists
  const html = [];

  for (const block of blocks) {
    const lines = block.split("\n").map(l => l.trim()).filter(Boolean);
    if (lines.length === 0) continue;

    // A short line wrapped entirely in ** or a markdown # heads its own block
    const isHeading =
      lines.length === 1 &&
      (/^\*\*(.+)\*\*$/.test(lines[0]) || /^#{1,3}\s+/.test(lines[0])) &&
      lines[0].length < 90;

    if (isHeading) {
      const headingText = lines[0].replace(/^#{1,3}\s+/, "").replace(/^\*\*(.+)\*\*$/, "$1");
      html.push(`<h4>${formatInline(headingText)}</h4>`);
      continue;
    }

    // Group contiguous lines of the same kind (plain/bullet/numbered) so an
    // intro sentence followed by a list — even without a blank line between
    // them, which the model often does — still renders as text + a real list.
    let i = 0;
    while (i < lines.length) {
      const kind = lineKind(lines[i]);
      let j = i + 1;
      while (j < lines.length && lineKind(lines[j]) === kind) j++;
      const group = lines.slice(i, j);

      if (kind === "bullet") {
        const items = group.map(l => `<li>${formatInline(l.replace(/^[-•*]\s+/, ""))}</li>`).join("");
        html.push(`<ul>${items}</ul>`);
      } else if (kind === "numbered") {
        const items = group.map(l => `<li>${formatInline(l.replace(/^\d+[.)]\s+/, ""))}</li>`).join("");
        html.push(`<ol>${items}</ol>`);
      } else {
        html.push(`<p>${group.map(formatInline).join("<br/>")}</p>`);
      }
      i = j;
    }
  }

  return html.join("");
}

function MessageBubble({ msg }) {
  const isUser = msg.role === "user";

  const renderAnswer = (text, sources) => {
    if (!text) return null;

    return (
      <div>
        <div
          className="msg-content"
          style={{ textAlign: "left" }}
          dangerouslySetInnerHTML={{ __html: formatMessage(text) }}
        />
        {sources && sources.length > 0 && (
          <div style={{
            marginTop: 12,
            paddingTop: 10,
            borderTop: "1px solid rgba(0,180,216,0.15)",
            fontSize: 12,
          }}>
            <span style={{ color: "#00B4D8", fontWeight: 700, marginRight: 8 }}>Sources</span>
            {sources.map((url, i) => (
              <span key={i}>
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "#64748B", textDecoration: "underline", wordBreak: "break-all" }}
                >
                  {url.replace("https://", "").replace(/\/$/, "")}
                </a>
                {i < sources.length - 1 && <span style={{ color: "#334155", margin: "0 6px" }}>·</span>}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{
      display: "flex",
      flexDirection: isUser ? "row-reverse" : "row",
      gap: 10,
      marginBottom: 20,
      alignItems: "flex-start",
    }}>
      {/* Avatar */}
      <div style={{
        width: 34, height: 34, borderRadius: "50%", flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: isUser ? 12 : 16, fontWeight: 800,
        background: isUser
          ? "linear-gradient(135deg, #1E3A5F, #2D5A8E)"
          : "linear-gradient(135deg, #004E6E, #00B4D8)",
        color: "white",
        boxShadow: isUser
          ? "0 2px 8px rgba(30,58,95,0.4)"
          : "0 2px 8px rgba(0,180,216,0.3)",
      }}>
        {isUser ? "You" : <BoltIcon />}
      </div>

      {/* Bubble */}
      <div style={{
        maxWidth: "76%",
        padding: "12px 16px",
        borderRadius: isUser ? "18px 4px 18px 18px" : "4px 18px 18px 18px",
        background: isUser
          ? "linear-gradient(135deg, #1E3A5F, #0D2B4E)"
          : "#1A2740",
        color: "#E2E8F0",
        fontSize: 14,
        lineHeight: 1.6,
        boxShadow: "0 2px 12px rgba(0,0,0,0.25)",
        border: isUser ? "none" : "1px solid rgba(0,180,216,0.15)",
      }}>
        {msg.typing
          ? <TypingIndicator />
          : isUser
            ? <div style={{ textAlign: "left", whiteSpace: "pre-wrap" }}>{msg.content}</div>
            : renderAnswer(msg.content, msg.sources)
        }
      </div>
    </div>
  );
}

export default function NEAChatbot() {
  const [messages, setMessages] = useState([{
    role: "assistant",
    content: "**Namaste! ⚡ I'm the NEA Assistant.**\n\nI can answer questions about Nepal Electricity Authority — tariff rates, no-light numbers, new connections, bill payment, careers, and more.\n\nWhat can I help you with?",
  }]);
  const [input, setInput]     = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus]   = useState(null); // {chunks, model}
  const [error, setError]     = useState(null);
  const bottomRef             = useRef(null);
  const inputRef              = useRef(null);

  // Check backend health on mount
  useEffect(() => {
    fetch(`${API}/health`)
      .then(r => r.json())
      .then(d => setStatus(d))
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text) => {
    const userText = (text || input).trim();
    if (!userText || loading) return;
    setInput("");
    setError(null);

    const history = messages
      .filter(m => !m.typing)
      .map(m => ({ role: m.role, content: m.content }));

    const newMessages = [...messages, { role: "user", content: userText }];
    setMessages([...newMessages, { role: "assistant", typing: true }]);
    setLoading(true);

    try {
      const resp = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText, history }),
      });

      if (!resp.ok) throw new Error(`Server error: ${resp.status}`);

      // Read SSE stream
      const reader  = resp.body.getReader();
      const decoder = new TextDecoder();
      let answer    = "";
      let sources   = [];

      setMessages([...newMessages, { role: "assistant", content: "", streaming: true }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split("\n").filter(l => l.startsWith("data: "));

        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.text) {
              answer += data.text;
              setMessages([...newMessages, { role: "assistant", content: answer, sources: [], streaming: true }]);
            }
            if (data.sources) sources = data.sources;
            if (data.error) throw new Error(data.error);
          } catch (e) {
            if (e.message.startsWith("Server")) throw e;
          }
        }
      }

      // Store sources separately — render them cleanly, not as raw text
      setMessages([...newMessages, { role: "assistant", content: answer, sources }]);

    } catch (e) {
      setError(e.message || "Something went wrong");
      setMessages(newMessages);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const isFirstMessage = messages.length <= 1;

  return (
    <div style={{
      display: "flex",
      height: "100vh",
      fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      background: "#0A1628",
      color: "#E2E8F0",
      overflow: "hidden",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        @keyframes pulse {
          0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
          40% { transform: scale(1); opacity: 1; }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; } 50% { opacity: 0; }
        }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1E3A5F; border-radius: 3px; }
        textarea { resize: none; font-family: inherit; }
        textarea:focus { outline: none; }
        button { cursor: pointer; border: none; font-family: inherit; }
        a { color: #00B4D8; }

        /* Assistant message formatting — left-aligned, readable spacing */
        .msg-content { font-size: 14px; line-height: 1.75; }
        .msg-content p { margin: 0 0 10px; }
        .msg-content p:last-child { margin-bottom: 0; }
        .msg-content h4 {
          font-size: 14px;
          font-weight: 700;
          color: #F8FAFC;
          margin: 14px 0 6px;
        }
        .msg-content h4:first-child { margin-top: 0; }
        .msg-content ul, .msg-content ol {
          margin: 0 0 10px;
          padding-left: 20px;
        }
        .msg-content ul:last-child, .msg-content ol:last-child { margin-bottom: 0; }
        .msg-content li { margin-bottom: 4px; }
        .msg-content li:last-child { margin-bottom: 0; }
        .msg-content strong { color: #F8FAFC; font-weight: 700; }
      `}</style>

      {/* ── Sidebar ──────────────────────────────────────────────────── */}
      <div style={{
        width: 260,
        flexShrink: 0,
        background: "#0D1B3E",
        borderRight: "1px solid rgba(0,180,216,0.12)",
        display: "flex",
        flexDirection: "column",
        padding: "24px 16px",
        gap: 24,
      }}>
        {/* Logo */}
        <div>
          <div style={{
            display: "flex", alignItems: "center", gap: 10, marginBottom: 6,
          }}>
            <div style={{
              width: 38, height: 38, borderRadius: 10,
              background: "linear-gradient(135deg, #004E6E, #00B4D8)",
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "white", fontSize: 18, flexShrink: 0,
              boxShadow: "0 0 16px rgba(0,180,216,0.3)",
            }}>
              <BoltIcon />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, color: "#F8FAFC" }}>NEA Assistant</div>
              <div style={{ fontSize: 11, color: "#64748B" }}>nea.org.np</div>
            </div>
          </div>

          {/* Status indicator */}
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "6px 10px",
            background: "rgba(0,180,216,0.07)",
            borderRadius: 8,
            border: "1px solid rgba(0,180,216,0.12)",
            marginTop: 10,
          }}>
            <div style={{
              width: 7, height: 7, borderRadius: "50%",
              background: status ? "#22C55E" : "#EF4444",
              boxShadow: status ? "0 0 6px #22C55E" : "none",
            }} />
            <span style={{ fontSize: 11, color: "#94A3B8" }}>
              {status
                ? `${status.chunks?.toLocaleString()} knowledge chunks`
                : "Backend offline — run app.py"
              }
            </span>
          </div>
        </div>

        {/* Suggested questions */}
        <div>
          <div style={{
            fontSize: 10, fontWeight: 700, color: "#475569",
            textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 10,
          }}>
            Quick Questions
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {SUGGESTED.map((q, i) => (
              <button
                key={i}
                onClick={() => sendMessage(q)}
                disabled={loading}
                style={{
                  background: "transparent",
                  border: "1px solid rgba(0,180,216,0.15)",
                  color: "#94A3B8",
                  padding: "7px 10px",
                  borderRadius: 8,
                  fontSize: 12,
                  textAlign: "left",
                  transition: "all 0.15s",
                  lineHeight: 1.4,
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = "rgba(0,180,216,0.08)";
                  e.currentTarget.style.borderColor = "rgba(0,180,216,0.3)";
                  e.currentTarget.style.color = "#CBD5E1";
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.borderColor = "rgba(0,180,216,0.15)";
                  e.currentTarget.style.color = "#94A3B8";
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Footer links */}
        <div style={{ marginTop: "auto" }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>
            Quick Links
          </div>
          {[
            ["Check Bill", "https://www.neabilling.com/viewonline/"],
            ["File Complaint", "https://crm.nea.org.np/complain"],
            ["Careers", "https://career.nea.org.np"],
            ["Tenders", "https://nea.org.np/tender/prequalification"],
          ].map(([label, href]) => (
            <a key={label} href={href} target="_blank" rel="noopener noreferrer"
              style={{
                display: "block", fontSize: 12, color: "#64748B",
                padding: "5px 0", textDecoration: "none",
                borderBottom: "1px solid rgba(255,255,255,0.04)",
              }}
              onMouseEnter={e => e.currentTarget.style.color = "#00B4D8"}
              onMouseLeave={e => e.currentTarget.style.color = "#64748B"}
            >
              {label} ↗
            </a>
          ))}
          <div style={{ marginTop: 12, fontSize: 10, color: "#334155" }}>
            Emergency: <span style={{ color: "#94A3B8", fontFamily: "monospace" }}>1400</span> / <span style={{ color: "#94A3B8", fontFamily: "monospace" }}>1402</span>
          </div>
        </div>
      </div>

      {/* ── Main Chat Area ──────────────────────────────────────────── */}
      <div style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}>

        {/* Header */}
        <div style={{
          padding: "16px 24px",
          borderBottom: "1px solid rgba(0,180,216,0.1)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "#0A1628",
          flexShrink: 0,
        }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16, color: "#F8FAFC" }}>
              नेपाल विद्युत प्राधिकरण
            </div>
            <div style={{ fontSize: 12, color: "#475569", marginTop: 1 }}>
              Nepal Electricity Authority — AI Assistant
            </div>
          </div>
          <div style={{
            fontSize: 11, color: "#475569",
            padding: "4px 10px",
            border: "1px solid rgba(0,180,216,0.1)",
            borderRadius: 20,
          }}>
            Powered by Groq + RAG
          </div>
        </div>

        {/* Messages */}
        <div style={{
          flex: 1,
          overflowY: "auto",
          padding: "24px",
          display: "flex",
          flexDirection: "column",
        }}>
          {/* Welcome hero — only on first load */}
          {isFirstMessage && (
            <div style={{
              textAlign: "center",
              padding: "40px 20px 32px",
              marginBottom: 8,
            }}>
              <div style={{
                width: 64, height: 64, borderRadius: 16, margin: "0 auto 16px",
                background: "linear-gradient(135deg, #004E6E, #00B4D8)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 32, color: "white",
                boxShadow: "0 0 40px rgba(0,180,216,0.25)",
              }}>
                <BoltIcon />
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, color: "#F8FAFC", marginBottom: 8 }}>
                NEA Knowledge Assistant
              </div>
              <div style={{ fontSize: 14, color: "#64748B", maxWidth: 400, margin: "0 auto" }}>
                Ask me anything about Nepal Electricity Authority — tariffs, contacts, connections, and more.
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <MessageBubble key={i} msg={msg} />
          ))}

          {error && (
            <div style={{
              background: "rgba(192,57,43,0.1)",
              border: "1px solid rgba(192,57,43,0.3)",
              color: "#E07070",
              padding: "10px 14px",
              borderRadius: 10,
              fontSize: 13,
              marginBottom: 12,
            }}>
              ⚠️ {error} — Is the backend running? (<code style={{ fontSize: 11 }}>python app.py</code>)
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div style={{
          padding: "16px 24px 20px",
          borderTop: "1px solid rgba(0,180,216,0.1)",
          background: "#0A1628",
          flexShrink: 0,
        }}>
          <div style={{
            display: "flex",
            gap: 10,
            alignItems: "flex-end",
            background: "#0D1B3E",
            border: `1px solid ${loading ? "rgba(0,180,216,0.5)" : "rgba(0,180,216,0.2)"}`,
            borderRadius: 14,
            padding: "10px 12px 10px 16px",
            transition: "border-color 0.2s",
            boxShadow: loading ? "0 0 20px rgba(0,180,216,0.08)" : "none",
          }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask anything about NEA..."
              rows={1}
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                color: "#E2E8F0",
                fontSize: 14,
                lineHeight: 1.6,
                maxHeight: 120,
                overflowY: "auto",
                paddingTop: 2,
              }}
            />
            <button
              onClick={() => sendMessage()}
              disabled={loading || !input.trim()}
              style={{
                width: 36, height: 36, borderRadius: 10, flexShrink: 0,
                background: loading || !input.trim()
                  ? "rgba(0,180,216,0.15)"
                  : "linear-gradient(135deg, #004E6E, #00B4D8)",
                color: loading || !input.trim() ? "#475569" : "white",
                display: "flex", alignItems: "center", justifyContent: "center",
                transition: "all 0.15s",
                boxShadow: loading || !input.trim() ? "none" : "0 4px 12px rgba(0,180,216,0.3)",
              }}
            >
              {loading
                ? <div style={{ width: 14, height: 14, border: "2px solid #00B4D8", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
                : <SendIcon />
              }
            </button>
          </div>
          <div style={{ fontSize: 11, color: "#1E3A5F", textAlign: "center", marginTop: 8 }}>
            Information sourced from nea.org.np · Always verify critical info on the official site
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
