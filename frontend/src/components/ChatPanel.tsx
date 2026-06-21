import { FormEvent, useState } from "react";

import { streamChatMessage } from "../api/client";
import type { SourceChunk } from "../types/api";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
};

export function ChatPanel() {
  const [sessionId] = useState(() => crypto.randomUUID());
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();

    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) {
      return;
    }

    const assistantMessageId = crypto.randomUUID();

    setError("");
    setIsLoading(true);
    setQuestion("");

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
          sessionId,
          topK: 3
        },
        (streamEvent) => {
          if (streamEvent.event === "sources") {
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
    }
  }

  return (
    <section className="card chat-card">
      <h2>RAG Chat</h2>
      <p className="session">Session: {sessionId}</p>

      <div className="messages">
        {messages.length === 0 ? (
          <p>Ask something about the indexed documents.</p>
        ) : (
          messages.map((message) => (
            <article key={message.id} className={message.role}>
              <strong>{message.role === "user" ? "You" : "Assistant"}</strong>
              <p>{message.content || (isLoading ? "Thinking..." : "")}</p>

              {message.sources && message.sources.length > 0 && (
                <details>
                  <summary>Sources</summary>
                  <ul>
                    {message.sources.map((source) => (
                      <li key={`${source.file_id}-${source.chunk_index}`}>
                        <strong>{source.source}</strong> · score {source.score}
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

      {error && <p className="error">{error}</p>}
    </section>
  );
}
