import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  clearChatHistory,
  getChatHistory,
  getHealth,
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

type SessionDialog =
  | {
      mode: "rename";
      sessionId: string;
      title: string;
    }
  | {
      mode: "delete";
      sessionId: string;
      title: string;
    }
  | null;

const SESSIONS_STORAGE_KEY = "pipefy-rag-chat-sessions";
const ACTIVE_SESSION_STORAGE_KEY = "pipefy-rag-chat-active-session";
const DEFAULT_SESSION_TITLE = "Nova conversa";

export function ChatPanel() {
  const initialSession = useMemo(() => createSession(), []);

  const [sessions, setSessions] = useState<ChatSession[]>(() =>
    loadSessions(initialSession)
  );
  const [activeSessionId, setActiveSessionId] = useState<string>(() =>
    loadActiveSessionId(initialSession.id)
  );
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [modelLabel, setModelLabel] = useState("Carregando modelo...");
  const [error, setError] = useState("");
  const [sessionDialog, setSessionDialog] = useState<SessionDialog>(null);
  const [renameDraft, setRenameDraft] = useState("");

  useEffect(() => {
    getHealth()
      .then((health) => {
        setModelLabel(health.llm?.model ?? "Modelo não informado");
      })
      .catch(() => {
        setModelLabel("Modelo indisponível");
      });
  }, []);

  useEffect(() => {
    if (!sessionDialog) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeSessionDialog();
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [sessionDialog]);

  useEffect(() => {
    localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(sessions));
  }, [sessions]);

  useEffect(() => {
    if (sessions.length === 0) {
      const session = createSession();
      setSessions([session]);
      setActiveSessionId(session.id);
      return;
    }

    if (!sessions.some((session) => session.id === activeSessionId)) {
      setActiveSessionId(sessions[0].id);
    }
  }, [activeSessionId, sessions]);

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
    setStatus("");
  }

  async function handleClearSession() {
    setError("");
    setStatus("");

    try {
      await clearChatHistory(activeSessionId);
      setMessages([]);
      setQuestion("");

      setSessions((currentSessions) =>
        currentSessions.map((session) =>
          session.id === activeSessionId
            ? { ...session, title: DEFAULT_SESSION_TITLE }
            : session
        )
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível limpar o histórico."
      );
    }
  }

  function openRenameDialog(sessionId: string) {
    const session = sessions.find((currentSession) => currentSession.id === sessionId);

    if (!session) {
      return;
    }

    setRenameDraft(session.title);
    setSessionDialog({
      mode: "rename",
      sessionId,
      title: session.title
    });
  }

  function openDeleteDialog(sessionId: string) {
    const session = sessions.find((currentSession) => currentSession.id === sessionId);

    if (!session) {
      return;
    }

    setSessionDialog({
      mode: "delete",
      sessionId,
      title: session.title
    });
  }

  function closeSessionDialog() {
    setSessionDialog(null);
    setRenameDraft("");
  }

  function confirmRenameSession() {
    if (!sessionDialog || sessionDialog.mode !== "rename") {
      return;
    }

    const nextTitle = renameDraft.trim();

    if (!nextTitle) {
      return;
    }

    setSessions((currentSessions) =>
      currentSessions.map((currentSession) =>
        currentSession.id === sessionDialog.sessionId
          ? { ...currentSession, title: nextTitle }
          : currentSession
      )
    );

    closeSessionDialog();
  }

  async function confirmDeleteSession() {
    if (!sessionDialog || sessionDialog.mode !== "delete") {
      return;
    }

    const sessionId = sessionDialog.sessionId;
    const remainingSessions = sessions.filter((session) => session.id !== sessionId);

    closeSessionDialog();
    setError("");
    setStatus("");

    try {
      await clearChatHistory(sessionId);
    } catch {
      // Keep deleting the local session even if the remote history is already unavailable.
    }

    if (remainingSessions.length === 0) {
      const fallbackSession = createSession();

      setSessions([fallbackSession]);
      setActiveSessionId(fallbackSession.id);
      setMessages([]);
      setQuestion("");

      return;
    }

    setSessions(remainingSessions);

    if (sessionId === activeSessionId) {
      setActiveSessionId(remainingSessions[0].id);
      setMessages([]);
      setQuestion("");
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
                session.title === DEFAULT_SESSION_TITLE || session.title === "New chat"
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
                  ? { ...message, sources: streamEvent.data as SourceChunk[] }
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
      <aside className="chat-sidebar">
        <div className="chat-sidebar-heading">
          <div>
            <p className="eyebrow small">Sessões</p>
            <h2>Conversas</h2>
          </div>

          <button
            type="button"
            className="icon-button"
            onClick={handleNewSession}
            aria-label="Criar nova conversa"
            title="Nova conversa"
          >
            +
          </button>
        </div>

        <div className="session-list">
          {sessions.map((session) => (
            <article
              key={session.id}
              className={`session-item ${
                session.id === activeSessionId ? "active" : ""
              }`}
            >
              <button
                type="button"
                className="session-select"
                onClick={() => setActiveSessionId(session.id)}
              >
                <strong>{session.title}</strong>
                <span>{new Date(session.createdAt).toLocaleString("pt-BR")}</span>
              </button>

              <div className="session-actions">
                <button
                  type="button"
                  className="session-action"
                  onClick={() => openRenameDialog(session.id)}
                  title="Renomear conversa"
                >
                  Renomear
                </button>

                <button
                  type="button"
                  className="session-action danger-link"
                  onClick={() => openDeleteDialog(session.id)}
                  title="Excluir conversa"
                >
                  Excluir
                </button>
              </div>
            </article>
          ))}
        </div>

        <button
          type="button"
          className="secondary-action"
          onClick={() => void handleClearSession()}
        >
          Limpar conversa atual
        </button>
      </aside>

      <div className="chat-main">
        <div className="chat-main-header">
          <div>
            <p className="eyebrow small">RAG Chat</p>
            <h2>Assistente de documentos</h2>
            <p className="session">Sessão: {activeSessionId}</p>
          </div>

          <span className="model-badge">
            <span className="status-dot" />
            {modelLabel}
          </span>
        </div>

        <div className="messages">
          {messages.length === 0 ? (
            <div className="empty-chat">
              <strong>Faça uma pergunta sobre seus documentos</strong>
            </div>
          ) : (
            messages.map((message) => (
              <div key={message.id} className={`message ${message.role}`}>
                <span className="message-label">
                  {message.role === "user" ? "Você" : "Assistente"}
                </span>

                <p>{message.content || status || "Pensando..."}</p>

                {message.sources && message.sources.length > 0 && (
                  <details className="sources-box">
                    <summary>Fontes recuperadas</summary>

                    <ul>
                      {message.sources.map((source) => (
                        <li key={`${source.file_id}-${source.chunk_index}-${source.score}`}>
                          <strong>{source.source}</strong>
                          <span>score {source.score.toFixed(4)}</span>
                          <p>{source.chunk}</p>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            ))
          )}
        </div>

        <form className="chat-form" onSubmit={(event) => void handleSubmit(event)}>
          <input
            value={question}
            disabled={isLoading}
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

      {sessionDialog && (
        <div
          className="session-modal-backdrop"
          role="presentation"
          onMouseDown={closeSessionDialog}
        >
          <div
            className="session-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="session-modal-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            {sessionDialog.mode === "rename" ? (
              <form
                className="session-modal-content"
                onSubmit={(event) => {
                  event.preventDefault();
                  confirmRenameSession();
                }}
              >
                <p className="eyebrow small">Renomear conversa</p>
                <h3 id="session-modal-title">Escolha um novo nome</h3>
                <p>Atualize o título da conversa para facilitar sua organização.</p>

                <label className="session-modal-label" htmlFor="session-title-input">
                  Nome da conversa
                </label>

                <input
                  id="session-title-input"
                  autoFocus
                  value={renameDraft}
                  onChange={(event) => setRenameDraft(event.target.value)}
                  maxLength={80}
                />

                <div className="session-modal-actions">
                  <button
                    type="button"
                    className="secondary-action"
                    onClick={closeSessionDialog}
                  >
                    Cancelar
                  </button>

                  <button type="submit" disabled={!renameDraft.trim()}>
                    Salvar
                  </button>
                </div>
              </form>
            ) : (
              <div className="session-modal-content">
                <p className="eyebrow small danger-text">Excluir conversa</p>
                <h3 id="session-modal-title">Excluir esta conversa?</h3>
                <p>
                  A conversa <strong>{sessionDialog.title}</strong> será removida da
                  lista e o histórico dessa sessão será limpo.
                </p>

                <div className="session-modal-actions">
                  <button
                    type="button"
                    className="secondary-action"
                    onClick={closeSessionDialog}
                  >
                    Cancelar
                  </button>

                  <button
                    type="button"
                    className="danger-button"
                    onClick={() => void confirmDeleteSession()}
                  >
                    Excluir conversa
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function createSession(): ChatSession {
  return {
    id: crypto.randomUUID(),
    title: DEFAULT_SESSION_TITLE,
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
      title: session.title === "New chat" ? DEFAULT_SESSION_TITLE : session.title
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
