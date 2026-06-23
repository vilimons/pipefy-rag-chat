import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  clearChatHistory,
  getChatHistory,
  streamChatMessage,
  getHealth
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
  const [modelLabel, setModelLabel] = useState("Carregando modelo...");

  useEffect(() => {
    getHealth()
      .then((health) => {
        setModelLabel(health.llm?.model ?? "Modelo não informado");
      })
      .catch(() => {
        setModelLabel("Modelo indisponível");
      });
  }, []);
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
      setStatus("Carregando histórico da conversa...");

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
          : "Não foi possível carregar o histórico."
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
          : "Não foi possível limpar o histórico."
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
    setStatus("Recuperando fontes relevantes...");
    setIsLoading(true);
    setQuestion("");

    setSessions((currentSessions) =>
      currentSessions.map((session) =>
        session.id === activeSessionId
          ? {
              ...session,
              title:
                session.title === "Nova conversa" || session.title === "New chat"
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
            setStatus("Gerando resposta com Ollama...");

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
          : "Não foi possível enviar a mensagem."
      );
    } finally {
      setIsLoading(false);
      setStatus("");
    }
  }

  return (
    <section className="chat-surface">
      <div className="chat-sidebar">
        <div className="chat-sidebar-heading">
          <div>
            <p className="eyebrow small">Sessões</p>
            <h2>Conversas</h2>
          </div>

          <button type="button" className="icon-button" onClick={handleNewSession}>
            +
          </button>
        </div>

        <div className="session-list" aria-label="Conversas">
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
              <span>{new Date(session.createdAt).toLocaleString("pt-BR")}</span>
            </button>
          ))}
        </div>

        <button type="button" className="secondary-action" onClick={handleClearSession}>
          Limpar conversa atual
        </button>
      </div>

      <div className="chat-main">
        <div className="chat-main-header">
          <div>
            <p className="eyebrow small">RAG Chat</p>
            <h2>Assistente de documentos</h2>
            <p className="session">Sessão: {activeSessionId}</p>
          </div>

          <div className="model-badge">
            <span className="status-dot" />
            {modelLabel}
          </div>
        </div>

        <div className="messages">
          {messages.length === 0 ? (
            <div className="empty-chat">
              <strong>Faça uma pergunta sobre seus documentos</strong>
            </div>
          ) : (
            messages.map((message) => (
              <article key={message.id} className={`message ${message.role}`}>
                <div className="message-label">
                  {message.role === "user" ? "Você" : "Assistente"}
                </div>

                <p>{message.content || status || "Pensando..."}</p>

                {message.sources && message.sources.length > 0 && (
                  <details className="sources-box">
                    <summary>Fontes recuperadas</summary>
                    <ul>
                      {message.sources.map((source) => (
                        <li key={`${source.file_id}-${source.chunk_index}`}>
                          <strong>{source.source}</strong>
                          <span>score {source.score.toFixed(4)}</span>
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
            placeholder="Pergunte algo sobre os documentos indexados..."
          />
          <button type="submit" disabled={isLoading}>
            {isLoading ? "Gerando..." : "Enviar"}
          </button>
        </form>

        {status && <p className="status">{status}</p>}
        {error && <p className="error">{error}</p>}
      </div>
    </section>
  );
}

function createSession(): ChatSession {
  return {
    id: crypto.randomUUID(),
    title: "Nova conversa",
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

    return parsedSessions.map((session) => ({
      ...session,
      title: session.title === "New chat" ? "Nova conversa" : session.title
    }));
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
