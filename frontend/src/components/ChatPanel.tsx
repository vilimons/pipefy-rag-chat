import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  clearChatHistory,
  getChatHistory,
  streamChatMessage
} from "../api/client";
import type { ChatHistoryMessage, SourceChunk } from "../types/api";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
};

type ChatSession = {
  id: string;
  title: string;
  createdAt: string;
};

const SESSIONS_STORAGE_KEY = "pipefy-rag-chat-sessions";
const ACTIVE_SESSION_STORAGE_KEY = "pipefy-rag-chat-active-session";

export function ChatPanel() {
  const initialSession = useMemo(() => createSession(), []);
  const [sessions, setSessions] = useState<ChatSession[]>(() =>
    loadSessions(initialSession)
  );
  const [activeSessionId, setActiveSessionId] = useState(() =>
    loadActiveSessionId(initialSession.id)
  );
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(sessions));
  }, [sessions]);

  useEffect(() => {
    localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, activeSessionId);
    void loadHistory(activeSessionId);
  }, [activeSessionId]);

  async function loadHistory(sessionId: string) {
    try {
      setError("");
      setStatus("Loading session history...");

      const history = await getChatHistory(sessionId);

      setMessages(
        history.messages.map((message) => ({
          id: crypto.randomUUID(),
          role: normalizeRole(message),
          content: message.content
        }))
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Failed to load session history."
      );
    } finally {
      setStatus("");
    }
  }

  function handleNewSession() {
    const session = createSession();

    setSessions((currentSessions) => [session, ...currentSessions]);
    setActiveSessionId(session.id);
    setMessages([]);
    setQuestion("");
    setError("");
  }

  async function handleClearSession() {
    setError("");

    try {
      await clearChatHistory(activeSessionId);
      setMessages([]);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Failed to clear session history."
      );
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();

    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) {
      return;
    }

    const assistantMessageId = crypto.randomUUID();

    setError("");
    setStatus("Retrieving relevant sources...");
    setIsLoading(true);
    setQuestion("");

    setSessions((currentSessions) =>
      currentSessions.map((session) =>
        session.id === activeSessionId
          ? {
              ...session,
              title:
                session.title === "New chat"
                  ? createTitle(trimmedQuestion)
                  : session.title
            }
          : session
      )
    );

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmedQuestion
      },
      {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        sources: []
      }
    ]);

    try {
      await streamChatMessage(
        {
          question: trimmedQuestion,
          sessionId: activeSessionId,
          topK: 3
        },
        (streamEvent) => {
          if (streamEvent.event === "sources") {
            setStatus("Generating answer...");

            setMessages((currentMessages) =>
              currentMessages.map((message) =>
                message.id === assistantMessageId
                  ? {
                      ...message,
                      sources: streamEvent.data as SourceChunk[]
                    }
                  : message
              )
            );
          }

          if (streamEvent.event === "token") {
            setStatus("");

            setMessages((currentMessages) =>
              currentMessages.map((message) =>
                message.id === assistantMessageId
                  ? {
                      ...message,
                      content: `${message.content}${String(streamEvent.data)}`
                    }
                  : message
              )
            );
          }

          if (streamEvent.event === "error") {
            setError(String(streamEvent.data));
            setStatus("");
          }

          if (streamEvent.event === "done") {
            setStatus("");
          }
        }
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Failed to send message."
      );
    } finally {
      setIsLoading(false);
      setStatus("");
    }
  }

  return (
    <section className="card chat-card">
      <div className="chat-header">
        <div>
          <h2>RAG Chat</h2>
          <p className="session">Session: {activeSessionId}</p>
        </div>

        <div className="chat-actions">
          <button type="button" onClick={handleNewSession}>
            New chat
          </button>
          <button type="button" className="secondary" onClick={handleClearSession}>
            Clear
          </button>
        </div>
      </div>

      <div className="chat-layout">
        <aside className="session-list" aria-label="Chat sessions">
          {sessions.map((session) => (
            <button
              type="button"
              key={session.id}
              className={
                session.id === activeSessionId
                  ? "session-item active"
                  : "session-item"
              }
              onClick={() => setActiveSessionId(session.id)}
            >
              <strong>{session.title}</strong>
              <span>{new Date(session.createdAt).toLocaleString()}</span>
            </button>
          ))}
        </aside>

        <div className="chat-main">
          <div className="messages">
            {messages.length === 0 ? (
              <p>Ask something about the indexed documents.</p>
            ) : (
              messages.map((message) => (
                <article key={message.id} className={message.role}>
                  <strong>
                    {message.role === "user" ? "You" : "Assistant"}
                  </strong>
                  <p>{message.content || status || "Thinking..."}</p>

                  {message.sources && message.sources.length > 0 && (
                    <details>
                      <summary>Sources</summary>
                      <ul>
                        {message.sources.map((source) => (
                          <li key={`${source.file_id}-${source.chunk_index}`}>
                            <strong>{source.source}</strong> · score{" "}
                            {source.score}
                            <p>{source.chunk}</p>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </article>
              ))
            )}
          </div>

          <form onSubmit={handleSubmit} className="chat-form">
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask a question about your documents..."
            />
            <button type="submit" disabled={isLoading}>
              {isLoading ? "Thinking..." : "Send"}
            </button>
          </form>

          {status && <p className="status">{status}</p>}
          {error && <p className="error">{error}</p>}
        </div>
      </div>
    </section>
  );
}

function createSession(): ChatSession {
  return {
    id: crypto.randomUUID(),
    title: "New chat",
    createdAt: new Date().toISOString()
  };
}

function createTitle(question: string): string {
  return question.length > 40 ? `${question.slice(0, 40)}...` : question;
}

function loadSessions(fallbackSession: ChatSession): ChatSession[] {
  const rawSessions = localStorage.getItem(SESSIONS_STORAGE_KEY);

  if (!rawSessions) {
    return [fallbackSession];
  }

  try {
    const parsedSessions = JSON.parse(rawSessions) as ChatSession[];

    if (parsedSessions.length === 0) {
      return [fallbackSession];
    }

    return parsedSessions;
  } catch {
    return [fallbackSession];
  }
}

function loadActiveSessionId(fallbackSessionId: string): string {
  return localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY) ?? fallbackSessionId;
}

function normalizeRole(message: ChatHistoryMessage): "user" | "assistant" {
  return message.role === "assistant" ? "assistant" : "user";
}
